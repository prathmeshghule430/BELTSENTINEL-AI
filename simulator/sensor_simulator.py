"""
============================================================
BELTSENTINEL AI
INTELLIGENT CONVEYOR MONITORING SYSTEM

MODULE 7.4
AUTOMATIC FIVE-JOINT ENCODER SIMULATOR

Purpose:
Simulate a moving conveyor belt before physical hardware
is connected.

Encoder movement:

J1 → J2 → J3 → J4 → J5 → J1 → ...

The simulator sends telemetry to:

POST /api/update

The Flask backend then:
    1. Stores telemetry
    2. Runs anomaly analysis
    3. Calculates current joint
    4. Sends information to dashboard

IMPORTANT:
The encoder values used here are temporary software
calibration values.

Current prototype calibration:

J1 = 0
J2 = 200
J3 = 400
J4 = 600
J5 = 800

Total conveyor position = 1000 pulses

These values will later be replaced with measurements
from the physical encoder/conveyor.
============================================================
"""

import random
import time
import requests


# ============================================================
# SERVER CONFIGURATION
# ============================================================

API_URL = "http://127.0.0.1:5000/api/update"


# ============================================================
# SIMULATION CONFIGURATION
# ============================================================

UPDATE_INTERVAL = 1.0

TOTAL_CONVEYOR_PULSES = 1000

PULSES_PER_UPDATE = 25


# ============================================================
# TEMPORARY FIVE-JOINT POSITIONS
# ============================================================

JOINT_POSITIONS = {

    1: 0,

    2: 200,

    3: 400,

    4: 600,

    5: 800

}


# ============================================================
# NORMAL SENSOR RANGES
# ============================================================

NORMAL_DATA = {

    "vibration_pulses": (0, 3),

    "acoustic_pulses": (0, 2),

    "acoustic_raw": (100, 400),

    "temperature": (25, 35),

    "humidity": (45, 70),

    "current_amps": (0.8, 2.5)

}


# ============================================================
# ANOMALY SENSOR RANGES
# ============================================================

ANOMALY_DATA = {

    "vibration_pulses": (10, 25),

    "acoustic_pulses": (8, 20),

    "acoustic_raw": (600, 950),

    "temperature": (38, 45),

    "humidity": (55, 75),

    "current_amps": (3.0, 4.8)

}


# ============================================================
# GENERATE NORMAL SENSOR DATA
# ============================================================

def generate_normal_data():

    return {

        "vibration_pulses": random.randint(
            NORMAL_DATA["vibration_pulses"][0],
            NORMAL_DATA["vibration_pulses"][1]
        ),

        "acoustic_pulses": random.randint(
            NORMAL_DATA["acoustic_pulses"][0],
            NORMAL_DATA["acoustic_pulses"][1]
        ),

        "acoustic_raw": random.randint(
            NORMAL_DATA["acoustic_raw"][0],
            NORMAL_DATA["acoustic_raw"][1]
        ),

        "temperature": round(
            random.uniform(
                NORMAL_DATA["temperature"][0],
                NORMAL_DATA["temperature"][1]
            ),
            1
        ),

        "humidity": round(
            random.uniform(
                NORMAL_DATA["humidity"][0],
                NORMAL_DATA["humidity"][1]
            ),
            1
        ),

        "current_amps": round(
            random.uniform(
                NORMAL_DATA["current_amps"][0],
                NORMAL_DATA["current_amps"][1]
            ),
            3
        )

    }


# ============================================================
# GENERATE ANOMALY SENSOR DATA
# ============================================================

def generate_anomaly_data():

    return {

        "vibration_pulses": random.randint(
            ANOMALY_DATA["vibration_pulses"][0],
            ANOMALY_DATA["vibration_pulses"][1]
        ),

        "acoustic_pulses": random.randint(
            ANOMALY_DATA["acoustic_pulses"][0],
            ANOMALY_DATA["acoustic_pulses"][1]
        ),

        "acoustic_raw": random.randint(
            ANOMALY_DATA["acoustic_raw"][0],
            ANOMALY_DATA["acoustic_raw"][1]
        ),

        "temperature": round(
            random.uniform(
                ANOMALY_DATA["temperature"][0],
                ANOMALY_DATA["temperature"][1]
            ),
            1
        ),

        "humidity": round(
            random.uniform(
                ANOMALY_DATA["humidity"][0],
                ANOMALY_DATA["humidity"][1]
            ),
            1
        ),

        "current_amps": round(
            random.uniform(
                ANOMALY_DATA["current_amps"][0],
                ANOMALY_DATA["current_amps"][1]
            ),
            3
        )

    }


# ============================================================
# GET JOINT FROM ENCODER POSITION
# ============================================================

def get_nearest_joint(position):

    position = position % TOTAL_CONVEYOR_PULSES

    nearest_joint = None

    smallest_distance = None

    for joint_id, joint_position in JOINT_POSITIONS.items():

        distance = abs(
            position - joint_position
        )

        circular_distance = min(
            distance,
            TOTAL_CONVEYOR_PULSES - distance
        )

        if (
            smallest_distance is None
            or circular_distance < smallest_distance
        ):

            smallest_distance = circular_distance

            nearest_joint = joint_id

    return nearest_joint


# ============================================================
# CREATE TELEMETRY DATA
# ============================================================

