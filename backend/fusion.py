"""
============================================================
BELTSENTINEL AI
AI + SENSOR FUSION ENGINE

MODULE 7.6

Purpose:
Combine:

    Camera / YOLO
    Vibration
    Acoustic
    Motor Current
    Temperature
    Encoder / Joint Location

to produce a prototype damage and risk assessment.

IMPORTANT:

This is a prototype fusion engine.

A single sensor does NOT prove physical belt damage.

Camera confidence is combined with sensor evidence
to produce a risk assessment.

Current YOLO classes:

    0 -> belt_crack
    1 -> belt_tear
    2 -> edge_damage
    3 -> joint_damage

Current ESP32 telemetry names:

    encoder_pulses
    vibration_events_per_sec
    acoustic_events_per_sec
    acoustic_raw
    temperature
    humidity
    current_amps
    motor_running
    motor_pwm
============================================================
"""


# ============================================================
# YOLO DAMAGE CLASSES
# ============================================================

DAMAGE_CLASSES = {

    "belt_crack": 0,

    "belt_tear": 1,

    "edge_damage": 2,

    "joint_damage": 3

}


# ============================================================
# FUSION THRESHOLDS
# ============================================================

FUSION_THRESHOLDS = {

    # Camera
    "camera_confidence": 50.0,
    "high_camera_confidence": 80.0,

    # Vibration
    "vibration_warning": 8.0,
    "vibration_critical": 18.0,

    # Acoustic events
    "acoustic_warning": 6.0,
    "acoustic_critical": 15.0,

    # Acoustic raw signal
    "acoustic_raw_warning": 600.0,
    "acoustic_raw_critical": 850.0,

    # Motor current
    "current_warning": 3.0,
    "current_critical": 4.5,

    # Temperature
    "temperature_warning": 38.0,
    "temperature_critical": 45.0

}


# ============================================================
# SAFE NUMBER CONVERSION
# ============================================================

def safe_float(value, default=0.0):

    try:

        return float(value)

    except (
        TypeError,
        ValueError
    ):

        return default


# ============================================================
# SENSOR EVIDENCE
# ============================================================

def calculate_sensor_evidence(data):

    if not isinstance(data, dict):

        data = {}


    evidence = 0

    reasons = []


    # --------------------------------------------------------
    # CURRENT ESP32 FIELD NAMES
    # --------------------------------------------------------

    vibration = safe_float(

        data.get(
            "vibration_events_per_sec",
            data.get(
                "vibration_pulses",
                0
            )
        )

    )


    acoustic = safe_float(

        data.get(
            "acoustic_events_per_sec",
            data.get(
                "acoustic_pulses",
                0
            )
        )

    )


    acoustic_raw = safe_float(

        data.get(
            "acoustic_raw",
            0
        )

    )


    current = safe_float(

        data.get(
            "current_amps",
            0
        )

    )


    temperature = safe_float(

        data.get(
            "temperature",
            0
        )

    )


    # ========================================================
    # VIBRATION
    # ========================================================

    if vibration >= FUSION_THRESHOLDS[
        "vibration_critical"
    ]:

        evidence += 25

        reasons.append(
            "High vibration activity"
        )

    elif vibration >= FUSION_THRESHOLDS[
        "vibration_warning"
    ]:

        evidence += 12

        reasons.append(
            "Elevated vibration activity"
        )


    # ========================================================
    # ACOUSTIC EVENTS
    # ========================================================

    if acoustic >= FUSION_THRESHOLDS[
        "acoustic_critical"
    ]:

        evidence += 20

        reasons.append(
            "High acoustic event activity"
        )

    elif acoustic >= FUSION_THRESHOLDS[
        "acoustic_warning"
    ]:

        evidence += 10

        reasons.append(
            "Elevated acoustic event activity"
        )


    # ========================================================
    # ACOUSTIC RAW SIGNAL
    # ========================================================

    if acoustic_raw >= FUSION_THRESHOLDS[
        "acoustic_raw_critical"
    ]:

        evidence += 15

        reasons.append(
            "High acoustic signal level"
        )

    elif acoustic_raw >= FUSION_THRESHOLDS[
        "acoustic_raw_warning"
    ]:

        evidence += 8

        reasons.append(
            "Elevated acoustic signal level"
        )


    # ========================================================
    # MOTOR CURRENT
    # ========================================================

    if current >= FUSION_THRESHOLDS[
        "current_critical"
    ]:

        evidence += 15

        reasons.append(
            "High motor current"
        )

    elif current >= FUSION_THRESHOLDS[
        "current_warning"
    ]:

        evidence += 8

        reasons.append(
            "Elevated motor current"
        )


    # ========================================================
    # TEMPERATURE
    # ========================================================

    if temperature >= FUSION_THRESHOLDS[
        "temperature_critical"
    ]:

        evidence += 15

        reasons.append(
            "High temperature"
        )

    elif temperature >= FUSION_THRESHOLDS[
        "temperature_warning"
    ]:

        evidence += 8

        reasons.append(
            "Elevated temperature"
        )


    return {

        "score": min(
            evidence,
            100
        ),

        "reasons": reasons

    }


