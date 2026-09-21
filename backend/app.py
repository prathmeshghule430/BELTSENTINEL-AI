"""
============================================================
BELTSENTINEL AI
INTELLIGENT CONVEYOR MONITORING SYSTEM

MODULE 7.10

Integrated:

    Telemetry
    SQLite
    Anomaly Engine
    AI Detection
    Sensor Fusion
    Five-Joint Localization
    Alerts
    Camera
    YOLO
    Dashboard

Architecture:

ESP32
   ↓
Sensor Telemetry
   ↓
Flask Backend
   ↓
Anomaly + Fusion
   ↓
Camera + YOLO
   ↓
Joint Tracker
   ↓
SQLite
   ↓
Dashboard

============================================================
"""

import os
import sys
import atexit
import json
import threading
from pathlib import Path
from datetime import datetime

from flask import (
    Flask,
    jsonify,
    request,
    send_from_directory,
    Response
)


# ============================================================
# OPTIONAL WEB PUSH LIBRARY
# ============================================================

try:
    from pywebpush import webpush, WebPushException
    WEBPUSH_AVAILABLE = True
except Exception:
    webpush = None
    WebPushException = Exception
    WEBPUSH_AVAILABLE = False


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except Exception:
    pass


# ============================================================
# MAKE BACKEND MODULES IMPORTABLE
# ============================================================

BACKEND_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# ============================================================
# CONFIG
# ============================================================

from config import (
    SYSTEM_NAME,
    SYSTEM_DESCRIPTION,
    MODE,
    JOINTS,
    YOLO_CLASSES,
    SERVER_HOST,
    SERVER_PORT
)


# ============================================================
# DATABASE
# ============================================================

from database import (
    initialize_database,
    save_telemetry,
    save_detection,
    save_alert,
    get_recent_telemetry,
    get_recent_detections,
    get_recent_alerts
)


# ============================================================
# ANOMALY
# ============================================================

from anomaly import (
    analyze_telemetry
)


# ============================================================
# FUSION
# ============================================================

from fusion import (
    analyze_fusion
)


# ============================================================
# JOINT TRACKER
# ============================================================

from joint_tracker import (
    get_current_joint_information,
    get_joint_information,
    JOINT_POSITIONS,
    TOTAL_CONVEYOR_PULSES,
    JOINT_TOLERANCE_COUNTS
)

# ============================================================
# ADDITIVE SIH INTELLIGENCE LAYER
# ============================================================
from intelligence import (
    initialize_intelligence_database,
    record_snapshot,
    calculate_prediction,
    digital_twin_state,
    maintenance_recommendations,
    future_sensor_readiness,
    scada_ready_payload
)


# ============================================================
# CAMERA
# ============================================================

from camera.inference import (
    InferenceManager
)


# ============================================================
# CAMERA STREAM ROUTES
# ============================================================

from backend.camera_routes import (
    camera_bp,
    configure_camera_routes
)


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)


# ============================================================
# DASHBOARD DIRECTORY
# ============================================================

DASHBOARD_DIR = os.path.join(
    BASE_DIR,
    "dashboard"
)


# ============================================================
# CAMERA MANAGER
# ============================================================

inference_manager = InferenceManager(
    camera_index=1,
    model_path=os.path.join(
        BASE_DIR,
        "models",
        "best.pt"
    )
)


# ============================================================
# CONNECT CAMERA ROUTES
# ============================================================

configure_camera_routes(
    inference_manager
)

app.register_blueprint(
    camera_bp
)


# ============================================================
# WEB PUSH CONFIGURATION
# ============================================================

PUSH_SUBSCRIPTIONS_FILE = Path(
    os.getenv(
        "PUSH_SUBSCRIPTIONS_FILE",
        os.path.join(BASE_DIR, "push_subscriptions.json")
    )
)

VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "").strip()
VAPID_PRIVATE_KEY_FILE = os.getenv(
    "VAPID_PRIVATE_KEY_FILE",
    os.path.join(BASE_DIR, "vapid_private.pem")
).strip()
if VAPID_PRIVATE_KEY_FILE and not os.path.isabs(VAPID_PRIVATE_KEY_FILE):
    VAPID_PRIVATE_KEY_FILE = os.path.join(
        BASE_DIR,
        VAPID_PRIVATE_KEY_FILE
    )
VAPID_SUBJECT = os.getenv(
    "VAPID_SUBJECT",
    "mailto:admin@example.com"
).strip()

push_lock = threading.Lock()


def load_push_subscriptions():
    try:
        if not PUSH_SUBSCRIPTIONS_FILE.exists():
            return []
        data = json.loads(
            PUSH_SUBSCRIPTIONS_FILE.read_text(encoding="utf-8")
        )
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_push_subscriptions(subscriptions):
    PUSH_SUBSCRIPTIONS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )
    temp_file = PUSH_SUBSCRIPTIONS_FILE.with_suffix(".tmp")
    temp_file.write_text(
        json.dumps(subscriptions, indent=2),
        encoding="utf-8"
    )
    temp_file.replace(PUSH_SUBSCRIPTIONS_FILE)


def push_is_configured():
    return bool(
        WEBPUSH_AVAILABLE
        and VAPID_PUBLIC_KEY
        and os.path.exists(VAPID_PRIVATE_KEY_FILE)
        and VAPID_SUBJECT
    )


