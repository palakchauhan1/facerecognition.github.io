// ─── DOM ELEMENTS ────────────────────────────────────────────────────────────

const camera = document.getElementById('camera');
const startCameraBtn = document.getElementById('startcamera');
const stopCameraBtn = document.getElementById('stopcamera');
const cameraMessage = document.querySelector('.camera-message');

const studentSelect = document.getElementById('studentSelect');
const captureFaceBtn = document.getElementById('captureFaceBtn');
const burstCaptureBtn = document.getElementById('burstCaptureBtn');
const captureProgress = document.getElementById('captureProgress');

const recognizedName = document.getElementById('recognizedName');
const recognizedRoll = document.getElementById('recognizedRoll');
const recognitionStatus = document.getElementById('recognitionStatus');
const profileIcon = document.getElementById('profileIcon');
const markAttendanceBtn = document.getElementById('markAttandence');

const studentForm = document.getElementById('studentForm');
const studentTable = document.getElementById('studentTable');
const attendenceTable = document.getElementById('attendenceTable');

const totalStudentsEl = document.getElementById('totalstudents');
const presentStudentsEl = document.getElementById('presentstudents');
const absentStudentsEl = document.getElementById('absentstudents');
const toastContainer = document.getElementById('toastContainer');

// ─── STATE ──────────────────────────────────────────────────────────────────

let cameraStream = null;
let recognitionInterval = null;
let currentRecognizedStudent = null;
let cachedStudents = [];
let isCapturingBurst = false;

const API_BASE = window.location.origin + '/api';

// ─── TOAST NOTIFICATIONS ────────────────────────────────────────────────────

function showToast(message, type = 'info') {
    if (!toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(40px)';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ─── CAMERA CAPTURE HELPER ──────────────────────────────────────────────────

function captureFrame() {
    if (!camera || !cameraStream || camera.videoWidth === 0) return null;
    const canvas = document.createElement('canvas');
    canvas.width = camera.videoWidth;
    canvas.height = camera.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(camera, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.85);
}

// ─── CAMERA CONTROLS ────────────────────────────────────────────────────────

startCameraBtn.addEventListener('click', async function () {
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 640 }, height: { ideal: 480 } },
            audio: false
        });

        camera.srcObject = cameraStream;
        if (cameraMessage) cameraMessage.style.display = 'none';

        recognitionStatus.textContent = 'Status: Camera started. Scanning...';
        showToast('Camera active! Ready for recognition or face capture.', 'success');

        startRecognitionLoop();
    } catch (error) {
        console.error('Camera error:', error);
        recognitionStatus.textContent = 'Status: Camera access denied';
        showToast('Camera access blocked. Please allow camera in browser permissions.', 'error');
    }
});

stopCameraBtn.addEventListener('click', function () {
    stopRecognitionLoop();

    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
        camera.srcObject = null;
    }

    if (cameraMessage) cameraMessage.style.display = 'block';

    currentRecognizedStudent = null;
    recognizedName.textContent = 'No Student Detected';
    recognizedRoll.textContent = 'Roll Number: -';
    recognitionStatus.textContent = 'Status: Camera is off';
    if (profileIcon) profileIcon.textContent = '👤';

    showToast('Camera stopped.', 'info');
});

// ─── RECOGNITION LOOP ───────────────────────────────────────────────────────

