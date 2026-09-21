"""
============================================================
BELTSENTINEL AI
CAMERA STREAM ROUTES

PHASE 2 - LIVE CAMERA + YOLO ON DASHBOARD

Provides:
    /api/camera/feed
    /api/camera/status

The Flask application owns the existing InferenceManager.
This module exposes its latest annotated JPEG frames and status.
============================================================
"""

import time

from flask import Blueprint, Response, jsonify


camera_bp = Blueprint("camera_bp", __name__)

_inference_manager = None


def configure_camera_routes(inference_manager):
    """Connect the route module to the application's InferenceManager."""
    global _inference_manager
    _inference_manager = inference_manager


def generate_camera_frames():
    """Generate an MJPEG stream from the latest YOLO-annotated frame."""
    while True:
        manager = _inference_manager

        if manager is None:
            time.sleep(0.2)
            continue

        frame = manager.get_jpeg()

        if frame is None:
            time.sleep(0.05)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Cache-Control: no-cache, no-store, must-revalidate\r\n"
            b"Pragma: no-cache\r\n"
            b"\r\n"
            + frame
            + b"\r\n"
        )


@camera_bp.route("/api/camera/feed")
def camera_feed():
    """Return the live MJPEG camera stream."""
    return Response(
        generate_camera_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@camera_bp.route("/api/camera/status")
def camera_status():
    """Return camera, YOLO and inference status."""
    manager = _inference_manager

    if manager is None:
        return jsonify({
            "camera": {"status": "NOT_INITIALIZED"},
            "yolo": {"loaded": False},
            "inference": {
                "status": "NOT_INITIALIZED",
                "camera_available": False,
                "model_loaded": False,
            },
        })

    return jsonify(manager.get_status())
