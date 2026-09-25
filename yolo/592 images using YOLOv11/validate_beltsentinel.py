from ultralytics import YOLO

MODEL = r"C:\Users\pc\Downloads\BELTSENTINELAI.v1i.yolov8\runs\detect\beltsentinel\weights\best.pt"

DATA = r"C:\Users\pc\Downloads\BELTSENTINELAI.v1i.yolov8\BELTSENTINELAI_detection\data.yaml"

model = YOLO(MODEL)

metrics = model.val(
    data=DATA,
    split="test",
    imgsz=640,
    batch=8,
    plots=True
)

print("\n==============================")
print("BELTSENTINEL AI TEST RESULTS")
print("==============================")

print(f"Precision    : {metrics.box.mp:.4f}")
print(f"Recall       : {metrics.box.mr:.4f}")
print(f"mAP50        : {metrics.box.map50:.4f}")
print(f"mAP50-95     : {metrics.box.map:.4f}")

print("==============================")
print("Validation completed.")