function startRecognitionLoop() {
    stopRecognitionLoop();

    recognitionInterval = setInterval(async () => {
        // Skip recognition if burst capturing faces
        if (isCapturingBurst || !cameraStream || camera.videoWidth === 0) return;

        const frame = captureFrame();
        if (!frame) return;

        try {
            const res = await fetch(`${API_BASE}/recognize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: frame })
            });

            const data = await res.json();

            if (data.success && data.student) {
                const s = data.student;
                currentRecognizedStudent = s;
                recognizedName.textContent = s.name;
                recognizedRoll.textContent = `Roll Number: ${s.roll} (${s.class})`;
                recognitionStatus.textContent = `Status: ✅ Verified (${data.confidence}% confidence)`;
                if (profileIcon) profileIcon.textContent = '🎓';
            } else {
                currentRecognizedStudent = null;
                recognizedName.textContent = 'No Student Detected';
                recognizedRoll.textContent = 'Roll Number: -';
                recognitionStatus.textContent = `Status: ${data.message || 'Scanning...'}`;
                if (profileIcon) profileIcon.textContent = '👤';
            }
        } catch (err) {
            console.error('Recognition error:', err);
        }
    }, 2500);
}

function stopRecognitionLoop() {
    if (recognitionInterval) {
        clearInterval(recognitionInterval);
        recognitionInterval = null;
    }
}

// ─── FACE CAPTURE ACTIONS ───────────────────────────────────────────────────

async function sendFaceCapture(roll, frameData) {
    const res = await fetch(`${API_BASE}/capture-face`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ roll: roll, image: frameData })
    });
    return await res.json();
}

// Single capture
captureFaceBtn.addEventListener('click', async function () {
    const roll = studentSelect.value;
    if (!roll) {
        showToast('Please select a student from the dropdown first!', 'error');
        return;
    }

    if (!cameraStream || camera.videoWidth === 0) {
        showToast('Please click "Start Camera" first before capturing.', 'error');
        return;
    }

    captureProgress.textContent = '📸 Capturing face sample...';
    captureProgress.style.color = '#333';

    const frame = captureFrame();
    if (!frame) return;

    try {
        const result = await sendFaceCapture(roll, frame);

        if (result.success) {
            captureProgress.textContent = `✅ Saved photo #${result.face_count}! Model trained.`;
            captureProgress.style.color = '#2b5632';
            showToast(result.message, 'success');
            await loadStudents(roll);
        } else {
            captureProgress.textContent = `⚠️ ${result.message}`;
            captureProgress.style.color = '#a93226';
            showToast(result.message, 'error');
        }
    } catch (err) {
        captureProgress.textContent = '❌ Failed to communicate with server.';
        showToast('Communication error with server.', 'error');
    }
});

// 5x Burst capture for better model training
burstCaptureBtn.addEventListener('click', async function () {
    const roll = studentSelect.value;
    if (!roll) {
        showToast('Please select a student from the dropdown first!', 'error');
        return;
    }

    if (!cameraStream || camera.videoWidth === 0) {
        showToast('Please click "Start Camera" first before capturing.', 'error');
        return;
    }

    isCapturingBurst = true;
    burstCaptureBtn.disabled = true;
    captureFaceBtn.disabled = true;

    let saved = 0;
    for (let i = 1; i <= 5; i++) {
        captureProgress.textContent = `📸 Snapping photo ${i} of 5 (tilt head slightly)...`;
        captureProgress.style.color = '#0056b3';

        const frame = captureFrame();
        if (frame) {
            try {
                const res = await sendFaceCapture(roll, frame);
                if (res.success) saved++;
            } catch (e) {
                console.error(e);
            }
        }
        await new Promise(r => setTimeout(r, 600));
    }

    burstCaptureBtn.disabled = false;
    captureFaceBtn.disabled = false;
    isCapturingBurst = false;

    if (saved > 0) {
        captureProgress.textContent = `🎉 Successfully captured ${saved} new face samples! AI model trained.`;
        captureProgress.style.color = '#2b5632';
        showToast(`Captured ${saved} face samples! Ready for auto-recognition.`, 'success');
        await loadStudents(roll);
    } else {
        captureProgress.textContent = '❌ No clear faces detected. Ensure good lighting and look straight at camera.';
        captureProgress.style.color = '#a93226';
        showToast('Could not detect face. Try again with proper lighting.', 'error');
    }
});

// ─── MARK ATTENDANCE ────────────────────────────────────────────────────────

markAttendanceBtn.addEventListener('click', async function () {
    if (!currentRecognizedStudent) {
        showToast('No student currently recognized. Look at the camera first!', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/attendance`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ roll: currentRecognizedStudent.roll })
        });

        const data = await res.json();

        if (data.success) {
            showToast(`✅ ${data.message}`, 'success');
            loadAttendance();
            loadDashboard();
        } else {
            showToast(`⚠️ ${data.message}`, 'error');
        }
    } catch (err) {
        showToast('Failed to mark attendance. Server offline?', 'error');
    }
});

// ─── REGISTER STUDENT FORM ──────────────────────────────────────────────────

studentForm.addEventListener('submit', async function (e) {
    e.preventDefault();

    const name = document.getElementById('studentName').value.trim();
    const studentClass = document.getElementById('studentClass').value.trim();

    if (!name || !studentClass) {
        showToast('Please provide both student name and class.', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/students`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, class: studentClass })
        });

        const data = await res.json();

        if (data.success) {
            showToast(`🎉 ${data.message} Now capture their face above!`, 'success');
            studentForm.reset();
            await loadStudents(data.student.roll);
            await loadDashboard();

            // Auto-prompt to start camera if off
            if (!cameraStream) {
                captureProgress.innerHTML = `👉 Click <strong>"Start Camera"</strong> above, then click <strong>"Capture Photo"</strong> for <em>${data.student.name}</em>.`;
                captureProgress.style.color = '#0056b3';
            }
        } else {
            showToast(`⚠️ ${data.message}`, 'error');
        }
    } catch (err) {
        showToast('Error registering student. Check server.', 'error');
    }
});

