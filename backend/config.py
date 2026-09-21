import os


# ============================================================
# BELTSENTINEL AI - CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)


# ============================================================
# DATABASE
# ============================================================

DATABASE_PATH = os.path.join(
    BASE_DIR,
    "database",
    "beltsentinel.db"
)


# ============================================================
# FLASK SERVER
# ============================================================

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5000


# ============================================================
# SYSTEM INFORMATION
# ============================================================

SYSTEM_NAME = "BELTSENTINEL AI"

SYSTEM_DESCRIPTION = (
    "Intelligent Conveyor Monitoring System"
)

MODE = "LIVE"


# ============================================================
# CONVEYOR JOINTS
# ============================================================

JOINTS = {
    1: "Joint 1",
    2: "Joint 2",
    3: "Joint 3",
    4: "Joint 4",
    5: "Joint 5"
}


# ============================================================
# YOLO MODEL CLASSES
#
# IMPORTANT:
# These MUST exactly match the trained best.pt model.
# ============================================================

YOLO_CLASSES = {
    0: "belt_crack",
    1: "belt_tear",
    2: "edge_damage",
    3: "joint_damage"
}


# ============================================================
# YOLO SETTINGS
# ============================================================

YOLO_MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "best.pt"
)

YOLO_CONFIDENCE = 0.25


# ============================================================
# SENSOR SETTINGS
# ============================================================

SENSOR_SETTINGS = {

    "encoder": {
        "enabled": True,
        "pin_a": 32,
        "pin_b": 33
    },

    "vibration": {
        "enabled": True,
        "pin": 27
    },

    "acoustic": {
        "enabled": True,
        "digital_pin": 26,
        "analog_pin": 34
    },

    "temperature_humidity": {
        "enabled": True,
        "pin": 4
    },

    # ACS712 is intentionally not connected currently.
    "motor_current": {
        "enabled": False,
        "value": 0.0
    }
}


# ============================================================
# MOTOR / L298N
# ============================================================

MOTOR_SETTINGS = {

    "enabled": True,

    "ena_pin": 25,
    "in1_pin": 18,
    "in2_pin": 19,

    "default_pwm": 150
}


# ============================================================
# SAFETY / RISK
# ============================================================

RISK_LEVELS = {
    "NORMAL": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4
}