from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
import cv2
from datetime import datetime
from ultralytics import YOLO
import shutil

# Import database and config
from database import db
from config import FLASK_CONFIG

app = Flask(__name__)
app.config.update(FLASK_CONFIG)
app.secret_key = FLASK_CONFIG['SECRET_KEY']

# Create necessary folders
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

# Load models
print("Loading models...")
try:
    model_v8 = YOLO('models/yolov8n.pt')
    print("✅ YOLOv8 model loaded")
except Exception as e:
    print(f"⚠️  YOLOv8 model not found: {e}")
    model_v8 = None

try:
    model_v11 = YOLO('models/yolo11n.pt')
    print("✅ YOLOv11 model loaded")
except Exception as e:
    print(f"⚠️  YOLOv11 model not found: {e}")
    model_v11 = None

# Test database connection
if db.test_connection():
    print("✅ Database connected successfully")
else:
    print("❌ Database connection failed - check MySQL and config.py")

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
    result = results[0]
    
    # Prepare detection data
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

# ==========================================
# MAIN ROUTES
# ==========================================

@app.route('/')
def index():
    """Main upload page"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard page with MySQL data"""
    try:
        # Get statistics from database
        stats_data = db.get_dashboard_stats()
        
        # Get recent inspections
        recent = db.get_recent_inspections(limit=10)
        
        # Get all inspections for charts
        all_inspections = db.get_all_inspections()
        
        stats = {
            'total_inspections': stats_data['total_inspections'] or 0,
            'total_detections': stats_data['total_detections'] or 0,
            'total_cracks': stats_data['total_cracks'] or 0,
            'total_corrosion': stats_data['total_corrosion'] or 0,
            'recent_inspections': recent
        }
        
        return render_template('dashboard.html', stats=stats, history=all_inspections)
    
    except Exception as e:
        print(f"Dashboard error: {e}")
        # Fallback to empty data
        stats = {
            'total_inspections': 0,
            'total_detections': 0,
            'total_cracks': 0,
            'total_corrosion': 0,
            'recent_inspections': []
        }
        return render_template('dashboard.html', stats=stats, history=[])

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
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # Run inference
        result = run_inference(filepath, model_version)
        
        if result is None:
            return jsonify({'error': f'Model YOLO{model_version.upper()} not available'}), 500
        
        # Handle zero detections
        if result['total'] == 0:
            result_filename = f"result_{unique_filename}"
            result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
            shutil.copy(filepath, result_path)
        else:
            # Save annotated image
            result_filename = f"result_{unique_filename}"
            result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
            cv2.imwrite(result_path, result['annotated_image'])
        
        # Save to database
        inspection_data = {
            'timestamp': datetime.now(),
            'filename': filename,
            'model': model_version.upper(),
            'bridge_name': None,
            'bridge_location': None,
            'bridge_type': None,
            'inspector_name': None,
            'weather_condition': None,
            'temperature': None,
            'inspection_notes': None,
            'severity_rating': 'Good' if result['total'] == 0 else 'Fair',
            'total_detections': result['total'],
            'crack_count': result['counts']['crack'],
            'corrosion_count': result['counts']['corrosion'],
            'inference_time': result['inference_time'],
            'original_image_path': f"/static/uploads/{unique_filename}",
            'result_image_path': f"/static/results/{result_filename}"
        }
        
        inspection_id = db.create_inspection(inspection_data)
        
        # Save individual detections
        for detection in result['detections']:
            detection_data = {
                'inspection_id': inspection_id,
                'defect_type': detection['class'],
                'confidence': detection['confidence'],
                'bbox_x1': detection['bbox'][0],
                'bbox_y1': detection['bbox'][1],
                'bbox_x2': detection['bbox'][2],
                'bbox_y2': detection['bbox'][3]
            }
            db.create_detection(detection_data)
        
        # Prepare response
        response = {
            'success': True,
            'inspection_id': inspection_id,
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
        import traceback
        print("=" * 70)
        print("ERROR IN /upload:")
        print(traceback.format_exc())
        print("=" * 70)
        return jsonify({'error': str(e)}), 500

# ==========================================
# CRUD ROUTES - INSPECTIONS
# ==========================================

@app.route('/inspections')
def inspections_list():
    """List all inspections"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        offset = (page - 1) * per_page
        
        inspections = db.get_all_inspections(limit=per_page, offset=offset)
        total = db.get_inspection_count()
        total_pages = (total + per_page - 1) // per_page
        
        return render_template('inspections_list.html', 
                             inspections=inspections,
                             page=page,
                             total_pages=total_pages,
                             total=total)
    except Exception as e:
        flash(f'Error loading inspections: {str(e)}', 'danger')
        return render_template('inspections_list.html', inspections=[], page=1, total_pages=1, total=0)

@app.route('/inspection/<int:inspection_id>')
def inspection_detail(inspection_id):
    """View single inspection details"""
    try:
        inspection = db.get_inspection(inspection_id)
        if not inspection:
            flash('Inspection not found', 'warning')
            return redirect(url_for('inspections_list'))
        
        detections = db.get_detections_by_inspection(inspection_id)
        
        return render_template('inspection_detail.html', 
                             inspection=inspection,
                             detections=detections)
    except Exception as e:
        flash(f'Error loading inspection: {str(e)}', 'danger')
        return redirect(url_for('inspections_list'))

@app.route('/inspection/<int:inspection_id>/edit', methods=['GET', 'POST'])
def inspection_edit(inspection_id):
    """Edit inspection details"""
    if request.method == 'POST':
        try:
            update_data = {
                'bridge_name': request.form.get('bridge_name'),
                'bridge_location': request.form.get('bridge_location'),
                'bridge_type': request.form.get('bridge_type'),
                'inspector_name': request.form.get('inspector_name'),
                'weather_condition': request.form.get('weather_condition'),
                'temperature': request.form.get('temperature') or None,
                'inspection_notes': request.form.get('inspection_notes'),
                'severity_rating': request.form.get('severity_rating')
            }
            
            success = db.update_inspection(inspection_id, update_data)
            
            if success:
                flash('Inspection updated successfully', 'success')
                return redirect(url_for('inspection_detail', inspection_id=inspection_id))
            else:
                flash('Failed to update inspection', 'danger')
        
        except Exception as e:
            flash(f'Error updating inspection: {str(e)}', 'danger')
    
    # GET request - show edit form
    inspection = db.get_inspection(inspection_id)
    if not inspection:
        flash('Inspection not found', 'warning')
        return redirect(url_for('inspections_list'))
    
    return render_template('inspection_edit.html', inspection=inspection)

@app.route('/inspection/<int:inspection_id>/delete', methods=['POST'])
def inspection_delete(inspection_id):
    """Delete inspection"""
    try:
        # Get inspection to delete associated images
        inspection = db.get_inspection(inspection_id)
        
        if inspection:
            # Delete from database
            success = db.delete_inspection(inspection_id)
            
            if success:
                # Delete image files
                try:
                    if inspection['original_image_path']:
                        original_path = inspection['original_image_path'].lstrip('/')
                        if os.path.exists(original_path):
                            os.remove(original_path)
                    
                    if inspection['result_image_path']:
                        result_path = inspection['result_image_path'].lstrip('/')
                        if os.path.exists(result_path):
                            os.remove(result_path)
                except Exception as img_err:
                    print(f"Error deleting images: {img_err}")
                
                flash('Inspection deleted successfully', 'success')
            else:
                flash('Failed to delete inspection', 'danger')
        else:
            flash('Inspection not found', 'warning')
    
    except Exception as e:
        flash(f'Error deleting inspection: {str(e)}', 'danger')
    
    return redirect(url_for('inspections_list'))

@app.route('/search')
def search():
    """Search inspections"""
    query = request.args.get('q', '').strip()
    
    if query:
        # Search with query
        inspections = db.search_inspections(query)
    else:
        # No query - redirect to full list
        return redirect(url_for('inspections_list'))
    
    return render_template('inspections_list.html', 
                         inspections=inspections,
                         search_query=query,
                         page=1,
                         total_pages=1,
                         total=len(inspections))

# ==========================================
# API ROUTES
# ==========================================

@app.route('/clear-history', methods=['POST'])
def clear_history():
    """Clear all inspection records from database"""
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Delete all inspections (cascades to detections)
                cursor.execute("DELETE FROM inspections")
                conn.commit()
                deleted_count = cursor.rowcount
        
        return jsonify({
            'success': True, 
            'message': f'Cleared {deleted_count} inspection(s)'
        })
    
    except Exception as e:
        print(f"Error clearing history: {e}")
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

@app.route('/api/stats')
def get_stats():
    """API endpoint for dashboard statistics"""
    try:
        stats = db.get_dashboard_stats()
        return jsonify({
            'total_inspections': stats['total_inspections'] or 0,
            'total_detections': stats['total_detections'] or 0,
            'total_cracks': stats['total_cracks'] or 0,
            'total_corrosion': stats['total_corrosion'] or 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🌉 STEEL BRIDGE DEFECT DETECTION - WEB INTERFACE (MySQL)")
    print("=" * 70)
    print(f"✅ Flask server starting...")
    print(f"🔗 Open your browser to: http://127.0.0.1:5000")
    print(f"📊 Dashboard: http://127.0.0.1:5000/dashboard")
    print(f"📋 Inspections: http://127.0.0.1:5000/inspections")
    print("=" * 70 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)