// ─── LOAD DATA: STUDENTS ────────────────────────────────────────────────────

async function loadStudents(selectRoll = null) {
    try {
        const res = await fetch(`${API_BASE}/students`);
        const data = await res.json();

        if (!data.success) return;
        cachedStudents = data.students || [];

        // 1. Update Dropdown
        const prevSelected = selectRoll || studentSelect.value;
        studentSelect.innerHTML = '<option value="">-- Choose Student --</option>';

        cachedStudents.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.roll;
            const faceInfo = s.face_count > 0 ? `(${s.face_count} photos)` : '(NO FACE)';
            opt.textContent = `${s.name} - Roll #${s.roll} ${faceInfo}`;
            if (String(s.roll) === String(prevSelected)) {
                opt.selected = true;
            }
            studentSelect.appendChild(opt);
        });

        // 2. Update Table
        studentTable.innerHTML = '';
        if (cachedStudents.length === 0) {
            studentTable.innerHTML = `
                <tr>
                    <td colspan="5" style="text-align:center; color:#888; padding: 20px;">
                        No students registered yet. Register one on the left!
                    </td>
                </tr>`;
            return;
        }

        cachedStudents.forEach(s => {
            const row = document.createElement('tr');
            const faceBadge = s.face_count > 0 
                ? `<span class="badge badge-success">✅ ${s.face_count} photo${s.face_count > 1 ? 's' : ''}</span>`
                : `<span class="badge badge-danger">❌ No Face</span>`;

            row.innerHTML = `
                <td><strong>${s.roll}</strong></td>
                <td>${s.name}</td>
                <td>${s.class}</td>
                <td>${faceBadge}</td>
                <td>
                    <button class="btn btn-sm secondary-btn capture-student-btn" data-roll="${s.roll}" title="Capture Face">
                        📸 Capture
                    </button>
                    <button class="btn btn-sm danger-btn delete-student-btn" data-roll="${s.roll}" title="Delete Student">
                        🗑️
                    </button>
                </td>
            `;

            // Action: select student for capture
            row.querySelector('.capture-student-btn').addEventListener('click', () => {
                studentSelect.value = s.roll;
                if (!cameraStream) {
                    showToast(`Selected ${s.name}. Please click "Start Camera" above to snap their face!`, 'info');
                } else {
                    captureFaceBtn.click();
                }
            });

            // Action: delete student
            row.querySelector('.delete-student-btn').addEventListener('click', async () => {
                if (!confirm(`Are you sure you want to delete ${s.name} (Roll #${s.roll})?`)) return;
                try {
                    const dRes = await fetch(`${API_BASE}/students/${s.roll}`, { method: 'DELETE' });
                    const dData = await dRes.json();
                    if (dData.success) {
                        showToast(dData.message, 'info');
                        loadStudents();
                        loadDashboard();
                    }
                } catch (e) {
                    showToast('Could not delete student.', 'error');
                }
            });

            studentTable.appendChild(row);
        });

    } catch (err) {
        console.error('Error loading students:', err);
    }
}

// ─── LOAD DATA: ATTENDANCE ──────────────────────────────────────────────────

async function loadAttendance() {
    try {
        const res = await fetch(`${API_BASE}/attendance`);
        const data = await res.json();
        if (!data.success) return;

        attendenceTable.innerHTML = '';
        const records = data.records || [];

        if (records.length === 0) {
            attendenceTable.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; color: #888; padding: 20px;">
                        No attendance marked yet today.
                    </td>
                </tr>`;
            return;
        }

        records.forEach((r, idx) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${idx + 1}</td>
                <td><strong>${r.name}</strong></td>
                <td>${r.roll}</td>
                <td>${r.date}</td>
                <td>${r.time}</td>
                <td><span class="badge badge-success">${r.status}</span></td>
            `;
            attendenceTable.appendChild(row);
        });
    } catch (err) {
        console.error('Error loading attendance:', err);
    }
}

// ─── LOAD DATA: DASHBOARD ───────────────────────────────────────────────────

async function loadDashboard() {
    try {
        const res = await fetch(`${API_BASE}/dashboard`);
        const data = await res.json();
        if (data.success) {
            if (totalStudentsEl) totalStudentsEl.textContent = data.total_students;
            if (presentStudentsEl) presentStudentsEl.textContent = data.present_today;
            if (absentStudentsEl) absentStudentsEl.textContent = data.absent_today;
        }
    } catch (err) {
        console.error('Error loading dashboard:', err);
    }
}

// ─── INITIALIZATION ─────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    loadStudents();
    loadAttendance();
    loadDashboard();
});
