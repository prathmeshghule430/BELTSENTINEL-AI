"""
============================================================
BELTSENTINEL AI
INTELLIGENT CONVEYOR MONITORING SYSTEM

JOINT TRACKER

Physical calibration:
    Belt length = 120 cm
    Joint spacing = 24 cm
    Number of joints = 5

Measured encoder positions:
    Joint 1 = 4706
    Joint 2 = 4743
    Joint 3 = 4763
    Joint 4 = 4803
    Joint 5 = 4822
    Joint 1 = 4856

This file is compatible with backend/app.py.
============================================================
"""


# ============================================================
# BASIC BELT CONFIGURATION
# ============================================================

BELT_LENGTH_CM = 120.0

JOINT_SPACING_CM = 24.0

NUMBER_OF_JOINTS = 5


# ============================================================
# PHYSICAL ENCODER CALIBRATION
# ============================================================

CALIBRATION_POINTS = [
    {
        "joint_id": 1,
        "joint_name": "Joint 1",
        "distance_cm": 0.0,
        "encoder": 4706
    },

    {
        "joint_id": 2,
        "joint_name": "Joint 2",
        "distance_cm": 24.0,
        "encoder": 4743
    },

    {
        "joint_id": 3,
        "joint_name": "Joint 3",
        "distance_cm": 48.0,
        "encoder": 4763
    },

    {
        "joint_id": 4,
        "joint_name": "Joint 4",
        "distance_cm": 72.0,
        "encoder": 4803
    },

    {
        "joint_id": 5,
        "joint_name": "Joint 5",
        "distance_cm": 96.0,
        "encoder": 4822
    },

    {
        "joint_id": 1,
        "joint_name": "Joint 1",
        "distance_cm": 120.0,
        "encoder": 4856
    }
]


# ============================================================
# COMPATIBILITY VARIABLES REQUIRED BY APP.PY
# ============================================================

# These are the actual measured encoder positions
# for the five physical joints.

JOINT_POSITIONS = {
    1: 4706,
    2: 4743,
    3: 4763,
    4: 4803,
    5: 4822
}


# Total encoder movement around the complete belt loop.

TOTAL_CONVEYOR_PULSES = 150


START_ENCODER = 4706

END_ENCODER = 4856


TOTAL_ENCODER_COUNTS = (
    END_ENCODER -
    START_ENCODER
)


# ============================================================
# JOINT TOLERANCE
# ============================================================

JOINT_TOLERANCE_COUNTS = 8


# ============================================================
# NORMALIZE ENCODER
# ============================================================

def normalize_encoder(encoder_value):
    """
    Convert cumulative encoder count into
    the calibrated 0-149 loop range.
    """

    try:

        encoder_value = int(
            encoder_value
        )

    except (
        TypeError,
        ValueError
    ):

        encoder_value = START_ENCODER


    if TOTAL_CONVEYOR_PULSES <= 0:

        return 0


    normalized = (
        encoder_value -
        START_ENCODER
    ) % TOTAL_CONVEYOR_PULSES


    return normalized


# ============================================================
# NORMALIZED TO ABSOLUTE ENCODER
# ============================================================

def normalized_to_absolute(
    normalized_value
):
    """
    Convert normalized loop position
    back to calibrated encoder range.
    """

    return (
        START_ENCODER +
        normalized_value
    )


# ============================================================
# ENCODER TO PHYSICAL DISTANCE
# ============================================================

