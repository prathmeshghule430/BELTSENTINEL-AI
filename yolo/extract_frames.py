import cv2
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

VIDEO_DIR = ROOT / "yolo" / "videos"
OUTPUT_DIR = ROOT / "yolo" / "frames"

FRAME_INTERVAL = 10


def extract_frames(video_path, output_folder):
    video_path = Path(video_path)
    output_folder = Path(output_folder)

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    cap = cv2.VideoCapture(
        str(video_path)
    )

    if not cap.isOpened():
        print(
            f"ERROR: Could not open video: {video_path}"
        )
        return

    frame_number = 0
    saved_frames = 0

    print()
    print("=" * 60)
    print("BELTSENTINEL AI")
    print("VIDEO FRAME EXTRACTION")
    print("=" * 60)
    print(f"Video: {video_path.name}")
    print(f"Output: {output_folder}")
    print(f"Frame interval: {FRAME_INTERVAL}")
    print("=" * 60)

    while True:
        success, frame = cap.read()

        if not success:
            break

        if frame_number % FRAME_INTERVAL == 0:

            filename = (
                f"{video_path.stem}_"
                f"{frame_number:06d}.jpg"
            )

            output_path = (
                output_folder / filename
            )

            cv2.imwrite(
                str(output_path),
                frame
            )

            saved_frames += 1

        frame_number += 1

    cap.release()

    print()
    print("EXTRACTION COMPLETE")
    print(f"Total video frames: {frame_number}")
    print(f"Saved frames: {saved_frames}")
    print("=" * 60)


def main():

    VIDEO_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    videos = []

    for extension in [
        "*.mp4",
        "*.avi",
        "*.mov",
        "*.mkv"
    ]:
        videos.extend(
            VIDEO_DIR.glob(extension)
        )

    if not videos:
        print()
        print("No videos found.")
        print()
        print(
            "Put your videos inside:"
        )
        print(
            VIDEO_DIR
        )
        print()
        return

    for video in videos:

        output_folder = (
            OUTPUT_DIR / video.stem
        )

        extract_frames(
            video,
            output_folder
        )


if __name__ == "__main__":
    main()