# ============================================================
# CAMERA EVIDENCE
# ============================================================

def calculate_camera_evidence(
    detection,
    confidence
):

    confidence = safe_float(
        confidence
    )


    detection = str(
        detection or "NORMAL"
    ).strip().lower()


    # --------------------------------------------------------
    # Normal belt
    # --------------------------------------------------------

    if detection in (
        "",
        "normal",
        "normal_belt"
    ):

        return {

            "score": 0,

            "reasons": []

        }


    # --------------------------------------------------------
    # Camera confidence
    # --------------------------------------------------------

    if confidence >= FUSION_THRESHOLDS[
        "high_camera_confidence"
    ]:

        score = 60

    elif confidence >= FUSION_THRESHOLDS[
        "camera_confidence"
    ]:

        score = 40

    elif confidence >= 25.0:

        # Low-confidence detection is treated
        # as supporting evidence only.

        score = 15

    else:

        score = 0


    reasons = []


    if score > 0:

        reasons.append(

            f"Camera detected {detection} "
            f"with {confidence:.2f}% confidence"

        )


    return {

        "score": score,

        "reasons": reasons

    }


# ============================================================
# COMPLETE FUSION
# ============================================================

def analyze_fusion(
    telemetry,
    detection="NORMAL",
    confidence=0.0,
    joint=None
):

    if not isinstance(
        telemetry,
        dict
    ):

        telemetry = {}


    # --------------------------------------------------------
    # Sensor evidence
    # --------------------------------------------------------

    sensor = calculate_sensor_evidence(
        telemetry
    )


    # --------------------------------------------------------
    # Camera evidence
    # --------------------------------------------------------

    camera = calculate_camera_evidence(

        detection,

        confidence

    )


    # --------------------------------------------------------
    # Total score
    # --------------------------------------------------------

    total_score = min(

        sensor["score"]
        +
        camera["score"],

        100

    )


    reasons = (

        camera["reasons"]
        +
        sensor["reasons"]

    )


    # ========================================================
    # RISK LEVEL
    # ========================================================

    if total_score >= 70:

        risk_level = "CRITICAL"

    elif total_score >= 30:

        risk_level = "WARNING"

    else:

        risk_level = "NORMAL"


    # ========================================================
    # DAMAGE DETECTION
    # ========================================================

    detection_text = str(
        detection or "NORMAL"
    ).strip()


    detection_lower = detection_text.lower()


    damage_detected = (

        detection_lower
        not in (
            "",
            "normal",
            "normal_belt"
        )

        and

        safe_float(
            confidence
        ) >= 50.0

    )


    # ========================================================
    # STATUS
    # ========================================================

    if damage_detected:

        status = "DAMAGED"

    elif risk_level == "CRITICAL":

        status = "CRITICAL"

    elif risk_level == "WARNING":

        status = "WARNING"

    else:

        status = "NORMAL"


    # ========================================================
    # MESSAGE
    # ========================================================

    if damage_detected:

        if joint:

            message = (

                f"AI detected {detection_text} "
                f"near {joint}."

            )

        else:

            message = (

                f"AI detected "
                f"{detection_text}."

            )


    elif risk_level == "CRITICAL":

        message = (

            "Multiple abnormal conditions "
            "detected by sensor fusion."

        )


    elif risk_level == "WARNING":

        if detection_lower not in (
            "",
            "normal",
            "normal_belt"
        ):

            message = (

                f"Possible {detection_text} detected. "
                "Sensor inspection recommended."

            )

        else:

            message = (

                "Abnormal sensor activity detected. "
                "Inspection recommended."

            )


    else:

        if detection_lower not in (
            "",
            "normal",
            "normal_belt"
        ):

            message = (

                f"Low-confidence {detection_text} "
                "observation detected."

            )

        else:

            message = (

                "Camera and sensor parameters "
                "are within prototype ranges."

            )


    # ========================================================
    # RESULT
    # ========================================================

    return {

        "risk_level":
            risk_level,

        "risk_score":
            round(
                total_score,
                2
            ),

        "status":
            status,

        "damage_detected":
            damage_detected,

        "detection":
            detection_text,

        "confidence":
            round(
                safe_float(
                    confidence
                ),
                2
            ),

        "joint":
            joint,

        "camera_score":
            camera["score"],

        "sensor_score":
            sensor["score"],

        "reasons":
            reasons,

        "message":
            message

    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("BELTSENTINEL AI")
    print("SENSOR FUSION ENGINE TEST")
    print("=" * 70)


    # --------------------------------------------------------
    # NORMAL
    # --------------------------------------------------------

    normal = {

        "encoder_pulses": 4706,

        "vibration_events_per_sec": 2,

        "acoustic_events_per_sec": 1,

        "acoustic_raw": 250,

        "temperature": 30,

        "humidity": 65,

        "current_amps": 0.0,

        "motor_running": True,

        "motor_pwm": 150

    }


    print()
    print("NORMAL SYSTEM:")
    print()

    print(

        analyze_fusion(

            normal,

            "NORMAL",

            0,

            "Joint 1"

        )

    )


    # --------------------------------------------------------
    # CAMERA + SENSOR ANOMALY
    # --------------------------------------------------------

    damaged = {

        "encoder_pulses": 4763,

        "vibration_events_per_sec": 15,

        "acoustic_events_per_sec": 10,

        "acoustic_raw": 700,

        "temperature": 40,

        "humidity": 70,

        "current_amps": 0.0,

        "motor_running": True,

        "motor_pwm": 150

    }


    print()
    print("CAMERA + SENSOR ANOMALY:")
    print()

    print(

        analyze_fusion(

            damaged,

            "joint_damage",

            92.4,

            "Joint 3"

        )

    )


    # --------------------------------------------------------
    # LOW CONFIDENCE CAMERA TEST
    # --------------------------------------------------------

    low_confidence = {

        "encoder_pulses": 4763,

        "vibration_events_per_sec": 2,

        "acoustic_events_per_sec": 1,

        "acoustic_raw": 250,

        "temperature": 30,

        "humidity": 65,

        "current_amps": 0.0,

        "motor_running": True,

        "motor_pwm": 150

    }


    print()
    print("LOW CONFIDENCE CAMERA DETECTION:")
    print()

    print(

        analyze_fusion(

            low_confidence,

            "joint_damage",

            27.34,

            "Joint 3"

        )

    )


    print()
    print("=" * 70)
    print("FUSION TEST COMPLETE")
    print("=" * 70)