def send_web_push(payload):
    """Send a push notification to all registered browsers."""

    if not push_is_configured():
        return {
            "sent": 0,
            "removed": 0,
            "configured": False
        }

    with push_lock:
        subscriptions = load_push_subscriptions()
        if not subscriptions:
            return {
                "sent": 0,
                "removed": 0,
                "configured": True
            }

        remaining = []
        sent = 0
        removed = 0

        for subscription in subscriptions:
            try:
                webpush(
                    subscription_info=subscription,
                    data=json.dumps(payload),
                    vapid_private_key=VAPID_PRIVATE_KEY_FILE,
                    vapid_claims={"sub": VAPID_SUBJECT}
                )
                remaining.append(subscription)
                sent += 1
            except WebPushException as exc:
                # 404/410 means the browser subscription is no longer valid.
                status_code = getattr(
                    getattr(exc, "response", None),
                    "status_code",
                    None
                )
                if status_code in (404, 410):
                    removed += 1
                else:
                    remaining.append(subscription)
                    print(f"WEB PUSH WARNING: {exc}")
            except Exception as exc:
                remaining.append(subscription)
                print(f"WEB PUSH ERROR: {exc}")

        save_push_subscriptions(remaining)

        return {
            "sent": sent,
            "removed": removed,
            "configured": True
        }


def queue_alert_push(alert):
    """Queue a push notification without blocking the telemetry request."""

    severity = str(
        alert.get("severity", "")
    ).upper()

    if severity not in ("WARNING", "CRITICAL"):
        return

    payload = {
        "title": (
            "BELTSENTINEL AI — CRITICAL"
            if severity == "CRITICAL"
            else "BELTSENTINEL AI — WARNING"
        ),
        "body": (
            f"{alert.get('message', 'Conveyor alert')}"
            f" | {alert.get('joint') or 'System'}"
        ),
        "severity": severity,
        "alert": alert,
        "telemetry": dict(telemetry_data),
        "risk": dict(risk_data),
        "detection": dict(ai_detection),
        "timestamp": datetime.now().isoformat(),
        "url": "/#alerts"
    }

    threading.Thread(
        target=send_web_push,
        args=(payload,),
        daemon=True
    ).start()


# ============================================================
# SYSTEM STATE
# ============================================================

system_data = {

    "system": SYSTEM_NAME,

    "description": SYSTEM_DESCRIPTION,

    "status": "ONLINE",

    "mode": MODE,

    "last_update": None
}


# ============================================================
# TELEMETRY
#
# These names match the CURRENT ESP32 firmware.
# ============================================================

telemetry_data = {

    "encoder_pulses": 0,

    "vibration_events_per_sec": 0.0,

    "acoustic_events_per_sec": 0.0,

    "acoustic_raw": 0.0,

    "temperature": 0.0,

    "humidity": 0.0,

    # ACS712 is currently NOT connected.
    # Keep this at 0.0 until a real current
    # sensor is connected and calibrated.
    "current_amps": 0.0,

    "motor_running": False,

    "motor_pwm": 150
}

# Optional future hardware channels are kept separately so they do not
# change the existing dashboard telemetry contract.
future_sensor_data = {
    "belt_load_kg": None,
    "belt_tension_kn": None,
    "alignment_mm": None,
    "thermal_max_c": None,
    "thermal_hotspot_count": None
}


# ============================================================
# AI DETECTION
# ============================================================

ai_detection = {

    "detection": "NORMAL",

    "confidence": 0.0,

    "joint": None,

    "status": "NORMAL",

    "timestamp": None,

    "source": "NONE"
}


# ============================================================
# RISK
# ============================================================

risk_data = {

    "risk_level": "NORMAL",

    "risk_score": 0,

    "status": "NORMAL",

    "damage_detected": False,

    "detection": "NORMAL",

    "confidence": 0.0,

    "joint": None,

    "camera_score": 0,

    "sensor_score": 0,

    "reasons": [],

    "message": "System operating normally."
}


# ============================================================
# CURRENT JOINT
# ============================================================

current_joint_state = {

    "joint_id": 1,

    "joint_name": "Joint 1",

    "encoder_position": 0,

    "calibrated_position": JOINT_POSITIONS.get(
        1,
        0
    ),

    "distance": 0
}


# ============================================================
# JOINT STATUS
# ============================================================

joint_status_state = {

    str(joint_id): {

        "id": joint_id,

        "name": joint_name,

        "position": JOINT_POSITIONS.get(
            joint_id,
            0
        ),

        "status": "NORMAL",

        "is_current": False,

        "damage_source": None

    }

    for joint_id, joint_name
    in JOINTS.items()

}


# ============================================================
# LAST CAMERA DETECTION
# ============================================================

last_camera_signature = None


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

initialize_database()
initialize_intelligence_database()


# ============================================================
# CURRENT JOINT UPDATE
# ============================================================

def update_current_joint(
    encoder_position
):

    global current_joint_state

    try:

        encoder_position = int(
            encoder_position
        )

    except (
        TypeError,
        ValueError
    ):

        encoder_position = 0


    information = (
        get_current_joint_information(
            encoder_position
        )
    )


    current_joint_state = information


    current_id = information.get(
        "joint_id"
    )


    for joint_key in joint_status_state:

        joint_status_state[
            joint_key
        ][
            "is_current"
        ] = (

            int(joint_key)
            ==
            current_id

        )


    return current_joint_state


