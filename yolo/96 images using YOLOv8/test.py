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

TEST_IMAGES = (
    ROOT /
    "yolo" /
    "dataset" /
    "images" /
    "test"
)

OUTPUT_DIR = (
    ROOT /
    "runs" /
    "detect" /
    "test_results"
)


def main():

    print("=" * 60)
    print("BELTSENTINEL AI")
    print("YOLO TEST")
    print("=" * 60)

    if not MODEL_PATH.exists():

        print()
        print("ERROR: best.pt not found.")
        print(MODEL_PATH)
        return

    if not TEST_IMAGES.exists():

        print()
        print("ERROR: Test image folder not found.")
        print(TEST_IMAGES)
        return

    model = YOLO(
        str(MODEL_PATH)
    )

    print()
    print("Running predictions on test images...")

    results = model.predict(
        source=str(TEST_IMAGES),
        imgsz=640,
        conf=0.25,
        save=True,
        project=str(OUTPUT_DIR.parent),
        name=OUTPUT_DIR.name
    )

    print()
    print("TEST COMPLETE")
    print(f"Results: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()