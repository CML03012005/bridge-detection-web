from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import cv2
import json
from datetime import datetime
from ultralytics import YOLO
import numpy as np
import shutil

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['RESULTS_FOLDER'] = 'static/results'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

# Create necessary folders
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
os.makedirs('data', exist_ok=True)

# Load models
print("Loading models...")
try:
    model_v8 = YOLO('models/yolov8n.pt')
    print("YOLOv8 model loaded")
except Exception as e:
    print(f"YOLOv8 model not found: {e}")
    model_v8 = None

try:
    model_v11 = YOLO('models/yolo11n.pt')
    print("YOLOv11 model loaded")
except Exception as e:
    print(f"YOLOv11 model not found: {e}")
    model_v11 = None

# for storing detection history
HISTORY_FILE = 'data/detection_history.json'

def load_history():
    """Load detection history from JSON file"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []

def save_history(detection):
    """Save detection to history"""
    history = load_history()
    history.append(detection)
    # Keep only last 100 detections
    history = history[-100:]
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def run_inference(image_path, model_version='v8'):
    """Run YOLO inference on image"""
    model = model_v8 if model_version == 'v8' else model_v11
    
    if model is None:
        return None
    
    # Run inference
    results = model.predict(image_path, conf=0.15, iou=0.45)
    
    # result
    result = results[0]
    
    # detection data
    detections = []
    class_counts = {'corrosion': 0, 'crack': 0}
    
    for box in result.boxes:
        cls = int(box.cls[0])
        conf = float(box.conf[0])
        xyxy = box.xyxy[0].cpu().numpy()
        
        class_name = result.names[cls]
        
        detections.append({
            'class': class_name,
            'confidence': round(conf * 100, 2),
            'bbox': [float(x) for x in xyxy]
        })
        
        if class_name in class_counts:
            class_counts[class_name] += 1
    
    # Draw boxes on image
    annotated_img = result.plot()
    
    return {
        'detections': detections,
        'counts': class_counts,
        'total': len(detections),
        'annotated_image': annotated_img,
        'inference_time': round(result.speed['inference'], 2)
    }

@app.route('/')
def index():
    """Main upload page"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard page"""
    history = load_history()
    
    # Calculate statistics
    total_inspections = len(history)
    total_detections = sum(h['total_detections'] for h in history)
    total_cracks = sum(h['counts']['crack'] for h in history)
    total_corrosion = sum(h['counts']['corrosion'] for h in history)
    
    # recent inspections (last 10)
    recent = history[-10:][::-1]  # newest first
    
    stats = {
        'total_inspections': total_inspections,
        'total_detections': total_detections,
        'total_cracks': total_cracks,
        'total_corrosion': total_corrosion,
        'recent_inspections': recent
    }
    
    return render_template('dashboard.html', stats=stats, history=history)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and run inference"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    model_version = request.form.get('model', 'v8')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Use PNG, JPG, or JPEG'}), 400
    
    try:
        # save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # inference
        result = run_inference(filepath, model_version)
        
        if result is None:
            return jsonify({'error': f'Model YOLO{model_version.upper()} not available'}), 500
        
        
        if result['total'] == 0:
            # save original image as "result" (no annotations)
            result_filename = f"result_{unique_filename}"
            result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
            shutil.copy(filepath, result_path)
            
            # save to history
            detection_record = {
                'timestamp': datetime.now().isoformat(),
                'filename': filename,
                'model': model_version.upper(),
                'total_detections': 0,
                'counts': {'crack': 0, 'corrosion': 0},
                'inference_time': result['inference_time'],
                'original_image': f"/static/uploads/{unique_filename}",
                'result_image': f"/static/results/{result_filename}"
            }
            save_history(detection_record)
            
            response = {
                'success': True,
                'filename': filename,
                'model': model_version.upper(),
                'detections': [],
                'counts': {'crack': 0, 'corrosion': 0},
                'total': 0,
                'inference_time': result['inference_time'],
                'original_image': f"/static/uploads/{unique_filename}",
                'result_image': f"/static/results/{result_filename}",
                'message': 'No defects detected. Try lowering confidence threshold or use different images.'
            }
            
            return jsonify(response)
        
        # save annotated image
        result_filename = f"result_{unique_filename}"
        result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
        cv2.imwrite(result_path, result['annotated_image'])
        
        # save to history
        detection_record = {
            'timestamp': datetime.now().isoformat(),
            'filename': filename,
            'model': model_version.upper(),
            'total_detections': result['total'],
            'counts': result['counts'],
            'inference_time': result['inference_time'],
            'original_image': f"/static/uploads/{unique_filename}",
            'result_image': f"/static/results/{result_filename}"
        }
        save_history(detection_record)
        
        # prepare response
        response = {
            'success': True,
            'filename': filename,
            'model': model_version.upper(),
            'detections': result['detections'],
            'counts': result['counts'],
            'total': result['total'],
            'inference_time': result['inference_time'],
            'original_image': f"/static/uploads/{unique_filename}",
            'result_image': f"/static/results/{result_filename}"
        }
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """API endpoint for dashboard statistics"""
    history = load_history()
    
    # Prepare data for charts
    detection_timeline = []
    for record in history[-20:]:  # Last 20 records
        detection_timeline.append({
            'timestamp': record['timestamp'],
            'total': record['total_detections']
        })
    
    return jsonify({
        'total_inspections': len(history),
        'total_detections': sum(h['total_detections'] for h in history),
        'total_cracks': sum(h['counts']['crack'] for h in history),
        'total_corrosion': sum(h['counts']['corrosion'] for h in history),
        'timeline': detection_timeline
    })

@app.route('/clear-history', methods=['POST'])
def clear_history():
    """Clear detection history"""
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump([], f)
        return jsonify({'success': True, 'message': 'History cleared'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)