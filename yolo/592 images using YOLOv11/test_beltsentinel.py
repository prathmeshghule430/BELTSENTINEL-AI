from ultralytics import YOLO

MODEL = r"C:\Users\pc\Downloads\BELTSENTINELAI.v1i.yolov8\runs\detect\beltsentinel\weights\best.pt"

TEST_IMAGES = r"C:\Users\pc\Downloads\BELTSENTINELAI.v1i.yolov8\BELTSENTINELAI_detection\test\images"

model = YOLO(MODEL)

results = model.predict(
    source=TEST_IMAGES,
    imgsz=640,
    conf=0.25,
    save=True,
    save_txt=True,
)

print("Testing complete.")
print("Predicted images were saved by Ultralytics.")