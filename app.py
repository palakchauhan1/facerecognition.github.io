"""
FaceAttend - Face Recognition Attendance System
Backend server using Flask and OpenCV LBPH Face Recognition.

Endpoints:
    GET    /                          → Serves frontend (index.html)
    GET    /api/students              → List all registered students
    POST   /api/students              → Register a new student
    DELETE /api/students/<int:roll>   → Delete a student and their face data
    POST   /api/capture-face          → Capture face sample from camera frame
    POST   /api/recognize             → Recognize face from camera frame
    POST   /api/attendance            → Mark attendance for student
    GET    /api/attendance            → Get today's attendance records
    GET    /api/dashboard             → Get dashboard statistics
"""

import os
import shutil
import json
import base64
import datetime
import numpy as np
import cv2

from flask import Flask, request, jsonify, send_from_directory

# ─── Configuration ───────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FACES_DIR = os.path.join(DATA_DIR, "faces")
STUDENTS_FILE = os.path.join(DATA_DIR, "students.json")
ATTENDANCE_FILE = os.path.join(DATA_DIR, "attendance.json")
MODEL_FILE = os.path.join(DATA_DIR, "face_model.yml")

os.makedirs(FACES_DIR, exist_ok=True)

# ─── OpenCV Face Detection & Recognition Setup ────────────────────────────────

CASCADE_PATH = os.path.join(DATA_DIR, "haarcascade_frontalface_default.xml")
if not os.path.exists(CASCADE_PATH):
    # Fallback to OpenCV built-in if available
    CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"

face_cascade = cv2.CascadeClassifier(CASCADE_PATH)

# LBPH Face Recognizer (no strict cut-off so we can evaluate distance dynamically)
recognizer = cv2.face.LBPHFaceRecognizer_create(
    radius=1,
    neighbors=8,
    grid_x=8,
    grid_y=8
)

# ─── Flask App ───────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder=".", static_url_path="")


# ─── Helper Functions ────────────────────────────────────────────────────────

