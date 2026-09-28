import os
import pickle
import sqlite3
import base64
from datetime import datetime
import importlib
from flask import Flask, render_template, request, jsonify

# Load CV libraries dynamically so Flask can run all routes
# and report clear status if libraries are missing in the active environment.
try:
    np = importlib.import_module("numpy")
    cv2 = importlib.import_module("cv2")
    face_recognition = importlib.import_module("face_recognition")
except ImportError as import_err:
    np = None
    cv2 = None
    face_recognition = None
    print(f"Note: CV dependencies not loaded: {import_err}")

app = Flask(__name__)

# IN-MEMORY FACE ENCODING CACHE
KNOWN_FACES = {"encodings": [], "names": []}


def load_known_faces():
    global KNOWN_FACES
    encodings_path = "face_encodings.pkl"
    if os.path.exists(encodings_path):
        try:
            with open(encodings_path, "rb") as file:
                saved_data = pickle.load(file)
                KNOWN_FACES = {
                    "encodings": saved_data.get("encodings", []),
                    "names": saved_data.get("names", []),
                }
                print(
                    f"Loaded {len(KNOWN_FACES['encodings'])} face encodings into cache."
                )
        except Exception as error:
            print(f"Error loading face encodings: {error}")
            KNOWN_FACES = {"encodings": [], "names": []}
    else:
        KNOWN_FACES = {"encodings": [], "names": []}


# DATABASE


def get_db():
    conn = sqlite3.connect("attendance.db", timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def create_table():
    conn = get_db()

    # Students table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_number TEXT UNIQUE NOT NULL,
            student_class TEXT NOT NULL
        )
    """)

    # Attendance table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)

    conn.commit()
    conn.close()


# HOME


@app.route("/")
def home():
    return render_template("index.html")


# ADD STUDENT


@app.route("/add_student", methods=["POST"])
def add_student():
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "No data received."})

    name = data.get("name")
    roll_number = data.get("rollNumber")
    student_class = data.get("studentClass")

    # Check empty fields
    if not name or not roll_number or not student_class:
        return jsonify({
            "success": False,
            "message": "Please fill all fields.",
        })

    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO students
            (name, roll_number, student_class)
            VALUES (?, ?, ?)
        """,
            (name, roll_number, student_class),
        )
        conn.commit()

        return jsonify({
            "success": True,
            "message": "Student registered successfully!",
        })

    except sqlite3.IntegrityError:
        return jsonify({
            "success": False,
            "message": "This roll number is already registered.",
        })
    finally:
        conn.close()


# RECOGNIZE FACE


@app.route("/recognize_face", methods=["POST"])
def recognize_face():
    global np, cv2, face_recognition
    if np is None or cv2 is None or face_recognition is None:
        try:
            np = importlib.import_module("numpy")
            cv2 = importlib.import_module("cv2")
            face_recognition = importlib.import_module("face_recognition")
        except ImportError:
            return jsonify({
                "success": False,
                "message": "CV dependencies (OpenCV/face_recognition/numpy) are not installed in this environment.",
            })

    data = request.get_json()

    if not data or "image" not in data:
        return jsonify({"success": False, "message": "Image not received."})

    try:
        image_data = data["image"]

        # Base64 header remove
        if "," in image_data:
            image_data = image_data.split(",")[1]

        # Base64 → image
        image_bytes = base64.b64decode(image_data)
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({
                "success": False,
                "message": "Failed to decode camera frame.",
            })

        # BGR → RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Detect face
        face_locations = face_recognition.face_locations(rgb_frame)
        if not face_locations:
            return jsonify({
                "success": True,
                "recognized": False,
                "message": "No face detected in camera.",
            })

        face_encodings = face_recognition.face_encodings(
            rgb_frame, face_locations
        )

        # Ensure cache is populated
        if not KNOWN_FACES["encodings"]:
            load_known_faces()

        known_encodings = KNOWN_FACES["encodings"]
        known_names = KNOWN_FACES["names"]

        if not known_encodings:
            return jsonify({
                "success": False,
                "message": "No trained face encodings found. Please train faces first.",
            })

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(
                known_encodings, face_encoding, tolerance=0.5
            )

            if True in matches:
                index = matches.index(True)
                student_name = known_names[index]

                conn = get_db()
                student = conn.execute(
                    """
                    SELECT id, name, roll_number, student_class
                    FROM students
                    WHERE LOWER(name) = LOWER(?)
                    ORDER BY id DESC
                """,
                    (student_name,),
                ).fetchone()
                conn.close()

                if student:
                    return jsonify({
                        "success": True,
                        "recognized": True,
                        "studentId": student["id"],
                        "name": student["name"],
                        "rollNumber": student["roll_number"],
                        "studentClass": student["student_class"],
                    })

                return jsonify({
                    "success": True,
                    "recognized": True,
                    "name": student_name,
                    "rollNumber": "-",
                })

        return jsonify({
            "success": True,
            "recognized": False,
            "message": "Face not recognized.",
        })

    except Exception as error:
        print("Recognition error:", error)
        return jsonify({"success": False, "message": "Face recognition failed."})


