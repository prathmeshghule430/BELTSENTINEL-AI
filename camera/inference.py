"""
============================================================
BELTSENTINEL AI
REAL-TIME CAMERA + YOLO INFERENCE MANAGER

MODULE 7.8

Responsibilities:

    Camera
       ↓
    OpenCV frame
       ↓
    YOLO detector
       ↓
    Detection result
       ↓
    Flask backend

The camera can work even when YOLO model is unavailable.

If models/best.pt is missing or invalid:
    Camera       = READY
    YOLO         = STANDBY
    Inference    = WAITING_FOR_MODEL
============================================================
"""

import threading
import time
import cv2

from camera.camera import CameraManager
from camera.detector import YOLODetector


class InferenceManager:

    def __init__(
        self,
        camera_index=0,
        model_path="models/best.pt"
    ):

        self.camera = CameraManager(
            camera_index=camera_index
        )

        self.detector = YOLODetector(
            model_path=model_path
        )

        self.running = False
        self.thread = None

        self.lock = threading.Lock()

        self.latest_result = {
            "detections": [],
            "status": "NOT_STARTED",
            "camera_available": False,
            "model_loaded": False,
            "timestamp": None
        }

        self.latest_jpeg = None

    # ========================================================
    # START
    # ========================================================

    def start(self):

        if self.running:
            return True

        camera_started = self.camera.start()

        self.running = True

        self.thread = threading.Thread(
            target=self._inference_loop,
            daemon=True
        )

        self.thread.start()

        print()
        print("=" * 60)
        print("BELTSENTINEL AI")
        print("CAMERA INFERENCE MANAGER")
        print("=" * 60)

        if camera_started:

            print("CAMERA       : CONNECTED")

        else:

            print("CAMERA       : NOT AVAILABLE")

        if self.detector.loaded:

            print("YOLO         : LOADED")

        else:

            print("YOLO         : STANDBY")

        print("INFERENCE    : RUNNING")
        print("=" * 60)

        return True

    # ========================================================
    # INFERENCE LOOP
    # ========================================================

    def _inference_loop(self):

        while self.running:

            frame = self.camera.get_frame()

            # ------------------------------------------------
            # Camera unavailable
            # ------------------------------------------------

            if frame is None:

                with self.lock:

                    self.latest_result = {

                        "detections": [],

                        "status":
                            "CAMERA_NOT_AVAILABLE",

                        "camera_available":
                            False,

                        "model_loaded":
                            self.detector.loaded,

                        "timestamp":
                            time.time()

                    }

                    self.latest_jpeg = None

                time.sleep(0.2)

                continue

            # ------------------------------------------------
            # Camera is working
            # ------------------------------------------------

            result = self.detector.detect(
                frame
            )

            annotated_frame = result.get(
                "frame"
            )

            # ------------------------------------------------
            # JPEG conversion
            # ------------------------------------------------

            jpeg = None

            if annotated_frame is not None:

                success, buffer = cv2.imencode(
                    ".jpg",
                    annotated_frame
                )

                if success:

                    jpeg = buffer.tobytes()

            # ------------------------------------------------
            # Determine status
            # ------------------------------------------------

            if self.detector.loaded:

                inference_status = result.get(
                    "status",
                    "UNKNOWN"
                )

            else:

                inference_status = (
                    "WAITING_FOR_MODEL"
                )

            # ------------------------------------------------
            # Store latest result
            # ------------------------------------------------

            with self.lock:

                self.latest_result = {

                    "detections":
                        result.get(
                            "detections",
                            []
                        ),

                    "status":
                        inference_status,

                    "camera_available":
                        True,

                    "model_loaded":
                        self.detector.loaded,

                    "timestamp":
                        time.time()

                }

                self.latest_jpeg = jpeg

            time.sleep(0.01)

    # ========================================================
    # RESULT
    # ========================================================

    def get_result(self):

        with self.lock:

            return dict(
                self.latest_result
            )

    # ========================================================
    # JPEG
    # ========================================================

    def get_jpeg(self):

        with self.lock:

            return self.latest_jpeg

    # ========================================================
    # STATUS
    # ========================================================

    def get_status(self):

        result = self.get_result()

        return {

            "camera":
                self.camera.get_status(),

            "yolo":
                self.detector.get_status(),

            "inference":
                result

        }

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):

        self.running = False

        if self.thread is not None:

            self.thread.join(
                timeout=1
            )

            self.thread = None

        self.camera.stop()

        print(
            "INFERENCE MANAGER STOPPED"
        )


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    manager = InferenceManager()

    manager.start()

    print()
    print("Inference manager running.")
    print("Press CTRL+C to stop.")

    try:

        while True:

            print(
                manager.get_status()
            )

            time.sleep(3)

    except KeyboardInterrupt:

        manager.stop()