def load_students():
    """Load students from JSON file."""
    if os.path.exists(STUDENTS_FILE):
        try:
            with open(STUDENTS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_students(students):
    """Save students to JSON file."""
    with open(STUDENTS_FILE, "w") as f:
        json.dump(students, f, indent=2)


def load_attendance():
    """Load attendance records from JSON file."""
    if os.path.exists(ATTENDANCE_FILE):
        try:
            with open(ATTENDANCE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_attendance(records):
    """Save attendance records to JSON file."""
    with open(ATTENDANCE_FILE, "w") as f:
        json.dump(records, f, indent=2)


def get_today_str():
    return datetime.date.today().strftime("%d-%m-%Y")


def get_time_str():
    return datetime.datetime.now().strftime("%I:%M %p")


def decode_base64_image(data_url):
    """Decode a base64 data URL into an OpenCV BGR image."""
    try:
        if "," in data_url:
            data_url = data_url.split(",")[1]
        img_bytes = base64.b64decode(data_url)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"Error decoding image: {e}")
        return None


def detect_faces(img):
    """Detect faces with tuned parameters for webcams."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=4,
        minSize=(40, 40),
        flags=cv2.CASCADE_SCALE_IMAGE
    )
    return faces, gray


def extract_face(gray, face_rect, size=(200, 200)):
    """Crop and standardize face region."""
    x, y, w, h = face_rect
    face_roi = gray[y:y+h, x:x+w]
    return cv2.resize(face_roi, size)


def train_recognizer():
    """Train LBPH recognizer with all stored face images."""
    global recognizer
    students = load_students()
    faces = []
    labels = []

    for student in students:
        roll = student["roll"]
        student_face_dir = os.path.join(FACES_DIR, str(roll))

        if not os.path.exists(student_face_dir):
            continue

        for filename in sorted(os.listdir(student_face_dir)):
            if not filename.lower().endswith((".jpg", ".png", ".jpeg")):
                continue
            filepath = os.path.join(student_face_dir, filename)
            img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                img_resized = cv2.resize(img, (200, 200))
                faces.append(img_resized)
                labels.append(int(roll))

    if len(faces) >= 1:
        recognizer = cv2.face.LBPHFaceRecognizer_create(radius=1, neighbors=8, grid_x=8, grid_y=8)
        recognizer.train(faces, np.array(labels))
        recognizer.save(MODEL_FILE)
        print(f"  [AI] Trained model with {len(faces)} face photos across {len(set(labels))} students.")
        return True
    else:
        if os.path.exists(MODEL_FILE):
            try:
                os.remove(MODEL_FILE)
            except Exception:
                pass
        return False


def load_model():
    """Load previously saved model if present."""
    if os.path.exists(MODEL_FILE):
        try:
            recognizer.read(MODEL_FILE)
            print("  [AI] Loaded existing face model from disk.")
            return True
        except Exception as e:
            print(f"  [AI] Could not load model: {e}")
    return False


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def serve_index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(BASE_DIR, path)


# ── Students API ─────────────────────────────────────────────────────────────

@app.route("/api/students", methods=["GET"])
def get_students():
    students = load_students()
    # Ensure face_count and has_face are accurate with disk
    for student in students:
        s_dir = os.path.join(FACES_DIR, str(student["roll"]))
        if os.path.exists(s_dir):
            photos = [f for f in os.listdir(s_dir) if f.lower().endswith((".jpg", ".png"))]
            student["face_count"] = len(photos)
            student["has_face"] = len(photos) > 0
        else:
            student["face_count"] = 0
            student["has_face"] = False
    return jsonify({"success": True, "students": students})


@app.route("/api/students", methods=["POST"])
def register_student():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    student_class = data.get("class", "").strip()

    if not name or not student_class:
        return jsonify({"success": False, "message": "Name and Class are required."}), 400

    students = load_students()
    roll = 101 if not students else max(s["roll"] for s in students) + 1

    student = {
        "name": name,
        "class": student_class,
        "roll": roll,
        "has_face": False,
        "face_count": 0,
        "registered_at": datetime.datetime.now().isoformat()
    }

    students.append(student)
    save_students(students)

    return jsonify({
        "success": True,
        "message": f"Student '{name}' registered with Roll #{roll}.",
        "student": student
    })


@app.route("/api/students/<int:roll>", methods=["DELETE"])
def delete_student(roll):
    students = load_students()
    student = next((s for s in students if s["roll"] == roll), None)
    if not student:
        return jsonify({"success": False, "message": "Student not found."}), 404

    students = [s for s in students if s["roll"] != roll]
    save_students(students)

    # Remove face images folder
    s_dir = os.path.join(FACES_DIR, str(roll))
    if os.path.exists(s_dir):
        shutil.rmtree(s_dir, ignore_errors=True)

    # Retrain
    train_recognizer()

    return jsonify({"success": True, "message": f"Deleted student Roll #{roll}."})


# ── Face Capture API ─────────────────────────────────────────────────────────

@app.route("/api/capture-face", methods=["POST"])
def capture_face():
    data = request.get_json() or {}
    roll = data.get("roll")
    image_data = data.get("image")

    if not roll or not image_data:
        return jsonify({"success": False, "message": "Roll number and image are required."}), 400

    try:
        roll = int(roll)
    except ValueError:
        return jsonify({"success": False, "message": "Invalid roll number."}), 400

    students = load_students()
    student = next((s for s in students if s["roll"] == roll), None)

    if not student:
        return jsonify({"success": False, "message": f"Student with Roll #{roll} not found."}), 404

    img = decode_base64_image(image_data)
    if img is None:
        return jsonify({"success": False, "message": "Could not read camera frame."}), 400

    faces, gray = detect_faces(img)

    if len(faces) == 0:
        return jsonify({
            "success": False,
            "message": "No face detected. Please face the camera with good lighting and stay still."
        }), 400

    if len(faces) > 1:
        return jsonify({
            "success": False,
            "message": "Multiple faces detected. Please make sure only one person is in view."
        }), 400

    # Save face image
    student_face_dir = os.path.join(FACES_DIR, str(roll))
    os.makedirs(student_face_dir, exist_ok=True)

    existing_photos = [f for f in os.listdir(student_face_dir) if f.lower().endswith(".jpg")]
    next_idx = len(existing_photos) + 1

    face_img = extract_face(gray, faces[0])
    face_path = os.path.join(student_face_dir, f"face_{next_idx}.jpg")
    cv2.imwrite(face_path, face_img)

    total_photos = next_idx
    student["has_face"] = True
    student["face_count"] = total_photos
    save_students(students)

    # Train model immediately
    train_recognizer()

    return jsonify({
        "success": True,
        "message": f"Face photo #{total_photos} captured for {student['name']}! (Trained & ready)",
        "face_count": total_photos,
        "student": student
    })


# ── Face Recognition API ─────────────────────────────────────────────────────

@app.route("/api/recognize", methods=["POST"])
def recognize_face():
    data = request.get_json() or {}
    image_data = data.get("image")

    if not image_data:
        return jsonify({"success": False, "message": "Image frame missing."}), 400

    if not os.path.exists(MODEL_FILE):
        return jsonify({
            "success": False,
            "message": "No face photos trained yet. Please capture a face first!"
        })

    img = decode_base64_image(image_data)
    if img is None:
        return jsonify({"success": False, "message": "Invalid image."}), 400

    faces, gray = detect_faces(img)

    if len(faces) == 0:
        return jsonify({"success": False, "message": "No face detected in camera."})

    # Pick largest detected face
    largest_face = max(faces, key=lambda r: r[2] * r[3])
    face_img = extract_face(gray, largest_face)

    try:
        label, distance = recognizer.predict(face_img)
    except Exception as e:
        return jsonify({"success": False, "message": f"Recognition error: {str(e)}"})

    # In LBPH: distance < 85 is generally a reliable match (lower distance = closer match)
    if distance < 85:
        students = load_students()
        student = next((s for s in students if s["roll"] == label), None)

        if student:
            confidence_pct = max(10, min(99, round(100 - (distance * 0.75))))
            return jsonify({
                "success": True,
                "student": student,
                "confidence": confidence_pct,
                "distance": round(distance, 1)
            })

    return jsonify({
        "success": False,
        "message": f"Face detected but not recognized (distance: {round(distance, 1)})."
    })


# ── Attendance API ───────────────────────────────────────────────────────────

@app.route("/api/attendance", methods=["POST"])
def mark_attendance():
    data = request.get_json() or {}
    roll = data.get("roll")

    if not roll:
        return jsonify({"success": False, "message": "Roll number is required."}), 400

    try:
        roll = int(roll)
    except ValueError:
        return jsonify({"success": False, "message": "Invalid roll."}), 400

    students = load_students()
    student = next((s for s in students if s["roll"] == roll), None)

    if not student:
        return jsonify({"success": False, "message": "Student not found."}), 404

    today = get_today_str()
    records = load_attendance()

    already_marked = any(r["roll"] == roll and r["date"] == today for r in records)

    if already_marked:
        return jsonify({
            "success": False,
            "message": f"{student['name']} (Roll #{roll}) is already marked Present today."
        })

    record = {
        "name": student["name"],
        "roll": student["roll"],
        "class": student["class"],
        "date": today,
        "time": get_time_str(),
        "status": "Present"
    }

    records.append(record)
    save_attendance(records)

    return jsonify({
        "success": True,
        "message": f"Attendance marked for {student['name']}!",
        "record": record
    })


@app.route("/api/attendance", methods=["GET"])
def get_attendance():
    today = get_today_str()
    records = load_attendance()
    today_records = [r for r in records if r["date"] == today]
    return jsonify({"success": True, "records": today_records})


# ── Dashboard API ────────────────────────────────────────────────────────────

@app.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    students = load_students()
    total = len(students)

    today = get_today_str()
    records = load_attendance()
    present_today = len(set(r["roll"] for r in records if r["date"] == today))
    absent_today = max(0, total - present_today)

    return jsonify({
        "success": True,
        "total_students": total,
        "present_today": present_today,
        "absent_today": absent_today
    })


# ─── Initialize ──────────────────────────────────────────────────────────────

def init():
    if not os.path.exists(STUDENTS_FILE):
        save_students([])
    if not os.path.exists(ATTENDANCE_FILE):
        save_attendance([])

    # If images exist, train or load model
    if not load_model():
        train_recognizer()


if __name__ == "__main__":
    init()
    print()
    print("=" * 55)
    print("  🎓 FaceAttend - Face Recognition Attendance System")
    print("=" * 55)
    print("  Server:  http://localhost:5001")
    print(f"  Data:    {DATA_DIR}")
    print(f"  Faces:   {FACES_DIR}")
    print("=" * 55)
    print()
    app.run(debug=True, host="0.0.0.0", port=5001)