def create_telemetry(
    encoder_position,
    anomaly=False
):

    if anomaly:

        sensor_data = generate_anomaly_data()

    else:

        sensor_data = generate_normal_data()


    data = {

        "encoder_pulses": encoder_position,

        "vibration_pulses":
            sensor_data["vibration_pulses"],

        "acoustic_pulses":
            sensor_data["acoustic_pulses"],

        "acoustic_raw":
            sensor_data["acoustic_raw"],

        "temperature":
            sensor_data["temperature"],

        "humidity":
            sensor_data["humidity"],

        "current_amps":
            sensor_data["current_amps"]

    }


    return data


# ============================================================
# SEND DATA TO FLASK
# ============================================================

def send_data(data):

    try:

        response = requests.post(

            API_URL,

            json=data,

            timeout=2

        )


        if response.status_code == 200:

            result = response.json()

            current_joint = result.get(
                "current_joint",
                {}
            )


            joint_name = current_joint.get(
                "joint_name",
                "Unknown"
            )


            risk = result.get(
                "risk",
                {}
            )


            risk_level = risk.get(
                "risk_level",
                "UNKNOWN"
            )


            risk_score = risk.get(
                "risk_score",
                0
            )


            print(
                f"ENCODER: "
                f"{data['encoder_pulses']:4d} | "
                f"{joint_name:8s} | "
                f"RISK: {risk_level:8s} | "
                f"SCORE: {risk_score:3d}"
            )


        else:

            print(
                f"SERVER ERROR: "
                f"HTTP {response.status_code}"
            )


    except requests.exceptions.ConnectionError:

        print(
            "ERROR: Flask backend is not running."
        )


    except requests.exceptions.Timeout:

        print(
            "ERROR: Flask backend request timed out."
        )


    except Exception as error:

        print(
            f"ERROR: {error}"
        )


# ============================================================
# DISPLAY JOINT POSITIONS
# ============================================================

def display_joint_positions():

    print()

    print(
        "Temporary Joint Calibration:"
    )

    print(
        "----------------------------"
    )


    for joint_id, position in JOINT_POSITIONS.items():

        print(
            f"Joint {joint_id} "
            f"→ Encoder Position {position}"
        )


    print(
        "----------------------------"
    )

    print(
        f"Total Conveyor Pulses: "
        f"{TOTAL_CONVEYOR_PULSES}"
    )

    print()


# ============================================================
# MAIN SIMULATION
# ============================================================

def main():

    print()

    print(
        "=" * 70
    )

    print(
        "BELTSENTINEL AI"
    )

    print(
        "AUTOMATIC FIVE-JOINT ENCODER SIMULATOR"
    )

    print(
        "MODULE 7.4"
    )

    print(
        "=" * 70
    )

    print()

    print(
        "Simulation mode active."
    )

    print(
        "The virtual conveyor belt is moving."
    )

    print()

    display_joint_positions()

    print(
        "Movement:"
    )

    print(
        "J1 → J2 → J3 → J4 → J5 → J1 ..."
    )

    print()

    print(
        f"Pulse movement per update: "
        f"{PULSES_PER_UPDATE}"
    )

    print(
        f"Update interval: "
        f"{UPDATE_INTERVAL} second"
    )

    print()

    print(
        "Press CTRL+C to stop."
    )

    print()

    print(
        "=" * 70
    )

    print()


    # --------------------------------------------------------
    # Starting encoder position
    # --------------------------------------------------------

    encoder_position = 0


    # --------------------------------------------------------
    # Counter
    # --------------------------------------------------------

    counter = 0


    # --------------------------------------------------------
    # Main loop
    # --------------------------------------------------------

    while True:

        counter += 1


        # ----------------------------------------------------
        # Determine whether to simulate an anomaly
        #
        # Every 40 cycles an abnormal sensor condition
        # is generated for demonstration.
        # ----------------------------------------------------

        anomaly = (

            counter % 40 == 0

        )


        # ----------------------------------------------------
        # Create telemetry
        # ----------------------------------------------------

        data = create_telemetry(

            encoder_position,

            anomaly

        )


        # ----------------------------------------------------
        # Display anomaly message
        # ----------------------------------------------------

        if anomaly:

            joint = get_nearest_joint(
                encoder_position
            )


            print()

            print(
                "!" * 70
            )

            print(
                "SIMULATED SENSOR ANOMALY"
            )

            print(
                f"Current encoder position: "
                f"{encoder_position}"
            )

            print(
                f"Nearest joint: Joint {joint}"
            )

            print(
                "!" * 70
            )


        # ----------------------------------------------------
        # Send telemetry
        # ----------------------------------------------------

        send_data(data)


        # ----------------------------------------------------
        # Move conveyor forward
        # ----------------------------------------------------

        encoder_position += (
            PULSES_PER_UPDATE
        )


        # ----------------------------------------------------
        # Loop around conveyor
        # ----------------------------------------------------

        if (
            encoder_position
            >= TOTAL_CONVEYOR_PULSES
        ):

            encoder_position = (
                encoder_position
                % TOTAL_CONVEYOR_PULSES
            )


            print()

            print(
                ">>> Conveyor completed one full cycle."
            )

            print(
                ">>> Returning to Joint 1."
            )

            print()


        # ----------------------------------------------------
        # Wait before next reading
        # ----------------------------------------------------

        time.sleep(
            UPDATE_INTERVAL
        )


# ============================================================
# PROGRAM START
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print()

        print(
            "=" * 70
        )

        print(
            "BELTSENTINEL AI SIMULATOR STOPPED"
        )

        print(
            "=" * 70
        )

        print()
