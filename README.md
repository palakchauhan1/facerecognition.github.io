# 🎓 FaceAttend — Face Recognition Attendance System

An automated, AI-powered student attendance management system built with **Python (Flask)**, **OpenCV**, **dlib / face_recognition**, and a responsive modern web dashboard.

---

## ✨ Features

- 📸 **Web-Based Face Registration & Training:** Capture student face samples directly from the web browser camera and train the facial encoding model on the fly without running command-line scripts.
- ⚡ **Instant Face Recognition:** Real-time facial matching against registered student encodings with confidence scoring and feedback.
- 📝 **Automated Attendance Logging:** Records student ID, date, time, and status in an SQLite database with duplicate entry protection for the same day.
- 📊 **Live Analytics Dashboard:** Real-time counters for Total Registered Students, Present Students Today, and Absent Students.
- 🗃️ **In-Memory Caching:** Fast response times by caching face encodings in memory instead of reloading heavy model files from disk repeatedly.
- 🎨 **Responsive UI:** Clean, modern user interface with responsive CSS grid and smooth interactions.

---

## 🛠️ Tech Stack

- **Backend:** Python 3.11, Flask
- **Computer Vision & AI:** OpenCV (`cv2`), `face_recognition` (dlib-based deep metric learning)
- **Database:** SQLite3
- **Frontend:** HTML5, CSS3, Vanilla JavaScript (ES6+, Fetch API, WebRTC MediaDevices)

---

## 🚀 Quick Start & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/palakchauhan1/facerecognition.github.io.git
cd facerecognition.github.io
```

### 2. Create and Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install flask opencv-python numpy face-recognition
```

*(Note: On macOS with Apple Silicon or Linux, you can also use Conda / Miniforge for easy installation of dlib/cmake dependencies).*

### 4. Run the Application
```bash
python app.py
```

### 5. Open in Browser
Open your browser and navigate to:
```
http://127.0.0.1:5050
```

---

## 📖 How It Works

1. **Register a Student:**
   - Go to the **Students Management** section.
   - Enter student details (Name, Roll Number, Class).
   - Click **📷 Open Camera to Capture Face**.
   - Click **Register & Train Face** — the app automatically captures 8 frames, detects faces, computes 128-d face encodings, saves datasets, and registers the student in SQLite.

2. **Take Attendance:**
   - Go to the **Take Attendance** section.
   - Click **Start Camera**.
   - When a student's face is recognized, click **Mark Attendance**.
   - Attendance status and dashboard numbers update in real-time!

---

## 📂 Project Structure

```
├── app.py                  # Flask server, routes, and recognition logic
├── templates/
│   └── index.html          # Server-rendered HTML dashboard template
├── static/
│   ├── style.css           # Styling and layout
│   └── script.js           # Client-side camera, capture, & API calls
├── index.html              # GitHub Pages live demo & showcase page
├── datasets/               # Captured student face image samples
├── face_encodings.pkl      # Precomputed face encodings binary
├── attendance.db           # SQLite database for students and attendance
└── .gitignore              # Ignored files (models, virtualenvs, cache)
```

---

## 👤 Author

Developed by **Palak Chauhan**  
GitHub: [@palakchauhan1](https://github.com/palakchauhan1)
