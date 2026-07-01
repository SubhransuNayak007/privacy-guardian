from models.manager import ModelManager
import cv2
import os

class DetectorService:
    def __init__(self, model_manager: ModelManager):
        self.yolo = model_manager.get_yolo()
        
        # Initialize Haar Cascades
        self.face_cascade = None
        self.plate_cascade = None
        
        try:
            face_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
            if os.path.exists(face_path):
                self.face_cascade = cv2.CascadeClassifier(face_path)
                
            plate_path = os.path.join(cv2.data.haarcascades, 'haarcascade_russian_plate_number.xml')
            if os.path.exists(plate_path):
                self.plate_cascade = cv2.CascadeClassifier(plate_path)
        except Exception as e:
            print(f"Error loading cascades: {e}")

    def run_detection(self, img_patch):
        dets = []
        
        # 1. Run YOLO (standard object detection)
        if self.yolo != "unavailable" and self.yolo is not None:
            try:
                res = self.yolo.predict(img_patch, verbose=False)[0]
                for box in res.boxes:
                    conf = float(box.conf[0])
                    if conf > 0.3:
                        name = res.names[int(box.cls[0])]
                        # Removed mock mapping to let generic YOLO classes (person, car) pass through accurately
                        x1, y1, x2, y2 = map(float, box.xyxy[0])
                        dets.append({"box": [x1, y1, x2, y2], "score": conf, "label": name})
            except Exception as e:
                pass
                
        # 2. Run Haar Cascades (specialized sub-regions)
        try:
            if img_patch is not None and img_patch.size > 0:
                gray = cv2.cvtColor(img_patch, cv2.COLOR_BGR2GRAY)
                
                # Face detection
                if self.face_cascade is not None and not self.face_cascade.empty():
                    faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(20, 20))
                    for (x, y, w, h) in faces:
                        dets.append({
                            "box": [float(x), float(y), float(x+w), float(y+h)],
                            "score": 0.85, # Base confidence for Cascade
                            "label": "face"
                        })
                        
                # License plate detection
                if self.plate_cascade is not None and not self.plate_cascade.empty():
                    plates = self.plate_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 10))
                    for (x, y, w, h) in plates:
                        dets.append({
                            "box": [float(x), float(y), float(x+w), float(y+h)],
                            "score": 0.85, # Base confidence
                            "label": "license_plate"
                        })
        except Exception as e:
            pass

        return dets
