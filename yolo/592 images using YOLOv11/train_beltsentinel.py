from ultralytics import YOLO

DATASET = r"C:\Users\pc\Downloads\BELTSENTINELAI.v1i.yolov8\BELTSENTINELAI_detection\data.yaml"

model = YOLO("yolo11n.pt")

model.train(
    data=DATASET,
    epochs=50,
    imgsz=640,
    batch=8,
    name="beltsentinel",
)