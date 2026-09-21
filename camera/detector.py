"""
BELTSENTINEL AI
YOLO Detection Engine

Trained YOLOv8 classes:

0 = belt_crack
1 = belt_tear
2 = edge_damage
3 = joint_damage

Trained model:
models/best.pt
"""

import os
import cv2


class YOLODetector:
    def __init__(
        self,
        model_path="models/best.pt",
        confidence_threshold=0.25
    ):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold

        self.model = None
        self.loaded = False
        self.error = None

        # IMPORTANT:
        # This order MUST match the trained best.pt model.
        self.class_names = {
            0: "belt_crack",
            1: "belt_tear",
            2: "edge_damage",
            3: "joint_damage"
        }

        self.load_model()

    def load_model(self):
        if not os.path.exists(self.model_path):
            self.error = (
                "YOLO model not found. "
                "Place trained model at "
                f"{self.model_path}"
            )

            print()
            print("YOLO MODEL NOT FOUND")
            print(self.error)
            print("Running in YOLO-READY mode.")

            self.loaded = False
            return False

        try:
            from ultralytics import YOLO

            self.model = YOLO(self.model_path)

            self.loaded = True
            self.error = None

            # Read the actual class names from the trained model.
            # This prevents the camera-side mapping from becoming
            # inconsistent with best.pt.
            if hasattr(self.model, "names") and self.model.names:
                model_names = self.model.names

                if isinstance(model_names, dict):
                    self.class_names = {
                        int(class_id): str(class_name)
                        for class_id, class_name in model_names.items()
                    }
                elif isinstance(model_names, list):
                    self.class_names = {
                        index: str(class_name)
                        for index, class_name in enumerate(model_names)
                    }

            print("YOLO MODEL LOADED")
            print(f"Model: {self.model_path}")

            return True

        except Exception as error:
            self.error = str(error)
            self.loaded = False

            print("YOLO LOAD ERROR:")
            print(error)

            return False

    def detect(self, frame):
        if frame is None:
            return {
                "frame": None,
                "detections": [],
                "status": "NO_FRAME"
            }

        if not self.loaded:
            return {
                "frame": frame,
                "detections": [],
                "status": "MODEL_NOT_LOADED"
            }

        try:
            results = self.model.predict(
                source=frame,
                conf=self.confidence_threshold,
                verbose=False
            )

            annotated_frame = frame.copy()
            detections = []

            for result in results:
                boxes = result.boxes

                if boxes is None:
                    continue

                for box in boxes:
                    class_id = int(
                        box.cls[0].item()
                    )

                    confidence = float(
                        box.conf[0].item()
                    )

                    x1, y1, x2, y2 = (
                        box.xyxy[0]
                        .cpu()
                        .numpy()
                        .astype(int)
                    )

                    class_name = self.class_names.get(
                        class_id,
                        f"class_{class_id}"
                    )

                    detection = {
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": round(
                            confidence,
                            4
                        ),
                        "bbox": {
                            "x1": int(x1),
                            "y1": int(y1),
                            "x2": int(x2),
                            "y2": int(y2)
                        }
                    }

                    detections.append(detection)

                    label = (
                        f"{class_name} "
                        f"{confidence * 100:.1f}%"
                    )

                    cv2.rectangle(
                        annotated_frame,
                        (x1, y1),
                        (x2, y2),
                        (255, 255, 255),
                        2
                    )

                    cv2.putText(
                        annotated_frame,
                        label,
                        (x1, max(y1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        2
                    )

            return {
                "frame": annotated_frame,
                "detections": detections,
                "status": "OK"
            }

        except Exception as error:
            self.error = str(error)

            return {
                "frame": frame,
                "detections": [],
                "status": "DETECTION_ERROR",
                "error": str(error)
            }

    def get_status(self):
        return {
            "loaded": self.loaded,
            "model_path": self.model_path,
            "confidence_threshold": self.confidence_threshold,
            "error": self.error,
            "classes": self.class_names
        }


if __name__ == "__main__":
    detector = YOLODetector()

    print()
    print("=" * 60)
    print("YOLO STATUS")
    print("=" * 60)

    print(detector.get_status())