import os
import numpy as np
import cv2
import onnxruntime
from onnxruntime.quantization import quantize_static, CalibrationDataReader, QuantType, quant_pre_process

# 1. SETUP PATHS
model_fp32 = 'yolov8n.onnx'
model_prep = 'yolov8n_preprocessed.onnx'
model_int8 = 'yolov8n_static_int8.onnx'
calibration_data_path = 'D:/project/bridge-detection-web/calibration_images'

# 2. PRE-PROCESS THE MODEL
quant_pre_process(model_fp32, model_prep)

# 3. DEFINE CALIBRATION DATA READER
class YOLODataReader(CalibrationDataReader):
    def __init__(self, calibration_image_folder, model_path):
        self.image_folder = calibration_image_folder
        self.image_files = [f for f in os.listdir(calibration_image_folder) if f.endswith(('.jpg', '.png'))]
        self.preprocess_flag = True
        self.enum_data = None
        
        # Get model input name and shape
        session = onnxruntime.InferenceSession(model_path)
        self.input_name = session.get_inputs()[0].name
        self.input_shape = session.get_inputs()[0].shape # Usually [1, 3, 640, 640]

    def get_next(self):
        if self.enum_data is None:
            self.enum_data = iter(self.image_files)
        
        image_file = next(self.enum_data, None)
        if image_file is None:
            return None

        # Load and preprocess image exactly as YOLOv8 expects
        img = cv2.imread(os.path.join(self.image_folder, image_file))
        img = cv2.resize(img, (640, 640))
        img = img.astype(np.float32) / 255.0  # Normalize
        img = img.transpose(2, 0, 1)          # HWC to CHW
        img = np.expand_dims(img, axis=0)     # Add batch dimension
        
        return {self.input_name: img}

# 4. RUN STATIC QUANTIZATION
data_reader = YOLODataReader(calibration_data_path, model_prep)

quantize_static(
    model_input=model_prep,
    model_output=model_int8,
    calibration_data_reader=data_reader,
    quant_format=onnxruntime.quantization.QuantFormat.QDQ, # Recommended for modern hardware
    activation_type=QuantType.QInt8,
    weight_type=QuantType.QInt8
)

print(f"✓ Static INT8 model saved to: {model_int8}")