# ============================================================
# APPLY DETECTION TO JOINT
# ============================================================

def apply_detection_to_joint(
    detection,
    confidence,
    joint
):

    detection_text = str(
        detection or "NORMAL"
    ).upper()


    try:

        confidence = float(
            confidence
        )

    except (
        TypeError,
        ValueError
    ):

        confidence = 0.0


    # --------------------------------------------------------
    # NORMAL DETECTION
    # --------------------------------------------------------

    if detection_text in (
        "NORMAL",
        "NORMAL_BELT"
    ):

        return


    # --------------------------------------------------------
    # Only sufficiently confident detections affect joints
    # --------------------------------------------------------

    if confidence < 50.0:

        return


    # --------------------------------------------------------
    # Determine joint
    # --------------------------------------------------------

    if not joint:

        joint_id = (
            current_joint_state.get(
                "joint_id"
            )
        )

        if joint_id:

            joint = (
                f"Joint {joint_id}"
            )


    # --------------------------------------------------------
    # Apply status
    # --------------------------------------------------------

    if joint:

        for joint_id in joint_status_state:

            joint_name = (
                joint_status_state[
                    joint_id
                ][
                    "name"
                ]
            )


            if (
                joint_name.lower()
                ==
                str(joint).lower()
            ):

                joint_status_state[
                    joint_id
                ][
                    "status"
                ] = "DAMAGED"


                joint_status_state[
                    joint_id
                ][
                    "damage_source"
                ] = "AI/FUSION"


# ============================================================
# RESET CAMERA DETECTION TO NORMAL
# ============================================================

def reset_camera_detection_to_normal():

    global ai_detection
    global risk_data
    global last_camera_signature


    # --------------------------------------------------------
    # Clear the old camera detection.
    #
    # IMPORTANT:
    # This does NOT erase previously marked joint damage.
    # Joint damage status remains available for the dashboard.
    # --------------------------------------------------------

    ai_detection = {

        "detection": "NORMAL",

        "confidence": 0.0,

        "joint": None,

        "status": "NORMAL",

        "timestamp": datetime.now().isoformat(),

        "source": "CAMERA_YOLO"

    }


    # --------------------------------------------------------
    # Recalculate risk using sensors only.
    # --------------------------------------------------------

    risk_data = analyze_fusion(

        telemetry_data,

        "NORMAL",

        0.0,

        current_joint_state.get(
            "joint_name"
        )

    )


    last_camera_signature = None


# ============================================================
# CAMERA → AI DETECTION
# ============================================================

def process_camera_detection():

    global ai_detection
    global risk_data
    global last_camera_signature


    # --------------------------------------------------------
    # Get latest inference result
    # --------------------------------------------------------

    try:

        result = (
            inference_manager.get_result()
        )

    except Exception:

        return


    if not isinstance(
        result,
        dict
    ):

        return


    detections = result.get(
        "detections",
        []
    )


    # --------------------------------------------------------
    # No YOLO model
    # --------------------------------------------------------

    if not result.get(
        "model_loaded",
        False
    ):

        return


    # --------------------------------------------------------
    # CAMERA NOT AVAILABLE
    # --------------------------------------------------------

    if not result.get(
        "camera_available",
        False
    ):

        return


    # --------------------------------------------------------
    # NO DETECTION
    #
    # IMPORTANT FIX:
    # Previously this returned without clearing the
    # previous detection.
    # --------------------------------------------------------

    if not detections:

        reset_camera_detection_to_normal()

        return


    # --------------------------------------------------------
    # Find highest-confidence detection
    # --------------------------------------------------------

    valid_detections = []


    for item in detections:

        if not isinstance(
            item,
            dict
        ):

            continue


        try:

            item_confidence = float(
                item.get(
                    "confidence",
                    0
                )
            )

        except (
            TypeError,
            ValueError
        ):

            item_confidence = 0.0


        valid_detections.append(
            (
                item_confidence,
                item
            )
        )


    if not valid_detections:

        reset_camera_detection_to_normal()

        return


    valid_detections.sort(
        key=lambda pair: pair[0],
        reverse=True
    )


    detection = (
        valid_detections[0][1]
    )


    # --------------------------------------------------------
    # Class name
    # --------------------------------------------------------

    class_name = str(
        detection.get(
            "class_name",
            "NORMAL"
        )
    )


    # --------------------------------------------------------
    # Confidence
    #
    # YOLO returns 0.0–1.0.
    # Dashboard/fusion uses percentage.
    # --------------------------------------------------------

    try:

        confidence = (

            float(
                detection.get(
                    "confidence",
                    0
                )
            )
            *
            100.0

        )

    except (
        TypeError,
        ValueError
    ):

        confidence = 0.0


    confidence = max(
        0.0,
        min(
            confidence,
            100.0
        )
    )


    # --------------------------------------------------------
    # Current conveyor joint
    # --------------------------------------------------------

    joint_id = (
        current_joint_state.get(
            "joint_id"
        )
    )


    joint = None


    if joint_id:

        joint = (
            f"Joint {joint_id}"
        )


    # --------------------------------------------------------
    # Normalize normal class
    # --------------------------------------------------------

    class_upper = str(
        class_name
    ).upper()


    is_normal = class_upper in (
        "NORMAL",
        "NORMAL_BELT"
    )


    # --------------------------------------------------------
    # NORMAL
    # --------------------------------------------------------

    if is_normal:

        reset_camera_detection_to_normal()

        return


    # --------------------------------------------------------
    # Detection status
    #
    # A camera detection itself is treated as a warning-level
    # observation. Fusion determines final risk.
    # --------------------------------------------------------

    detection_status = "WARNING"


    # --------------------------------------------------------
    # Detection signature
    #
    # Used to avoid repeatedly writing exactly the same
    # detection into SQLite.
    # --------------------------------------------------------

    signature = (

        class_name,

        round(
            confidence,
            1
        ),

        joint

    )


    # --------------------------------------------------------
    # Update live AI state FIRST.
    #
    # This is important because the dashboard should always
    # receive the latest YOLO result even when the database
    # entry is a duplicate.
    # --------------------------------------------------------

    timestamp = (
        datetime.now().isoformat()
    )


    ai_detection = {

        "detection":
            class_name,

        "confidence":
            round(
                confidence,
                2
            ),

        "joint":
            joint,

        "status":
            detection_status,

        "timestamp":
            timestamp,

        "source":
            "CAMERA_YOLO"

    }


    # --------------------------------------------------------
    # Fusion
    # --------------------------------------------------------

    risk_data = analyze_fusion(

        telemetry_data,

        class_name,

        confidence,

        joint

    )


    # --------------------------------------------------------
    # Joint state
    #
    # Only >=50% camera confidence can mark a joint damaged.
    # --------------------------------------------------------

    apply_detection_to_joint(

        class_name,

        confidence,

        joint

    )


    # --------------------------------------------------------
    # Avoid duplicate database entries
    # --------------------------------------------------------

    if signature == last_camera_signature:

        return


    last_camera_signature = signature


    # --------------------------------------------------------
    # Database detection
    # --------------------------------------------------------

    save_detection(

        class_name,

        confidence,

        joint,

        risk_data.get(
            "status",
            "WARNING"
        )

    )


    # --------------------------------------------------------
    # Alert
    # --------------------------------------------------------

    if risk_data.get(
        "damage_detected",
        False
    ):

        alert_severity = risk_data.get(
            "risk_level",
            "WARNING"
        )
        alert_message = risk_data.get(
            "message",
            "AI damage detected"
        )
        save_alert(
            "CAMERA_AI",
            alert_severity,
            alert_message,
            joint
        )
        queue_alert_push({
            "alert_type": "CAMERA_AI",
            "severity": alert_severity,
            "message": alert_message,
            "joint": joint,
            "timestamp": datetime.now().isoformat()
        })


