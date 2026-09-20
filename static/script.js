


/* HTML ELEMENTS */

const camera = document.getElementById("camera");
const startCameraBtn = document.getElementById("startCamera");
const stopCameraBtn = document.getElementById("stopCamera");
const markAttendanceBtn = document.getElementById("markAttendance");

const studentForm = document.getElementById("studentForm");
const studentTable = document.getElementById("studentTable");
const attendanceTable = document.getElementById("attendanceTable");

const recognizedName = document.getElementById("recognizedName");
const recognizedRoll = document.getElementById("recognizedRoll");
const recognitionStatus = document.getElementById("recognitionStatus");

const totalStudents = document.getElementById("totalStudents");
const presentStudents = document.getElementById("presentStudents");
const absentStudents = document.getElementById("absentStudents");

/* REGISTRATION CAMERA ELEMENTS */

const regVideo = document.getElementById("regVideo");
const toggleRegCameraBtn = document.getElementById("toggleRegCameraBtn");
const regCameraWrapper = document.getElementById("regCameraWrapper");
const captureStatus = document.getElementById("captureStatus");

/* STATE VARIABLES */

let cameraStream = null;
let recognitionLoop = null;
let recognitionRunning = false;
let isRecognizing = false;

let regCameraStream = null;
let regCameraOpen = false;

let students = [];
let attendance = [];
let currentRecognizedStudent = null;

/* START CAMERA */

startCameraBtn.addEventListener("click", async function () {
    try {
        if (cameraStream) {
            return;
        }

        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: false
        });

        camera.srcObject = cameraStream;
        recognitionStatus.textContent = "Status: Camera is running";
        recognitionRunning = true;

        if (recognitionLoop) {
            clearInterval(recognitionLoop);
        }

        recognitionLoop = setInterval(() => {
            if (!recognitionRunning) {
                if (recognitionLoop) {
                    clearInterval(recognitionLoop);
                    recognitionLoop = null;
                }
                return;
            }
            recognizeFace();
        }, 2000);

    } catch (error) {
        console.error("Camera access error:", error);
        recognitionStatus.textContent = "Status: Camera access denied";
        alert("Camera access is required for attendance.");
    }
});

/* STOP CAMERA */

stopCameraBtn.addEventListener("click", function () {
    recognitionRunning = false;

    if (recognitionLoop) {
        clearInterval(recognitionLoop);
        recognitionLoop = null;
    }

    if (cameraStream) {
        const tracks = cameraStream.getTracks();
        tracks.forEach(function (track) {
            track.stop();
        });
        camera.srcObject = null;
        cameraStream = null;
    }

    currentRecognizedStudent = null;
    recognitionStatus.textContent = "Status: Camera stopped";
    recognizedName.textContent = "No Student Detected";
    recognizedRoll.textContent = "Roll Number: -";
});

/* FACE RECOGNITION */

async function recognizeFace() {
    if (!camera.srcObject || !recognitionRunning || isRecognizing) {
        return;
    }

    if (camera.videoWidth === 0 || camera.videoHeight === 0) {
        return;
    }

    isRecognizing = true;

    // Create canvas to capture current video frame
    const canvas = document.createElement("canvas");
    canvas.width = camera.videoWidth;
    canvas.height = camera.videoHeight;

    const context = canvas.getContext("2d");
    context.drawImage(camera, 0, 0, canvas.width, canvas.height);

    const imageData = canvas.toDataURL("image/jpeg", 0.8);

    try {
        const response = await fetch("/recognize_face", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                image: imageData
            })
        });

        const result = await response.json();

        if (result.success && result.recognized) {
            recognizedName.textContent = result.name;
            recognizedRoll.textContent = "Roll Number: " + (result.rollNumber || "-");
            recognitionStatus.textContent = "Status: Face Recognized";

            currentRecognizedStudent = {
                id: result.studentId,
                name: result.name,
                rollNumber: result.rollNumber,
                studentClass: result.studentClass
            };
        } else {
            recognizedName.textContent = "No Student Detected";
            recognizedRoll.textContent = "Roll Number: -";
            currentRecognizedStudent = null;

            if (result.message) {
                recognitionStatus.textContent = "Status: " + result.message;
            } else {
                recognitionStatus.textContent = "Status: Face Not Recognized";
            }
        }
    } catch (error) {
        console.error("Recognition error:", error);
        recognitionStatus.textContent = "Status: Recognition failed";
    } finally {
        isRecognizing = false;
    }
}