# GET STUDENTS


@app.route("/get_students", methods=["GET"])
def get_students():
    conn = get_db()
    try:
        students = conn.execute("""
            SELECT
                id,
                name,
                roll_number,
                student_class
            FROM students
            ORDER BY id DESC
        """).fetchall()

        return jsonify([
            {
                "id": student["id"],
                "name": student["name"],
                "rollNumber": student["roll_number"],
                "studentClass": student["student_class"],
            }
            for student in students
        ])
    finally:
        conn.close()


# GET TODAY'S ATTENDANCE


@app.route("/get_attendance", methods=["GET"])
def get_attendance():
    conn = get_db()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        records = conn.execute(
            """
            SELECT 
                a.id,
                a.student_id,
                s.name,
                s.roll_number,
                s.student_class,
                a.date,
                a.time,
                a.status
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE a.date = ?
            ORDER BY a.id DESC
        """,
            (today,),
        ).fetchall()

        return jsonify([
            {
                "id": record["id"],
                "studentId": record["student_id"],
                "name": record["name"],
                "rollNumber": record["roll_number"],
                "studentClass": record["student_class"],
                "date": record["date"],
                "time": record["time"],
                "status": record["status"],
            }
            for record in records
        ])
    finally:
        conn.close()


# GET DASHBOARD STATS


@app.route("/get_dashboard_stats", methods=["GET"])
def get_dashboard_stats():
    conn = get_db()
    try:
        today = datetime.now().strftime("%Y-%m-%d")

        total_row = conn.execute(
            "SELECT COUNT(*) AS count FROM students"
        ).fetchone()
        total_students = total_row["count"] if total_row else 0

        present_row = conn.execute(
            """
            SELECT COUNT(DISTINCT student_id) AS count 
            FROM attendance 
            WHERE date = ?
        """,
            (today,),
        ).fetchone()
        present_students = present_row["count"] if present_row else 0

        absent_students = max(total_students - present_students, 0)

        return jsonify({
            "success": True,
            "totalStudents": total_students,
            "presentStudents": present_students,
            "absentStudents": absent_students,
        })
    finally:
        conn.close()


# MARK ATTENDANCE


@app.route("/mark_attendance", methods=["POST"])
def mark_attendance():
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "No data received."})

    student_id = data.get("studentId")

    # Check student ID
    if not student_id:
        return jsonify({
            "success": False,
            "message": "Student ID is required.",
        })

    conn = get_db()
    try:
        # Current date and time
        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")

        # Check today's attendance
        existing = conn.execute(
            """
            SELECT id
            FROM attendance
            WHERE student_id = ?
            AND date = ?
        """,
            (student_id, date),
        ).fetchone()

        if existing:
            return jsonify({
                "success": False,
                "message": "Attendance already marked today.",
            })

        # Insert attendance
        conn.execute(
            """
            INSERT INTO attendance
            (
                student_id,
                date,
                time,
                status
            )
            VALUES (?, ?, ?, ?)
        """,
            (student_id, date, time, "Present"),
        )
        conn.commit()

        return jsonify({
            "success": True,
            "message": "Attendance marked successfully!",
        })
    finally:
        conn.close()