# ============================================================
# WEB PUSH API
# ============================================================

@app.route("/api/push/public-key")
def push_public_key():
    return jsonify({
        "success": True,
        "configured": push_is_configured(),
        "public_key": VAPID_PUBLIC_KEY
    })


@app.route("/api/push/status")
def push_status():
    with push_lock:
        count = len(load_push_subscriptions())

    return jsonify({
        "success": True,
        "configured": push_is_configured(),
        "webpush_available": WEBPUSH_AVAILABLE,
        "subscription_count": count
    })


@app.route("/api/push/subscribe", methods=["POST"])
def push_subscribe():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "Invalid push subscription"
        }), 400

    endpoint = data.get("endpoint")
    keys = data.get("keys")

    if not endpoint or not isinstance(keys, dict):
        return jsonify({
            "success": False,
            "message": "Push subscription endpoint and keys are required"
        }), 400

    subscription = {
        "endpoint": str(endpoint),
        "keys": {
            "p256dh": str(keys.get("p256dh", "")),
            "auth": str(keys.get("auth", ""))
        }
    }

    if not subscription["keys"]["p256dh"] or not subscription["keys"]["auth"]:
        return jsonify({
            "success": False,
            "message": "Push subscription keys are incomplete"
        }), 400

    with push_lock:
        subscriptions = load_push_subscriptions()
        subscriptions = [
            item for item in subscriptions
            if item.get("endpoint") != subscription["endpoint"]
        ]
        subscriptions.append(subscription)
        save_push_subscriptions(subscriptions)

    return jsonify({
        "success": True,
        "message": "Push notifications enabled",
        "subscription_count": len(subscriptions)
    })


@app.route("/api/push/unsubscribe", methods=["POST"])
def push_unsubscribe():
    data = request.get_json(silent=True) or {}
    endpoint = data.get("endpoint")

    if not endpoint:
        return jsonify({
            "success": False,
            "message": "Subscription endpoint is required"
        }), 400

    with push_lock:
        subscriptions = load_push_subscriptions()
        filtered = [
            item for item in subscriptions
            if item.get("endpoint") != endpoint
        ]
        save_push_subscriptions(filtered)

    return jsonify({
        "success": True,
        "message": "Push notifications disabled",
        "subscription_count": len(filtered)
    })


@app.route("/api/push/test", methods=["POST"])
def push_test():
    if not push_is_configured():
        return jsonify({
            "success": False,
            "message": "Web Push is not configured. Generate VAPID keys and configure .env first."
        }), 503

    result = send_web_push({
        "title": "BELTSENTINEL AI — TEST",
        "body": "Mobile push notifications are working.",
        "severity": "TEST",
        "url": "/#settings",
        "timestamp": datetime.now().isoformat()
    })

    return jsonify({
        "success": True,
        "message": "Test push dispatched",
        **result
    })


