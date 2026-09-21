from pathlib import Path

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = (
    ROOT /
    "runs" /
    "detect" /
    "beltsentinel" /
    "weights" /
    "best.pt"
)

DATA_FILE = (
    ROOT /
    "yolo" /
    "data.yaml"
)


def main():

    print("=" * 60)
    print("BELTSENTINEL AI")
    print("YOLO VALIDATION")
    print("=" * 60)

    if not MODEL_PATH.exists():

        print()
        print("ERROR: Trained model not found.")
        print()
        print(
            f"Expected:"
        )
        print(MODEL_PATH)
        print()
        print(
            "Train the model first."
        )

        return

    print()
    print("Loading model:")
    print(MODEL_PATH)

    model = YOLO(
        str(MODEL_PATH)
    )

    print()
    print("Running validation...")

    results = model.val(
        data=str(DATA_FILE),
        imgsz=640
    )

    print()
    print("=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)

    print(results)


if __name__ == "__main__":
    main()