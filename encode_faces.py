try:
    import importlib

    face_recognition = importlib.import_module("face_recognition")
except ImportError as error:
    raise SystemExit(
        "Missing dependency: install it with "
        "'python -m pip install face-recognition'"
    ) from error
import os
import pickle

dataset_folder = "datasets"
encodings = []
names = []

for student_name in os.listdir(dataset_folder):

    student_folder = os.path.join(dataset_folder, student_name)

    if not os.path.isdir(student_folder):
        continue

    print(f"Processing: {student_name}")

    for image_name in os.listdir(student_folder):

        image_path = os.path.join(student_folder, image_name)

        try:
            image = face_recognition.load_image_file(image_path)

            face_locations = face_recognition.face_locations(image)

            if len(face_locations) != 1:
                print(
                    f"Skipped {image_name}: "
                    f"found {len(face_locations)} faces."
                )
                continue

            face_encoding = face_recognition.face_encodings(
                image,
                face_locations
            )[0]

            encodings.append(face_encoding)
            names.append(student_name)

            print(f"Encoded: {image_name}")

        except Exception as error:
            print(f"Error with {image_name}: {error}")

data = {
    "encodings": encodings,
    "names": names
}

with open("face_encodings.pkl", "wb") as file:
    pickle.dump(data, file)

print()
print("Face encoding completed.")
print(f"Total encoded photos: {len(encodings)}")