/* MARK ATTENDANCE */

markAttendanceBtn.addEventListener("click", async function () {
    let studentId = null;

    if (currentRecognizedStudent && currentRecognizedStudent.id) {
        studentId = currentRecognizedStudent.id;
    } else {
        const name = recognizedName.textContent.trim();
        if (name === "No Student Detected" || name === "") {
            alert("No student has been recognized yet. Please face the camera.");
            return;
        }

        const match = students.find(function (s) {
            return s.name.toLowerCase() === name.toLowerCase();
        });

        if (match) {
            studentId = match.id;
        } else {
            alert("Recognized student '" + name + "' was not found in the student database.");
            return;
        }
    }

    try {
        const response = await fetch("/mark_attendance", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                studentId: studentId
            })
        });

        const result = await response.json();

        if (result.success) {
            recognitionStatus.textContent = "Status: Attendance Marked";
            alert(result.message);
            await loadAttendance();
            await loadDashboardStats();
        } else {
            alert(result.message);
        }
    } catch (error) {
        console.error("Attendance submission error:", error);
        alert("Something went wrong while marking attendance.");
    }
});

/* REGISTRATION CAMERA TOGGLE */

toggleRegCameraBtn.addEventListener("click", async function () {
    if (!regCameraOpen) {
        try {
            regCameraStream = await navigator.mediaDevices.getUserMedia({
                video: true,
                audio: false
            });
            regVideo.srcObject = regCameraStream;
            regCameraWrapper.style.display = "block";
            toggleRegCameraBtn.textContent = "❌ Close Camera";
            captureStatus.textContent = "Camera ready. Fill form and click Register & Train Face.";
            regCameraOpen = true;
        } catch (err) {
            console.error("Registration camera error:", err);
            alert("Could not open camera. Please allow camera access.");
        }
    } else {
        stopRegCamera();
    }
});

function stopRegCamera() {
    if (regCameraStream) {
        regCameraStream.getTracks().forEach(track => track.stop());
        regCameraStream = null;
    }
    regVideo.srcObject = null;
    regCameraWrapper.style.display = "none";
    toggleRegCameraBtn.textContent = "📷 Open Camera to Capture Face";
    captureStatus.textContent = "Camera ready. Click Register to auto-capture.";
    regCameraOpen = false;
}

/* CAPTURE FRAMES FROM REGISTRATION CAMERA */

async function captureFrames(count, intervalMs) {
    const frames = [];
    for (let i = 0; i < count; i++) {
        captureStatus.textContent = `Capturing sample ${i + 1} of ${count}...`;

        const canvas = document.createElement("canvas");
        canvas.width = regVideo.videoWidth || 640;
        canvas.height = regVideo.videoHeight || 480;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(regVideo, 0, 0, canvas.width, canvas.height);
        frames.push(canvas.toDataURL("image/jpeg", 0.85));

        await new Promise(resolve => setTimeout(resolve, intervalMs));
    }
    return frames;
}

/* REGISTER STUDENT */

studentForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const name = document.getElementById("studentName").value.trim();
    const rollNumber = document.getElementById("rollNumber").value.trim();
    const studentClass = document.getElementById("studentClass").value.trim();

    if (!name || !rollNumber || !studentClass) {
        alert("Please fill all the fields.");
        return;
    }

    // If camera is open, capture face frames and register with face training
    if (regCameraOpen && regCameraStream) {
        captureStatus.textContent = "Starting face capture...";

        let frames;
        try {
            frames = await captureFrames(8, 200);
        } catch (err) {
            console.error("Capture error:", err);
            alert("Failed to capture camera frames.");
            return;
        }

        captureStatus.textContent = "Training face model... Please wait.";

        try {
            const response = await fetch("/register_student_with_face", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: name,
                    rollNumber: rollNumber,
                    studentClass: studentClass,
                    images: frames
                })
            });

            const result = await response.json();

            if (result.success) {
                captureStatus.textContent = "✅ " + result.message;
                alert(result.message);
                studentForm.reset();
                stopRegCamera();
                await loadStudents();
                await loadDashboardStats();
            } else {
                captureStatus.textContent = "❌ " + result.message;
                alert(result.message);
            }
        } catch (error) {
            console.error("Face registration error:", error);
            alert("Something went wrong during face registration.");
        }

    } else {
        // No camera open — fall back to text-only registration
        try {
            const response = await fetch("/add_student", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: name,
                    rollNumber: rollNumber,
                    studentClass: studentClass
                })
            });

            const result = await response.json();

            if (result.success) {
                alert(result.message + " (Note: No face captured. Open camera to enable face recognition for this student.)");
                studentForm.reset();
                await loadStudents();
                await loadDashboardStats();
            } else {
                alert(result.message);
            }
        } catch (error) {
            console.error("Student registration error:", error);
            alert("Something went wrong while registering student.");
        }
    }
});

/* LOAD STUDENTS */

async function loadStudents() {
    try {
        const response = await fetch("/get_students");
        students = await response.json();

        studentTable.innerHTML = "";

        if (students.length === 0) {
            const emptyRow = document.createElement("tr");
            emptyRow.innerHTML = `
                <td colspan="3" style="text-align: center; color: #888;">
                    No students registered yet.
                </td>
            `;
            studentTable.appendChild(emptyRow);
            return;
        }

        students.forEach(function (student) {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${student.name}</td>
                <td>${student.rollNumber}</td>
                <td>${student.studentClass}</td>
            `;
            studentTable.appendChild(row);
        });
    } catch (error) {
        console.error("Error loading students:", error);
    }
}

/* LOAD ATTENDANCE */

async function loadAttendance() {
    try {
        const response = await fetch("/get_attendance");
        attendance = await response.json();

        attendanceTable.innerHTML = "";

        if (attendance.length === 0) {
            const emptyRow = document.createElement("tr");
            emptyRow.innerHTML = `
                <td colspan="6" style="text-align: center; color: #888;">
                    No attendance recorded today yet.
                </td>
            `;
            attendanceTable.appendChild(emptyRow);
            return;
        }

        attendance.forEach(function (record, index) {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${index + 1}</td>
                <td>${record.name}</td>
                <td>${record.rollNumber}</td>
                <td>${record.date}</td>
                <td>${record.time}</td>
                <td>
                    <span class="present">
                        ${record.status}
                    </span>
                </td>
            `;
            attendanceTable.appendChild(row);
        });
    } catch (error) {
        console.error("Error loading attendance:", error);
    }
}

/* LOAD DASHBOARD STATS */

async function loadDashboardStats() {
    try {
        const response = await fetch("/get_dashboard_stats");
        const data = await response.json();

        if (data.success) {
            totalStudents.textContent = data.totalStudents;
            presentStudents.textContent = data.presentStudents;
            absentStudents.textContent = data.absentStudents;
        }
    } catch (error) {
        console.error("Error loading dashboard stats:", error);
        // Fallback calculations
        const total = students.length;
        const present = attendance.length;
        const absent = Math.max(total - present, 0);

        totalStudents.textContent = total;
        presentStudents.textContent = present;
        absentStudents.textContent = absent;
    }
}

/* INITIALIZE APP */

async function initApp() {
    await loadStudents();
    await loadAttendance();
    await loadDashboardStats();
}

initApp();