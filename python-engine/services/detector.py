from models.manager import ModelManager

class DetectorService:
    def __init__(self, model_manager: ModelManager):
        self.yolo = model_manager.get_yolo()

    def run_detection(self, img_patch):
        dets = []
        if self.yolo != "unavailable" and self.yolo is not None:
            try:
                res = self.yolo.predict(img_patch, verbose=False)[0]
                for box in res.boxes:
                    conf = float(box.conf[0])
                    if conf > 0.3:
                        name = res.names[int(box.cls[0])]
                        x1, y1, x2, y2 = map(float, box.xyxy[0])
                        dets.append({"box": [x1, y1, x2, y2], "score": conf, "label": name})
            except:
                pass
        return dets