def encoder_to_distance_cm(
    encoder_value
):
    """
    Convert encoder count to physical belt distance.

    Uses piecewise interpolation between the
    measured calibration points.
    """

    normalized = normalize_encoder(
        encoder_value
    )


    absolute_encoder = (
        START_ENCODER +
        normalized
    )


    points = CALIBRATION_POINTS


    for index in range(
        len(points) - 1
    ):

        point_1 = points[index]

        point_2 = points[
            index + 1
        ]


        encoder_1 = point_1[
            "encoder"
        ]

        encoder_2 = point_2[
            "encoder"
        ]


        distance_1 = point_1[
            "distance_cm"
        ]

        distance_2 = point_2[
            "distance_cm"
        ]


        if (
            encoder_1 <=
            absolute_encoder <=
            encoder_2
        ):

            encoder_range = (
                encoder_2 -
                encoder_1
            )

            distance_range = (
                distance_2 -
                distance_1
            )


            if encoder_range == 0:

                return (
                    distance_1 %
                    BELT_LENGTH_CM
                )


            ratio = (
                absolute_encoder -
                encoder_1
            ) / encoder_range


            distance = (
                distance_1 +
                ratio *
                distance_range
            )


            return (
                distance %
                BELT_LENGTH_CM
            )


    return 0.0


# ============================================================
# CIRCULAR DISTANCE
# ============================================================

def circular_distance(
    distance_1,
    distance_2
):
    """
    Shortest physical distance between
    two positions on the circular belt.
    """

    difference = abs(
        distance_1 -
        distance_2
    )


    return min(
        difference,
        BELT_LENGTH_CM -
        difference
    )


# ============================================================
# GET ALL JOINTS
# ============================================================

def get_all_joints():
    """
    Return the five physical conveyor joints.
    """

    return [

        {
            "joint_id": 1,
            "joint_name": "Joint 1",
            "distance_cm": 0.0,
            "encoder": 4706
        },

        {
            "joint_id": 2,
            "joint_name": "Joint 2",
            "distance_cm": 24.0,
            "encoder": 4743
        },

        {
            "joint_id": 3,
            "joint_name": "Joint 3",
            "distance_cm": 48.0,
            "encoder": 4763
        },

        {
            "joint_id": 4,
            "joint_name": "Joint 4",
            "distance_cm": 72.0,
            "encoder": 4803
        },

        {
            "joint_id": 5,
            "joint_name": "Joint 5",
            "distance_cm": 96.0,
            "encoder": 4822
        }

    ]


# ============================================================
# GET CURRENT JOINT
# ============================================================

def get_current_joint(
    encoder_value
):
    """
    Determine which physical joint is
    closest to the current encoder position.
    """

    current_distance = (
        encoder_to_distance_cm(
            encoder_value
        )
    )


    joints = get_all_joints()


    nearest_joint = min(

        joints,

        key=lambda joint:
        circular_distance(

            current_distance,

            joint[
                "distance_cm"
            ]

        )

    )


    distance_from_joint = (
        circular_distance(

            current_distance,

            nearest_joint[
                "distance_cm"
            ]

        )
    )


    return {

        "joint_id":
            nearest_joint[
                "joint_id"
            ],

        "joint_name":
            nearest_joint[
                "joint_name"
            ],

        "name":
            nearest_joint[
                "joint_name"
            ],

        "encoder_position":
            int(
                encoder_value
            ),

        "calibrated_position":
            nearest_joint[
                "encoder"
            ],

        "distance":
            round(
                current_distance,
                2
            ),

        "current_distance_cm":
            round(
                current_distance,
                2
            ),

        "joint_distance_cm":
            nearest_joint[
                "distance_cm"
            ],

        "distance_from_joint_cm":
            round(
                distance_from_joint,
                2
            ),

        "near_joint":
            distance_from_joint
            <= (
                JOINT_SPACING_CM /
                2
            )

    }


# ============================================================
# APP.PY COMPATIBILITY
# ============================================================

def get_current_joint_information(
    encoder_value
):
    """
    Compatibility function used by app.py.
    """

    return get_current_joint(
        encoder_value
    )


# ============================================================
# GET JOINT INFORMATION
# ============================================================

