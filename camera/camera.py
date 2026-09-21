"""
BELTSENTINEL AI
Camera Manager

Supports:
1. USB webcam in future
2. Camera unavailable mode
3. Frame capture
4. JPEG encoding for dashboard streaming
"""

import cv2
import threading
import time


class CameraManager:

    def __init__(self, camera_index=0, width=640, height=480):
        self.camera_index = camera_index
        self.width = width
        self.height = height

        self.camera = None
        self.running = False
        self.thread = None

        self.latest_frame = None
        self.lock = threading.Lock()

        self.camera_available = False
        self.last_error = None

    def start(self):

        if self.running:
            return True

        print("=" * 60)
        print("BELTSENTINEL AI")
        print("CAMERA MANAGER")
        print("=" * 60)

        print(f"Trying camera index: {self.camera_index}")

        self.camera = cv2.VideoCapture(
            self.camera_index,
            cv2.CAP_DSHOW
        )

        if not self.camera.isOpened():

            print("CAMERA NOT AVAILABLE")
            print("System will continue without physical camera.")
            print("Connect USB camera later.")

            self.camera_available = False
            self.running = False

            if self.camera is not None:
                self.camera.release()

            self.camera = None

            return False

        self.camera.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            self.width
        )

        self.camera.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            self.height
        )

        self.camera_available = True
        self.running = True

        self.thread = threading.Thread(
            target=self._capture_loop,
            daemon=True
        )

        self.thread.start()

        print("CAMERA CONNECTED")
        print(f"Resolution: {self.width}x{self.height}")

        return True

    def _capture_loop(self):

        while self.running:

            if self.camera is None:
                break

            success, frame = self.camera.read()

            if not success:

                self.last_error = (
                    "Camera frame could not be read."
                )

                self.camera_available = False

                time.sleep(0.1)

                continue

            with self.lock:

                self.latest_frame = frame

            self.camera_available = True

            time.sleep(0.01)

    def get_frame(self):

        with self.lock:

            if self.latest_frame is None:
                return None

            return self.latest_frame.copy()

    def get_jpeg(self):

        frame = self.get_frame()

        if frame is None:
            return None

        success, buffer = cv2.imencode(
            ".jpg",
            frame
        )

        if not success:
            return None

        return buffer.tobytes()

    def get_status(self):

        return {
            "available": self.camera_available,
            "running": self.running,
            "camera_index": self.camera_index,
            "width": self.width,
            "height": self.height,
            "error": self.last_error
        }

    def stop(self):

        self.running = False

        if self.thread is not None:
            self.thread.join(timeout=1)

        if self.camera is not None:
            self.camera.release()

        self.camera = None
        self.camera_available = False

        print("CAMERA STOPPED")


if __name__ == "__main__":

    camera = CameraManager()

    if camera.start():

        print("Camera test running.")
        print("Press CTRL+C to stop.")

        try:

            while True:

                frame = camera.get_frame()

                if frame is not None:

                    cv2.imshow(
                        "BELTSENTINEL AI - Camera Test",
                        frame
                    )

                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

                time.sleep(0.01)

        except KeyboardInterrupt:
            pass

        finally:

            camera.stop()
            cv2.destroyAllWindows()

    else:

        print()
        print("No camera detected.")
        print("This is OK for now.")
        print("Connect a USB camera later.")