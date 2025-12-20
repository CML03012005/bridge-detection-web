from ultralytics import YOLO

model = YOLO('models/yolov8n.pt')

print("=" * 70)
print("MODEL VERIFICATION")
print("=" * 70)
print(f"Model classes: {model.names}")
print(f"Number of classes: {len(model.names)}")
print("=" * 70)
