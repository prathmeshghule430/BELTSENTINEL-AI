from pathlib import Path
import sys

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


def main():

    print("=" * 60)
    print("BELTSENTINEL AI")
    print("YOLO IMAGE PREDICTION")
    print("=" * 60)

    if not MODEL_PATH.exists():

        print()
        print("ERROR: Trained model not found.")
        print(MODEL_PATH)
        return

    if len(sys.argv) < 2:

        print()
        print(
            "Usage:"
        )
        print(
            "python yolo/predict.py path_to_image"
        )
        return

    image_path = Path(
        sys.argv[1]
    )

    if not image_path.exists():

        print()
        print("ERROR: Image not found.")
        print(image_path)
        return

    model = YOLO(
        str(MODEL_PATH)
    )

    print()
    print("Image:")
    print(image_path)

    results = model.predict(
        source=str(image_path),
        imgsz=640,
        conf=0.25,
        save=True
    )

    print()
    print("Prediction complete.")

    for result in results:

        if result.boxes is None:
            continue

        for box in result.boxes:

            class_id = int(
                box.cls[0].item()
            )

            confidence = float(
                box.conf[0].item()
            )

            class_name = (
                model.names[class_id]
            )

            print(
                f"{class_name}: "
                f"{confidence * 100:.2f}%"
            )


if __name__ == "__main__":
    main()