"""
============================================================
BELTSENTINEL AI
ANOMALY DETECTION ENGINE

MODULE 7.5

IMPORTANT CHANGE:

Encoder position is NOT treated as an abnormality.

The encoder is used for:

    conveyor movement
    position tracking
    joint localization

Sensor anomaly detection uses:

    temperature
    vibration
    acoustic
    motor current

Camera/AI fusion is handled separately.
============================================================
"""


# ============================================================
# THRESHOLDS
# ============================================================

THRESHOLDS = {

    "temperature": {

        "warning": 38.0,

        "critical": 45.0

    },


    "current_amps": {

        "warning": 3.0,

        "critical": 4.5

    },


    "vibration_pulses": {

        "warning": 8,

        "critical": 18

    },


    "acoustic_pulses": {

        "warning": 6,

        "critical": 15

    },


    "acoustic_raw": {

        "warning": 600,

        "critical": 850

    }

}


# ============================================================
# CHECK PARAMETER
# ============================================================

def check_parameter(
    name,
    value
):

    reasons = []

    score = 0


    try:

        value = float(value)

    except (
        TypeError,
        ValueError
    ):

        value = 0


    if name not in THRESHOLDS:

        return score, reasons


    threshold = THRESHOLDS[name]


    if value >= threshold["critical"]:

        if name == "temperature":

            score = 30

            reasons.append(
                "Temperature critically elevated"
            )

        elif name == "current_amps":

            score = 30

            reasons.append(
                "Motor current critically elevated"
            )

        elif name == "vibration_pulses":

            score = 30

            reasons.append(
                "Vibration activity critically high"
            )

        elif name == "acoustic_pulses":

            score = 20

            reasons.append(
                "Acoustic event activity critically high"
            )

        elif name == "acoustic_raw":

            score = 20

            reasons.append(
                "Acoustic signal critically elevated"
            )


    elif value >= threshold["warning"]:

        if name == "temperature":

            score = 15

            reasons.append(
                "Temperature elevated"
            )

        elif name == "current_amps":

            score = 15

            reasons.append(
                "Motor current elevated"
            )

        elif name == "vibration_pulses":

            score = 15

            reasons.append(
                "Vibration activity elevated"
            )

        elif name == "acoustic_pulses":

            score = 10

            reasons.append(
                "Acoustic event activity elevated"
            )

        elif name == "acoustic_raw":

            score = 10

            reasons.append(
                "Acoustic signal elevated"
            )


    return score, reasons


# ============================================================
# ANALYZE TELEMETRY
# ============================================================

def analyze_telemetry(data):

    total_score = 0

    reasons = []


    parameters = [

        "temperature",

        "current_amps",

        "vibration_pulses",

        "acoustic_pulses",

        "acoustic_raw"

    ]


    for parameter in parameters:

        value = data.get(
            parameter,
            0
        )


        score, parameter_reasons = (
            check_parameter(
                parameter,
                value
            )
        )


        total_score += score

        reasons.extend(
            parameter_reasons
        )


    total_score = min(
        total_score,
        100
    )


    if total_score >= 60:

        risk_level = "CRITICAL"

        message = (
            "Multiple abnormal sensor "
            "conditions detected."
        )

    elif total_score >= 20:

        risk_level = "WARNING"

        message = (
            "Abnormal sensor activity "
            "detected."
        )

    else:

        risk_level = "NORMAL"

        message = (
            "Sensor parameters are within "
            "configured prototype ranges."
        )


    return {

        "risk_level": risk_level,

        "risk_score": total_score,

        "reasons": reasons,

        "message": message

    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    normal_data = {

        "temperature": 30,

        "current_amps": 1.8,

        "vibration_pulses": 2,

        "acoustic_pulses": 1,

        "acoustic_raw": 250

    }


    anomaly_data = {

        "temperature": 42,

        "current_amps": 4.0,

        "vibration_pulses": 15,

        "acoustic_pulses": 10,

        "acoustic_raw": 700

    }


    print(
        analyze_telemetry(
            normal_data
        )
    )


    print(
        analyze_telemetry(
            anomaly_data
        )
    )