# ============================================================
# SERVICE WORKER
# ============================================================

@app.route("/sw.js")
def service_worker():
    return send_from_directory(
        DASHBOARD_DIR,
        "sw.js",
        mimetype="application/javascript",
        max_age=0
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/")
def dashboard():

    return send_from_directory(

        DASHBOARD_DIR,

        "index.html"

    )


# ============================================================
# CSS
# ============================================================

@app.route(
    "/css/<path:filename>"
)
def dashboard_css(filename):

    return send_from_directory(

        os.path.join(
            DASHBOARD_DIR,
            "css"
        ),

        filename

    )


# ============================================================
# JAVASCRIPT
# ============================================================

@app.route(
    "/js/<path:filename>"
)
def dashboard_js(filename):

    return send_from_directory(

        os.path.join(
            DASHBOARD_DIR,
            "js"
        ),

        filename

    )


# ============================================================
# SYSTEM STATUS
# ============================================================

@app.route(
    "/api/status"
)
def status():

    process_camera_detection()


    return jsonify({

        "system":
            SYSTEM_NAME,

        "description":
            SYSTEM_DESCRIPTION,

        "status":
            system_data[
                "status"
            ],

        "mode":
            system_data[
                "mode"
            ],

        "joints":
            len(JOINTS),

        "last_update":
            system_data[
                "last_update"
            ],

        "risk_level":
            risk_data[
                "risk_level"
            ],

        "risk_score":
            risk_data[
                "risk_score"
            ],

        "current_joint":
            current_joint_state

    })


# ============================================================
# TELEMETRY
# ============================================================

@app.route(
    "/api/telemetry"
)
def telemetry():

    return jsonify(
        telemetry_data
    )


# ============================================================
# TELEMETRY UPDATE
# ============================================================

@app.route(
    "/api/update",
    methods=["POST"]
)
def update_telemetry():

    global telemetry_data
    global system_data
    global risk_data
    global future_sensor_data


    data = request.get_json(
        silent=True
    )


    if not data:

        return jsonify({

            "success":
                False,

            "message":
                "No sensor data received"

        }), 400


    # --------------------------------------------------------
    # Current ESP32 fields
    # --------------------------------------------------------

    fields = [

        "encoder_pulses",

        "vibration_events_per_sec",

        "acoustic_events_per_sec",

        "acoustic_raw",

        "temperature",

        "humidity",

        "current_amps",

        "motor_running",

        "motor_pwm"

    ]

    # Optional future hardware fields. They are stored separately and do
    # not affect the existing telemetry schema or dashboard.
    for optional_field in future_sensor_data:
        if optional_field in data:
            future_sensor_data[optional_field] = data[optional_field]


    for field in fields:

        if field in data:

            telemetry_data[
                field
            ] = data[field]


    # ========================================================
    # NUMERIC NORMALIZATION
    # ========================================================

    try:

        telemetry_data[
            "encoder_pulses"
        ] = int(

            telemetry_data[
                "encoder_pulses"
            ]

        )

    except (
        TypeError,
        ValueError
    ):

        telemetry_data[
            "encoder_pulses"
        ] = 0


    try:

        telemetry_data[
            "vibration_events_per_sec"
        ] = float(

            telemetry_data[
                "vibration_events_per_sec"
            ]

        )

    except (
        TypeError,
        ValueError
    ):

        telemetry_data[
            "vibration_events_per_sec"
        ] = 0.0


    try:

        telemetry_data[
            "acoustic_events_per_sec"
        ] = float(

            telemetry_data[
                "acoustic_events_per_sec"
            ]

        )

    except (
        TypeError,
        ValueError
    ):

        telemetry_data[
            "acoustic_events_per_sec"
        ] = 0.0


    try:

        telemetry_data[
            "acoustic_raw"
        ] = float(

            telemetry_data[
                "acoustic_raw"
            ]

        )

    except (
        TypeError,
        ValueError
    ):

        telemetry_data[
            "acoustic_raw"
        ] = 0.0


    try:

        telemetry_data[
            "temperature"
        ] = float(

            telemetry_data[
                "temperature"
            ]

        )

    except (
        TypeError,
        ValueError
    ):

        telemetry_data[
            "temperature"
        ] = 0.0


    try:

        telemetry_data[
            "humidity"
        ] = float(

            telemetry_data[
                "humidity"
            ]

        )

    except (
        TypeError,
        ValueError
    ):

        telemetry_data[
            "humidity"
        ] = 0.0


    try:

        telemetry_data[
            "current_amps"
        ] = float(

            telemetry_data[
                "current_amps"
            ]

        )

    except (
        TypeError,
        ValueError
    ):

        telemetry_data[
            "current_amps"
        ] = 0.0


    # --------------------------------------------------------
    # Motor running
    # --------------------------------------------------------

    motor_running_value = (
        telemetry_data.get(
            "motor_running",
            False
        )
    )


    if isinstance(
        motor_running_value,
        str
    ):

        telemetry_data[
            "motor_running"
        ] = (

            motor_running_value
            .strip()
            .lower()

            in (
                "true",
                "1",
                "yes",
                "on",
                "running"
            )

        )

    else:

        telemetry_data[
            "motor_running"
        ] = bool(
            motor_running_value
        )


    # --------------------------------------------------------
    # Motor PWM
    # --------------------------------------------------------

    try:

        telemetry_data[
            "motor_pwm"
        ] = int(

            telemetry_data.get(
                "motor_pwm",
                150
            )

        )

    except (
        TypeError,
        ValueError
    ):

        telemetry_data[
            "motor_pwm"
        ] = 150


    # ========================================================
    # SYSTEM TIMESTAMP
    # ========================================================

    system_data[
        "last_update"
    ] = datetime.now().isoformat()


    # ========================================================
    # JOINT LOCALIZATION
    # ========================================================

    current_joint = (
        update_current_joint(

            telemetry_data[
                "encoder_pulses"
            ]

        )
    )


    # ========================================================
    # SAVE TELEMETRY
    # ========================================================

    save_telemetry(
        telemetry_data
    )


    # ========================================================
    # SENSOR ANOMALY
    # ========================================================

    sensor_risk = (
        analyze_telemetry(
            telemetry_data
        )
    )


    # ========================================================
    # CAMERA PROCESSING
    # ========================================================

    process_camera_detection()


    # ========================================================
    # FUSION
    #
    # Recalculate with the latest telemetry and current
    # camera detection.
    # ========================================================

    risk_data = analyze_fusion(

        telemetry_data,

        ai_detection[
            "detection"
        ],

        ai_detection[
            "confidence"
        ],

        ai_detection[
            "joint"
        ]

    )

    # Additive intelligence history. Existing telemetry storage and
    # response contracts remain unchanged.
    try:
        record_snapshot(
            telemetry_data,
            risk_data,
            ai_detection
        )
    except Exception as intelligence_error:
        print(f"INTELLIGENCE SNAPSHOT WARNING: {intelligence_error}")


    return jsonify({

        "success":
            True,

        "message":
            "Telemetry updated successfully",

        "data":
            telemetry_data,

        "sensor_risk":
            sensor_risk,

        "risk":
            risk_data,

        "current_joint":
            current_joint

    })


# ============================================================
# ESP32 TELEMETRY ENDPOINT
# ============================================================

@app.route(
    "/api/esp32/telemetry",
    methods=["POST"]
)
def esp32_telemetry():

    return update_telemetry()


# ============================================================
# RISK
# ============================================================

@app.route(
    "/api/risk"
)
def risk():

    process_camera_detection()


    return jsonify(
        risk_data
    )


# ============================================================
# DETECTION
# ============================================================

@app.route(
    "/api/detection"
)
def detection():

    process_camera_detection()


    return jsonify(
        ai_detection
    )


# ============================================================
# MANUAL DETECTION UPDATE
# ============================================================

@app.route(
    "/api/detection/update",
    methods=["POST"]
)
def update_detection():

    global ai_detection
    global risk_data


    data = request.get_json(
        silent=True
    )


    if not data:

        return jsonify({

            "success":
                False,

            "message":
                "No detection data received"

        }), 400


    detection_name = str(
        data.get(
            "detection",
            "NORMAL"
        )
    )


    confidence = data.get(
        "confidence",
        0
    )


    joint = data.get(
        "joint"
    )


    status = data.get(
        "status",
        "NORMAL"
    )


    try:

        confidence = float(
            confidence
        )

    except (
        TypeError,
        ValueError
    ):

        confidence = 0.0


    ai_detection = {

        "detection":
            detection_name,

        "confidence":
            confidence,

        "joint":
            joint,

        "status":
            status,

        "timestamp":
            datetime.now().isoformat(),

        "source":
            "MANUAL_API"

    }


    risk_data = analyze_fusion(

        telemetry_data,

        detection_name,

        confidence,

        joint

    )


    apply_detection_to_joint(

        detection_name,

        confidence,

        joint

    )


    save_detection(

        detection_name,

        confidence,

        joint,

        status

    )


    if risk_data.get(
        "damage_detected",
        False
    ):

        alert_severity = risk_data.get(
            "risk_level",
            "WARNING"
        )
        alert_message = risk_data.get(
            "message",
            "AI damage detected"
        )
        save_alert(
            "AI_DETECTION",
            alert_severity,
            alert_message,
            joint
        )
        queue_alert_push({
            "alert_type": "AI_DETECTION",
            "severity": alert_severity,
            "message": alert_message,
            "joint": joint,
            "timestamp": datetime.now().isoformat()
        })


    return jsonify({

        "success":
            True,

        "message":
            "AI detection updated",

        "data":
            ai_detection,

        "risk":
            risk_data

    })


# ============================================================
# CAMERA STATUS
# ============================================================

@app.route(
    "/api/camera/status"
)
def camera_status():

    return jsonify(
        inference_manager.get_status()
    )


# ============================================================
# CAMERA FRAME
# ============================================================

@app.route(
    "/api/camera/frame"
)
def camera_frame():

    frame = (
        inference_manager.get_jpeg()
    )


    if frame is None:

        return jsonify({

            "success":
                False,

            "message":
                "Camera frame unavailable"

        }), 503


    return Response(

        frame,

        mimetype="image/jpeg",

        headers={

            "Cache-Control":
                "no-cache, no-store, must-revalidate",

            "Pragma":
                "no-cache",

            "Expires":
                "0"

        }

    )


# ============================================================
# CAMERA LATEST RESULT
# ============================================================

@app.route(
    "/api/camera/result"
)
def camera_result():

    process_camera_detection()


    return jsonify(

        inference_manager.get_result()

    )


# ============================================================
# JOINTS
# ============================================================

@app.route(
    "/api/joints"
)
def joints():

    return jsonify(
        joint_status_state
    )


# ============================================================
# CURRENT JOINT
# ============================================================

@app.route(
    "/api/joints/current"
)
def current_joint():

    return jsonify({

        "success":
            True,

        "current_joint":
            current_joint_state,

        "encoder_position":
            telemetry_data[
                "encoder_pulses"
            ],

        "total_conveyor_pulses":
            TOTAL_CONVEYOR_PULSES

    })


# ============================================================
# CALIBRATION
# ============================================================

@app.route(
    "/api/joints/calibration"
)
def joint_calibration():

    return jsonify({

        "success":
            True,

        "belt_length_cm":
            120.0,

        "joint_spacing_cm":
            24.0,

        "total_conveyor_pulses":
            TOTAL_CONVEYOR_PULSES,

        "joint_positions":
            JOINT_POSITIONS,

        "tolerance_counts":
            JOINT_TOLERANCE_COUNTS,

        "calibration_type":
            "PIECEWISE_PHYSICAL_CALIBRATION",

        "note":
            (
                "Calibrated using measured encoder "
                "positions for the 120 cm prototype belt."
            )

    })


# ============================================================
# JOINT INFORMATION
# ============================================================

@app.route(
    "/api/joints/information"
)
def joint_information():

    return jsonify(
        get_joint_information()
    )


# ============================================================
# YOLO CLASSES
# ============================================================

@app.route(
    "/api/yolo/classes"
)
def yolo_classes():

    return jsonify(
        YOLO_CLASSES
    )


# ============================================================
# ALERTS
# ============================================================

@app.route(
    "/api/alerts",
    methods=["GET"]
)
def alerts():

    limit = request.args.get(

        "limit",

        default=50,

        type=int

    )


    limit = min(

        max(
            limit,
            1
        ),

        500

    )


    return jsonify(

        get_recent_alerts(
            limit
        )

    )


# ============================================================
# CREATE ALERT
# ============================================================

@app.route(
    "/api/alerts",
    methods=["POST"]
)
def create_alert():

    data = request.get_json(
        silent=True
    )


    if not data:

        return jsonify({

            "success":
                False,

            "message":
                "No alert data received"

        }), 400


    alert_type = data.get(
        "alert_type",
        "UNKNOWN"
    )
    alert_severity = data.get(
        "severity",
        "WARNING"
    )
    alert_message = data.get(
        "message",
        "System anomaly detected"
    )
    alert_joint = data.get("joint")

    save_alert(
        alert_type,
        alert_severity,
        alert_message,
        alert_joint
    )
    queue_alert_push({
        "alert_type": alert_type,
        "severity": alert_severity,
        "message": alert_message,
        "joint": alert_joint,
        "timestamp": datetime.now().isoformat()
    })


    return jsonify({

        "success":
            True,

        "message":
            "Alert saved"

    })


# ============================================================
# TELEMETRY HISTORY
# ============================================================

@app.route(
    "/api/telemetry/history"
)
def telemetry_history():

    limit = request.args.get(

        "limit",

        default=100,

        type=int

    )


    limit = min(

        max(
            limit,
            1
        ),

        1000

    )


    return jsonify(

        get_recent_telemetry(
            limit
        )

    )


# ============================================================
# AI DETECTION HISTORY
# ============================================================

@app.route(
    "/api/detection/history"
)
def detection_history():

    limit = request.args.get(
        "limit",
        default=200,
        type=int
    )

    limit = min(max(limit, 1), 1000)

    return jsonify(
        get_recent_detections(limit)
    )


# ============================================================
# HEALTH
# ============================================================

@app.route(
    "/api/health"
)
def health():

    camera_status_data = (
        inference_manager.get_status()
    )


    camera_info = (
        camera_status_data.get(
            "camera",
            {}
        )
    )


    yolo_info = (
        camera_status_data.get(
            "yolo",
            {}
        )
    )


    inference_info = (
        camera_status_data.get(
            "inference",
            {}
        )
    )


    # --------------------------------------------------------
    # Camera status supports the current CameraManager field:
    #
    #     available
    #
    # and also the older possible field:
    #
    #     camera_available
    # --------------------------------------------------------

    camera_available = bool(

        camera_info.get(
            "available",
            camera_info.get(
                "camera_available",
                inference_info.get(
                    "camera_available",
                    False
                )
            )
        )

    )


    yolo_loaded = bool(

        yolo_info.get(
            "loaded",
            inference_info.get(
                "model_loaded",
                False
            )
        )

    )


    return jsonify({

        "system":
            SYSTEM_NAME,

        "backend":
            "READY",

        "database":
            "READY",

        "anomaly_engine":
            "READY",

        "fusion_engine":
            "READY",

        "joint_tracker":
            "READY",

        "camera":
            (
                "READY"
                if camera_available
                else "STANDBY"
            ),

        "yolo":
            (
                "READY"
                if yolo_loaded
                else "STANDBY"
            ),

        "inference":
            (
                "READY"
                if (
                    camera_available
                    and
                    yolo_loaded
                )
                else "STANDBY"
            ),

        "mode":
            MODE

    })


# ============================================================
# API INFORMATION
# ============================================================

@app.route(
    "/api"
)
def api_information():

    return jsonify({

        "system":
            SYSTEM_NAME,

        "description":
            SYSTEM_DESCRIPTION,

        "version":
            "Module 7.10",

        "mode":
            MODE,

        "services": {

            "telemetry":
                "/api/telemetry",

            "telemetry_update":
                "/api/update",

            "esp32_telemetry":
                "/api/esp32/telemetry",

            "telemetry_history":
                "/api/telemetry/history",

            "risk":
                "/api/risk",

            "detection":
                "/api/detection",

            "detection_update":
                "/api/detection/update",

            "camera_status":
                "/api/camera/status",

            "camera_feed":
                "/api/camera/feed",

            "camera_frame":
                "/api/camera/frame",

            "camera_result":
                "/api/camera/result",

            "joints":
                "/api/joints",

            "current_joint":
                "/api/joints/current",

            "joint_calibration":
                "/api/joints/calibration",

            "joint_information":
                "/api/joints/information",

            "yolo_classes":
                "/api/yolo/classes",

            "alerts":
                "/api/alerts",

            "push_public_key":
                "/api/push/public-key",

            "push_status":
                "/api/push/status",

            "push_subscribe":
                "/api/push/subscribe",

            "push_unsubscribe":
                "/api/push/unsubscribe",

            "push_test":
                "/api/push/test",

            "health":
                "/api/health",

            "intelligence_summary":
                "/api/intelligence/summary",

            "intelligence_prediction":
                "/api/intelligence/prediction",

            "maintenance_recommendations":
                "/api/maintenance/recommendations",

            "digital_twin":
                "/api/digital-twin",

            "sensor_readiness":
                "/api/sensors/readiness",

            "future_sensor_values":
                "/api/sensors/future",

            "scada_integration":
                "/api/integration/scada"

        }

    })


# ============================================================
# ADDITIVE SIH INTELLIGENCE APIs
# ============================================================

@app.route("/api/sensors/future")
def future_sensor_values():
    return jsonify({
        "success": True,
        "values": future_sensor_data,
        "source": "OPTIONAL_FUTURE_HARDWARE_OR_SIMULATION"
    })


@app.route("/api/intelligence/prediction")
def intelligence_prediction():
    return jsonify(calculate_prediction())


@app.route("/api/intelligence/summary")
def intelligence_summary():
    prediction = calculate_prediction()
    return jsonify({
        "success": True,
        "prediction": prediction,
        "maintenance": maintenance_recommendations(risk_data, prediction),
        "digital_twin": digital_twin_state(
            telemetry_data,
            risk_data,
            current_joint_state
        ),
    })


@app.route("/api/maintenance/recommendations")
def maintenance_api():
    prediction = calculate_prediction()
    return jsonify({
        "success": True,
        "recommendations": maintenance_recommendations(risk_data, prediction),
        "prediction": prediction,
    })


@app.route("/api/digital-twin")
def digital_twin_api():
    return jsonify(digital_twin_state(
        telemetry_data,
        risk_data,
        current_joint_state
    ))


@app.route("/api/sensors/readiness")
def sensor_readiness_api():
    return jsonify(future_sensor_readiness())


@app.route("/api/integration/scada")
def scada_integration_api():
    return jsonify(scada_ready_payload(
        telemetry_data,
        risk_data,
        current_joint_state
    ))


# ============================================================
# 404
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    return jsonify({

        "success":
            False,

        "error":
            "Endpoint not found"

    }), 404


# ============================================================
# SHUTDOWN
# ============================================================

def shutdown_camera():

    try:

        inference_manager.stop()

    except Exception:

        pass


atexit.register(
    shutdown_camera
)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print()

    print("=" * 70)

    print(
        "BELTSENTINEL AI"
    )

    print(
        "INTELLIGENT CONVEYOR MONITORING SYSTEM"
    )

    print(
        "MODULE 7.10"
    )

    print("=" * 70)

    print()

    print(
        f"System        : {SYSTEM_NAME}"
    )

    print(
        f"Mode          : {MODE}"
    )

    print(
        "Backend       : READY"
    )

    print(
        "Database      : READY"
    )

    print(
        "Anomaly       : READY"
    )

    print(
        "Fusion        : READY"
    )

    print(
        "Joint Tracker : READY"
    )

    print(
        "Camera        : STARTING"
    )

    print(
        "YOLO          : CHECKING MODEL"
    )

    print()

    print(
        "Five-Joint Physical Calibration:"
    )


    for joint_id, position in (
        JOINT_POSITIONS.items()
    ):

        print(

            f"  Joint {joint_id}"
            f" → Encoder Position {position}"

        )


    print()

    print(
        f"Total Conveyor Pulses:"
        f" {TOTAL_CONVEYOR_PULSES}"
    )

    print()

    print(
        f"Joint Tolerance:"
        f" {JOINT_TOLERANCE_COUNTS} counts"
    )

    print()


    # --------------------------------------------------------
    # Start camera
    # --------------------------------------------------------

    inference_manager.start()


    print()

    print(
        f"Dashboard:"
        f" http://127.0.0.1:{SERVER_PORT}/"
    )

    print()

    print(
        "BELTSENTINEL AI BACKEND STARTING..."
    )

    print("=" * 70)

    print()


    app.run(

        host=SERVER_HOST,

        port=SERVER_PORT,

        debug=True,

        use_reloader=False

    )