# REGISTER STUDENT WITH FACE (WEB-BASED CAPTURE)


@app.route("/register_student_with_face", methods=["POST"])
def register_student_with_face():
    global KNOWN_FACES

    # Ensure CV libraries are loaded
    global np, cv2, face_recognition
    if np is None or cv2 is None or face_recognition is None:
        try:
            np = importlib.import_module("numpy")
            cv2 = importlib.import_module("cv2")
            face_recognition = importlib.import_module("face_recognition")
        except ImportError:
            return jsonify({
                "success": False,
                "message": "CV libraries not available. Cannot process face images.",
            })

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data received."})

    name = data.get("name", "").strip()
    roll_number = data.get("rollNumber", "").strip()
    student_class = data.get("studentClass", "").strip()
    images = data.get("images", [])  # list of base64 image strings

    # Validate fields
    if not name or not roll_number or not student_class:
        return jsonify({"success": False, "message": "Please fill all fields."})

    if not images or len(images) == 0:
        return jsonify({"success": False, "message": "No face images captured."})

    # Insert student into database
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO students (name, roll_number, student_class)
            VALUES (?, ?, ?)
        """,
            (name, roll_number, student_class),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({
            "success": False,
            "message": "This roll number is already registered.",
        })
    finally:
        conn.close()

    # Save images and generate encodings
    student_folder = os.path.join("datasets", name)
    os.makedirs(student_folder, exist_ok=True)

    new_encodings = []
    saved_count = 0

    for idx, image_data in enumerate(images):
        try:
            # Strip base64 header if present
            if "," in image_data:
                image_data = image_data.split(",")[1]

            image_bytes = base64.b64decode(image_data)
            image_array = np.frombuffer(image_bytes, dtype=np.uint8)
            frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if frame is None:
                continue

            # Save raw image to dataset folder
            filename = os.path.join(student_folder, f"{idx + 1}.jpg")
            cv2.imwrite(filename, frame)

            # Generate face encoding
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)

            if len(face_locations) == 1:
                encoding = face_recognition.face_encodings(rgb_frame, face_locations)[0]
                new_encodings.append(encoding)
                saved_count += 1

        except Exception as e:
            print(f"Error processing image {idx + 1}: {e}")
            continue

    if saved_count == 0:
        return jsonify({
            "success": False,
            "message": "No valid face detected in captured images. Please retake photos with a clear face view.",
        })

    # Append new encodings to existing ones in memory
    KNOWN_FACES["encodings"].extend(new_encodings)
    KNOWN_FACES["names"].extend([name] * len(new_encodings))

    # Persist updated encodings to disk
    try:
        with open("face_encodings.pkl", "wb") as f:
            pickle.dump({"encodings": KNOWN_FACES["encodings"], "names": KNOWN_FACES["names"]}, f)
    except Exception as e:
        print(f"Warning: Could not save encodings to disk: {e}")

    return jsonify({
        "success": True,
        "message": f"Student '{name}' registered and face trained successfully with {saved_count} sample(s)!",
        "encodedSamples": saved_count,
    })


# RELOAD ENCODINGS ENDPOINT


@app.route("/reload_encodings", methods=["POST"])
def reload_encodings():
    load_known_faces()
    return jsonify({
        "success": True,
        "count": len(KNOWN_FACES["encodings"]),
        "message": f"Reloaded {len(KNOWN_FACES['encodings'])} encodings.",
    })


# Initialize DB and Encodings at startup (for Gunicorn & Direct execution)
create_table()
load_known_faces()


# RUN APPLICATION


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(debug=True, host="0.0.0.0", port=port)