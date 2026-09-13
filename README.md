# 🎓 FaceAttend - Face Recognition Attendance System

An automated, AI-powered Face Recognition Attendance System built with **Python (Flask)**, **OpenCV**, and a responsive **Web Dashboard** (HTML5, CSS3, JavaScript).

---

## 🌟 Key Features

- 👤 **Student Registration**: Easily register new students with their name and class/branch.
- 📸 **Face Data Capture**:
  - **1x Snapshot**: Take a single picture to register a student's face.
  - **⚡ 5x Burst Capture**: Automatically snap 5 angles in seconds to train the model with higher accuracy.
- 🤖 **Real-Time Face Recognition**: Uses OpenCV Haar Cascades for face detection and Local Binary Patterns Histograms (LBPH) for recognition.
- 📋 **Automated Attendance**: Real-time facial identification marks student attendance with timestamp and date.
- 📊 **Live Dashboard**: Displays real-time counts for Total Students, Present Today, and Absent Today.
- 🛡️ **Privacy First**: Sensitive face crops and model files are local to your machine.

---

## 🛠️ Tech Stack

- **Backend**: Python 3, Flask
- **Computer Vision / AI**: OpenCV (`opencv-contrib-python`), Haar Cascades, LBPH Face Recognizer
- **Frontend**: HTML5, Vanilla CSS3 (Custom responsive layout & design system), JavaScript (ES6+)

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/face-recognition-attendance-system.git
cd face-recognition-attendance-system
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python3 app.py
```

### 4. Open in Browser
Visit **[http://localhost:5001](http://localhost:5001)** in your web browser.

---

## 📖 How to Use

1. **Register Student**:
   - Scroll to **Students Management**.
   - Enter student name and class (e.g. *Palak*, *B.Tech CSE*) and click **Register Student**.
2. **Capture Facial Data**:
   - Scroll up to **Take Attendance** and click **Start Camera**.
   - In the **Register Student Face** toolbar, pick the student from the dropdown.
   - Click **5x Burst Capture** while looking at the camera.
3. **Verify Attendance**:
   - Look directly into the camera. The AI will detect and display your name and verification confidence.
   - Click **Mark Attendance** to record attendance in today's log.

---

## 📁 Project Structure

```
├── app.py                 # Flask server & OpenCV Face Recognition API
├── index.html             # Responsive Web Dashboard
├── script.js              # Camera stream, real-time recognition loop & API calls
├── style.css              # Custom styling, animations & theme
├── requirements.txt       # Python dependencies
├── .gitignore             # Ignored directories & cache
├── README.md              # Project documentation
└── data/                  # Face model, cascade XML & storage
    └── haarcascade_frontalface_default.xml
```

---

## 📄 License
This project is open source and available under the [MIT License](LICENSE).
