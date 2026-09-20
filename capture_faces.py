try:
    import importlib

    cv2 = importlib.import_module("cv2")
except ImportError:
    print("OpenCV is not installed. Install it with: python -m pip install opencv-python")
    raise SystemExit(1)
import os

student_name = input("Enter student folder name: ").strip()

folder = os.path.join("datasets", student_name)
os.makedirs(folder, exist_ok=True)

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Camera could not be opened.")
    exit()

count = 0

print("Camera started.")
print("Look at the camera.")
print("Press Q to stop.")

while True:
    ret, frame = camera.read()

    if not ret:
        print("Could not read camera.")
        break

    cv2.imshow("Face Capture", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("c"):
        filename = os.path.join(folder, f"{count + 1}.jpg")
        cv2.imwrite(filename, frame)
        count += 1
        print(f"Photo {count} saved.")

    elif key == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()

print(f"Total photos saved: {count}")