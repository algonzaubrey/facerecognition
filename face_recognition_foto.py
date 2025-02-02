import os
import cv2
import torch
from facenet_pytorch import InceptionResnetV1, MTCNN
from types import MethodType

### Load Models
resnet = InceptionResnetV1(pretrained='vggface2').eval()
mtcnn = MTCNN(
    image_size=160, keep_all=True, thresholds=[0.4, 0.5, 0.5], min_face_size=60
)

def detect_box(self, img, save_path=None):
    batch_boxes, batch_probs, batch_points = self.detect(img, landmarks=True)
    if not self.keep_all:
        batch_boxes, batch_probs, batch_points = self.select_boxes(
            batch_boxes, batch_probs, batch_points, img, method=self.selection_method
        )
    faces = self.extract(img, batch_boxes, save_path)
    return batch_boxes, faces

mtcnn.detect_box = MethodType(detect_box, mtcnn)

def encode(img):
    with torch.no_grad():
        img_embedding = resnet(img)
    return img_embedding

### Load Encoded Features from Dataset
saved_pictures = "UAS/foto"
all_people_faces = {}

for file in os.listdir(saved_pictures):
    if file.lower().endswith(('.png', '.jpg', '.jpeg')):
        person_face = os.path.splitext(file)[0]
        img_path = os.path.join(saved_pictures, file)
        img = cv2.imread(img_path)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        batch_boxes, faces = mtcnn.detect_box(img_rgb)
        if faces is not None and len(faces) > 0:
            face_tensor = faces[0].unsqueeze(0)
            all_people_faces[person_face] = encode(face_tensor)[0]

def recognize_from_photo(photo_path, thres=0.8):
    if not os.path.exists(photo_path):
        print(f"[ERROR] File not found: {photo_path}")
        return

    img = cv2.imread(photo_path)
    if img is None:
        print(f"[ERROR] Unable to read the file: {photo_path}")
        return

    try:
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    except cv2.error as e:
        print(f"[ERROR] cv2.cvtColor failed: {e}")
        return

    batch_boxes, cropped_images = mtcnn.detect_box(img_rgb)

    if cropped_images is not None:
        for box, cropped in zip(batch_boxes, cropped_images):
            x, y, x2, y2 = [int(coord) for coord in box]
            img_embedding = encode(cropped.unsqueeze(0))

            detect_dict = {k: (v - img_embedding).norm().item() for k, v in all_people_faces.items()}
            min_key = min(detect_dict, key=detect_dict.get)
            if detect_dict[min_key] >= thres:
                min_key = 'Unknown'

            cv2.rectangle(img, (x, y), (x2, y2), (0, 0, 255), 2)
            cv2.putText(
                img, min_key, (x + 5, y + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2
            )
    else:
        print("[INFO] No faces detected in the image.")

    cv2.imshow("Face Recognition Result", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

### Main Entry Point
if __name__ == "__main__":
    test_photo_path = "UAS/timezone.jpg"
    recognize_from_photo(test_photo_path)
