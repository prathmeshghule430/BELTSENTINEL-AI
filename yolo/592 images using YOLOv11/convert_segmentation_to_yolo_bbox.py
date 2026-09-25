"""
BELTSENTINEL AI
YOLO Segmentation -> YOLO Bounding Box Converter

Converts a Roboflow/YOLO segmentation dataset into standard
YOLO object-detection format.

Original dataset is NOT modified.

Expected source structure:
source/
    train/
        images/
        labels/
    valid/
        images/
        labels/
    test/
        images/
        labels/
    data.yaml

Output:
BELTSENTINELAI_detection/
    train/
        images/
        labels/
    valid/
        images/
        labels/
    test/
        images/
        labels/
    data.yaml
"""

from pathlib import Path
import shutil


# ============================================================
# CHANGE THIS ONLY IF YOUR DATASET IS NOT IN THE SAME FOLDER
# ============================================================

SOURCE_DIR = Path(r".")  # Put the script inside your extracted dataset folder

OUTPUT_DIR = Path(r"BELTSENTINELAI_detection")


# ============================================================
# SETTINGS
# ============================================================

SPLITS = ["train", "valid", "test"]

CLASS_NAMES = [
    "belt_crack",
    "belt_tear",
    "edge_damage",
    "joint_damage",
]

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"
}


def polygon_to_bbox(values):
    """
    Convert normalized polygon coordinates:

        x1 y1 x2 y2 x3 y3 ...

    into YOLO bounding-box format:

        center_x center_y width height
    """

    if len(values) < 6 or len(values) % 2 != 0:
        raise ValueError(
            f"Invalid polygon: expected at least 3 (x,y) points, "
            f"got {len(values) // 2} points."
        )

    xs = values[0::2]
    ys = values[1::2]

    # Clamp coordinates to valid normalized range.
    xs = [max(0.0, min(1.0, x)) for x in xs]
    ys = [max(0.0, min(1.0, y)) for y in ys]

    x_min = min(xs)
    x_max = max(xs)
    y_min = min(ys)
    y_max = max(ys)

    width = x_max - x_min
    height = y_max - y_min

    center_x = (x_min + x_max) / 2.0
    center_y = (y_min + y_max) / 2.0

    # Prevent zero-size boxes.
    if width <= 0 or height <= 0:
        raise ValueError("Polygon produced a zero-size bounding box.")

    return center_x, center_y, width, height


def convert_label_file(src_file, dst_file):
    converted = 0
    skipped = 0
    output_lines = []

    text = src_file.read_text(encoding="utf-8").strip()

    if not text:
        dst_file.write_text("", encoding="utf-8")
        return 0, 0

    for line_number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()

        if not line:
            continue

        parts = line.split()

        try:
            class_id = int(parts[0])
            coordinates = [float(v) for v in parts[1:]]

            if class_id < 0 or class_id >= len(CLASS_NAMES):
                raise ValueError(
                    f"class id {class_id} is outside 0-{len(CLASS_NAMES)-1}"
                )

            cx, cy, w, h = polygon_to_bbox(coordinates)

            output_lines.append(
                f"{class_id} "
                f"{cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"
            )

            converted += 1

        except Exception as exc:
            skipped += 1
            print(
                f"WARNING: {src_file} line {line_number} skipped: {exc}"
            )

    dst_file.parent.mkdir(parents=True, exist_ok=True)
    dst_file.write_text(
        "\n".join(output_lines) + ("\n" if output_lines else ""),
        encoding="utf-8"
    )

    return converted, skipped


def copy_images(src_images, dst_images):
    dst_images.mkdir(parents=True, exist_ok=True)

    count = 0

    if not src_images.exists():
        print(f"WARNING: Missing image folder: {src_images}")
        return 0

    for file in src_images.iterdir():
        if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS:
            shutil.copy2(file, dst_images / file.name)
            count += 1

    return count


def create_data_yaml():
    data = {
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "nc": len(CLASS_NAMES),
        "names": {
            i: name for i, name in enumerate(CLASS_NAMES)
        },
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    yaml_file = OUTPUT_DIR / "data.yaml"

    # Write manually for maximum compatibility with YOLO/Ultralytics.
    lines = [
        "train: train/images",
        "val: valid/images",
        "test: test/images",
        "",
        f"nc: {len(CLASS_NAMES)}",
        "",
        "names:",
    ]

    for i, name in enumerate(CLASS_NAMES):
        lines.append(f"  {i}: {name}")

    yaml_file.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )


def main():
    print("=" * 60)
    print("BELTSENTINEL AI")
    print("YOLO Segmentation -> Bounding Box Converter")
    print("=" * 60)
    print()

    source = SOURCE_DIR.resolve()
    output = OUTPUT_DIR.resolve()

    print(f"Source: {source}")
    print(f"Output: {output}")
    print()

    if not source.exists():
        print("ERROR: Source folder does not exist.")
        print("Put this Python file inside your extracted Roboflow dataset.")
        input("\nPress Enter to exit...")
        return

    if output.exists():
        print(f"WARNING: Output folder already exists:")
        print(output)
        answer = input("Delete and recreate it? (yes/no): ").strip().lower()

        if answer != "yes":
            print("Cancelled. Original dataset was not changed.")
            input("\nPress Enter to exit...")
            return

        shutil.rmtree(output)

    total_images = 0
    total_labels = 0
    total_skipped = 0

    for split in SPLITS:
        src_images = source / split / "images"
        src_labels = source / split / "labels"

        dst_images = output / split / "images"
        dst_labels = output / split / "labels"

        print(f"\n--- {split.upper()} ---")

        image_count = copy_images(src_images, dst_images)
        total_images += image_count

        print(f"Images copied: {image_count}")

        if not src_labels.exists():
            print(f"WARNING: Missing labels folder: {src_labels}")
            continue

        label_files = list(src_labels.glob("*.txt"))

        for label_file in label_files:
            destination = dst_labels / label_file.name

            converted, skipped = convert_label_file(
                label_file,
                destination
            )

            total_labels += converted
            total_skipped += skipped

    create_data_yaml()

    print()
    print("=" * 60)
    print("CONVERSION COMPLETE")
    print("=" * 60)
    print(f"Images copied:       {total_images}")
    print(f"Objects converted:   {total_labels}")
    print(f"Lines skipped:       {total_skipped}")
    print(f"Output folder:       {output}")
    print()
    print("Classes:")
    for i, name in enumerate(CLASS_NAMES):
        print(f"  {i}: {name}")
    print()
    print("A standard YOLO label should now look like:")
    print("3 0.500000 0.400000 0.250000 0.120000")
    print()
    print("Your original Roboflow dataset was NOT modified.")
    print("=" * 60)

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