def get_joint_information():
    """
    Return complete joint calibration information.

    This function intentionally takes NO argument because
    backend/app.py calls:

        get_joint_information()
    """

    return {

        "success":
            True,

        "belt_length_cm":
            BELT_LENGTH_CM,

        "joint_spacing_cm":
            JOINT_SPACING_CM,

        "number_of_joints":
            NUMBER_OF_JOINTS,

        "total_conveyor_pulses":
            TOTAL_CONVEYOR_PULSES,

        "start_encoder":
            START_ENCODER,

        "end_encoder":
            END_ENCODER,

        "total_encoder_counts":
            TOTAL_ENCODER_COUNTS,

        "joint_positions":
            JOINT_POSITIONS,

        "joints":
            get_all_joints(),

        "calibration_points":
            CALIBRATION_POINTS,

        "tolerance_counts":
            JOINT_TOLERANCE_COUNTS,

        "calibration_type":
            "Piecewise physical calibration"

    }


# ============================================================
# GET NEAREST JOINT
# ============================================================

def get_nearest_joint(
    encoder_value
):
    """
    Return nearest physical joint.
    """

    return get_current_joint(
        encoder_value
    )


# ============================================================
# CALIBRATION INFORMATION
# ============================================================

def get_calibration_information():
    """
    Return calibration information.
    """

    return {

        "belt_length_cm":
            BELT_LENGTH_CM,

        "joint_spacing_cm":
            JOINT_SPACING_CM,

        "number_of_joints":
            NUMBER_OF_JOINTS,

        "start_encoder":
            START_ENCODER,

        "end_encoder":
            END_ENCODER,

        "total_encoder_counts":
            TOTAL_ENCODER_COUNTS,

        "total_conveyor_pulses":
            TOTAL_CONVEYOR_PULSES,

        "joint_positions":
            JOINT_POSITIONS,

        "calibration_points":
            CALIBRATION_POINTS,

        "tolerance_counts":
            JOINT_TOLERANCE_COUNTS,

        "calibration_type":
            "Piecewise physical calibration"

    }


# ============================================================
# ESTIMATE DEFECT LOCATION
# ============================================================

def estimate_defect_location(
    encoder_value
):
    """
    Estimate the physical location of
    a detected belt defect.
    """

    current = get_current_joint(
        encoder_value
    )


    return {

        "distance_cm":
            current[
                "current_distance_cm"
            ],

        "joint_id":
            current[
                "joint_id"
            ],

        "joint_name":
            current[
                "joint_name"
            ],

        "distance_from_joint_cm":
            current[
                "distance_from_joint_cm"
            ]

    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print(
        "BELTSENTINEL AI - JOINT TRACKER"
    )
    print(
        "PIECEWISE PHYSICAL CALIBRATION"
    )
    print("=" * 70)

    print()

    print(
        f"Belt length       : "
        f"{BELT_LENGTH_CM} cm"
    )

    print(
        f"Joint spacing     : "
        f"{JOINT_SPACING_CM} cm"
    )

    print(
        f"Number of joints  : "
        f"{NUMBER_OF_JOINTS}"
    )

    print(
        f"Total loop counts : "
        f"{TOTAL_CONVEYOR_PULSES}"
    )

    print()

    print(
        "CALIBRATED JOINTS"
    )

    print("-" * 70)

    for joint in get_all_joints():

        print(

            f"{joint['joint_name']:10}"
            f" | Distance = "
            f"{joint['distance_cm']:6.1f} cm"
            f" | Encoder = "
            f"{joint['encoder']}"

        )

    print()

    print(
        "CALIBRATION TEST"
    )

    print("-" * 70)

    test_values = [

        4706,
        4743,
        4763,
        4803,
        4822,
        4856

    ]


    for encoder in test_values:

        result = (
            get_current_joint(
                encoder
            )
        )


        print(

            f"Encoder {encoder}"
            f" -> "
            f"{result['distance']:.1f} cm"
            f" -> "
            f"{result['joint_name']}"

        )

    print()

    print(
        "APP.PY COMPATIBILITY TEST"
    )

    print("-" * 70)

    result_1 = (
        get_current_joint_information(
            4743
        )
    )

    print(
        "get_current_joint_information(4743):"
    )

    print(result_1)

    print()

    result_2 = (
        get_joint_information()
    )

    print(
        "get_joint_information():"
    )

    print(result_2)

    print()

    print(
        "ALL JOINT TRACKER TESTS COMPLETE"
    )

    print("=" * 70)