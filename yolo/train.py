from pathlib import Path

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]

DATA_FILE = (
    ROOT /
    "yolo" /
    "data.yaml"
)

RUNS_DIR = (
    ROOT /
    "runs" /
    "detect"
)


def main():

    print("=" * 60)
    print("BELTSENTINEL AI")
    print("YOLO TRAINING")
    print("=" * 60)

    print()
    print("Dataset:")
    print(DATA_FILE)

    print()
    print("Loading pretrained YOLO model...")

    model = YOLO(
        "yolo26n.pt"
    )

    print()
    print("Starting training...")
    print()

    model.train(
        data=str(DATA_FILE),

        epochs=50,

        imgsz=640,

        batch=8,

        project=str(RUNS_DIR),

        name="beltsentinel",

        patience=15,

        pretrained=True,

        workers=0,

        verbose=True
    )

    print()
    print("=" * 60)
    print("TRAINING FINISHED")
    print("=" * 60)

    best_model = (
        RUNS_DIR /
        "beltsentinel" /
        "weights" /
        "best.pt"
    )

    print()
    print("Best model:")
    print(best_model)

    if best_model.exists():

        print()
        print("SUCCESS: best.pt created.")

    else:

        print()
        print(
            "WARNING: best.pt was not found."
        )


if __name__ == "__main__":
    main()