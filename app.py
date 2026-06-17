import os
import shutil
from datetime import datetime

import cv2
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from ultralytics import YOLO
from werkzeug.utils import secure_filename

from config import CONFIDENCE_THRESHOLD, FLASK_CONFIG, IOU_THRESHOLD
from database import db
from severity import analyze_rust

app = Flask(__name__)
app.config.update(FLASK_CONFIG)
app.secret_key = FLASK_CONFIG['SECRET_KEY']

# Create necessary folders
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

# Severity level → DPWH rating mapping (matches severity.py output)
SEVERITY_TO_DPWH = {
    'NONE':   'Good',
    'LOW':    'Fair',
    'MEDIUM': 'Poor',
    'HIGH':   'Bad',
}

# Load rust detection model (place trained best.pt in models/)
print("Loading model...")
try:
    rust_model = YOLO('models/best.pt')
    print("✅ Rust detection model loaded")
except Exception as e:
    print(f"⚠️  Model not found (models/best.pt): {e}")
    rust_model = None

# Test database connection
if db.test_connection():
    print("✅ Database connected successfully")
else:
    print("❌ Database connection failed - check MySQL and config.py")


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def run_inference(image_path):
    """Run YOLO inference on image and return detections + severity analysis"""
    if rust_model is None:
        return None
    model = rust_model

    results = model.predict(image_path, conf=CONFIDENCE_THRESHOLD, iou=IOU_THRESHOLD)
    result = results[0]

    # Read image for color-based severity analysis
    image_bgr = cv2.imread(image_path)
    img_h, img_w = image_bgr.shape[:2] if image_bgr is not None else (640, 640)

    detections = []
    rust_count = 0

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
        rust_count += 1

    # Run severity analysis (uses per-detection 'class' for max-wins aggregation)
    severity_analysis = analyze_rust(detections, (img_h, img_w))

    # Draw boxes on image
    annotated_img = result.plot()

    return {
        'detections': detections,
        'rust_count': rust_count,
        'total': len(detections),
        'annotated_image': annotated_img,
        'inference_time': round(result.speed['inference'], 2),
        'severity_analysis': severity_analysis,
    }


# ==========================================
# MAIN ROUTES
# ==========================================

@app.route('/')
def index():
    """Redirect root to the primary action page"""
    return redirect(url_for('new_inspection'))


@app.route('/new-inspection')
def new_inspection():
    """Main upload page"""
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    """Dashboard page with MySQL data"""
    try:
        stats_data = db.get_dashboard_stats()
        recent = db.get_recent_inspections(limit=10)
        all_inspections = db.get_all_inspections()

        stats = {
            'total_inspections':  stats_data['total_inspections'] or 0,
            'total_detections':   stats_data['total_detections'] or 0,
            'total_rust':         stats_data['total_rust'] or 0,
            'total_low':          stats_data['total_low'] or 0,
            'total_medium':       stats_data['total_medium'] or 0,
            'total_high':         stats_data['total_high'] or 0,
            'recent_inspections': recent,
        }

        return render_template('dashboard.html', stats=stats, history=all_inspections)

    except Exception as e:
        print(f"Dashboard error: {e}")
        stats = {
            'total_inspections': 0, 'total_detections': 0, 'total_rust': 0,
            'total_low': 0, 'total_medium': 0, 'total_high': 0,
            'recent_inspections': [],
        }
        return render_template('dashboard.html', stats=stats, history=[])


# ==========================================
# CRUD ROUTES - INSPECTIONS
# ==========================================

@app.route('/inspections')
def inspections_list():
    """List all inspections with pagination"""
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
                'bridge_name':       request.form.get('bridge_name'),
                'bridge_location':   request.form.get('bridge_location'),
                'bridge_type':       request.form.get('bridge_type'),
                'inspector_name':    request.form.get('inspector_name'),
                'weather_condition': request.form.get('weather_condition'),
                'temperature':       request.form.get('temperature') or None,
                'inspection_notes':  request.form.get('inspection_notes'),
                'severity_rating':   request.form.get('severity_rating'),
            }

            success = db.update_inspection(inspection_id, update_data)

            if success:
                flash('Inspection updated successfully', 'success')
                return redirect(url_for('inspection_detail', inspection_id=inspection_id))
            else:
                flash('Failed to update inspection', 'danger')

        except Exception as e:
            flash(f'Error updating inspection: {str(e)}', 'danger')

    inspection = db.get_inspection(inspection_id)
    if not inspection:
        flash('Inspection not found', 'warning')
        return redirect(url_for('inspections_list'))

    return render_template('inspection_edit.html', inspection=inspection)


@app.route('/inspection/<int:inspection_id>/delete', methods=['POST'])
def inspection_delete(inspection_id):
    """Delete inspection"""
    try:
        inspection = db.get_inspection(inspection_id)

        if inspection:
            success = db.delete_inspection(inspection_id)

            if success:
                try:
                    for path_key in ('original_image_path', 'result_image_path'):
                        path = inspection.get(path_key, '')
                        if path:
                            local_path = path.lstrip('/')
                            if os.path.exists(local_path):
                                os.remove(local_path)
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


@app.route('/api/detect', methods=['POST'])
def detect():
    """
    Run full inference + severity.py on uploaded image.
    Saves images to static folders but does NOT create a DB record —
    the user decides whether to save via the 'Save Inspection' button
    which calls /api/save-inspection.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400

    if rust_model is None:
        return jsonify({'error': 'Model not loaded. Place best.pt in models/'}), 500

    try:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)

        # Full inference + severity.py at configured threshold
        result = run_inference(filepath)
        if result is None:
            return jsonify({'error': 'Inference failed'}), 500

        result_filename = f"result_{unique_filename}"
        result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
        if result['total'] == 0:
            shutil.copy(filepath, result_path)
        else:
            cv2.imwrite(result_path, result['annotated_image'])

        severity_analysis = result['severity_analysis']

        # Low-threshold run for slider exploration
        raw_results = rust_model.predict(filepath, conf=0.01, iou=0.01, verbose=False)
        raw_result = raw_results[0]
        img = cv2.imread(filepath)
        img_h, img_w = img.shape[:2] if img is not None else (640, 640)

        all_detections = []
        for box in raw_result.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            xyxy = box.xyxy[0].cpu().numpy()
            all_detections.append({
                'class':      raw_result.names[cls],
                'confidence': round(conf, 4),
                'bbox':       [round(float(x), 1) for x in xyxy],
            })

        return jsonify({
            'success':              True,
            'all_detections':       all_detections,
            'saved_detections':     result['detections'],   # proper-threshold detections for DB save
            'img_width':            img_w,
            'img_height':           img_h,
            'inference_time':       result['inference_time'],
            'conf_threshold':       CONFIDENCE_THRESHOLD,
            'severity_level':       severity_analysis['severity'],
            'filename':             filename,
            'original_image_path':  f"/static/uploads/{unique_filename}",
            'result_image_path':    f"/static/results/{result_filename}",
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/save-inspection', methods=['POST'])
def save_inspection():
    """
    Create a DB record from a previously run test detection.
    Called when the user clicks 'Add to Inspections' on the Test Model page.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    try:
        severity_level = data.get('severity_level', 'NONE')
        dpwh_severity  = SEVERITY_TO_DPWH.get(severity_level, 'Good')
        detections     = data.get('detections', [])

        inspection_data = {
            'timestamp':            datetime.now(),
            'filename':             data.get('filename', ''),
            'model':                'YOLOv8n-Rust',
            'bridge_name':          None,
            'bridge_location':      None,
            'bridge_type':          None,
            'inspector_name':       None,
            'weather_condition':    None,
            'temperature':          None,
            'inspection_notes':     None,
            'severity_rating':      dpwh_severity,
            'total_detections':     len(detections),
            'rust_count':           len(detections),
            'severity_level':       severity_level,
            'blur_score':           None,
            'upload_source':        'web',
            'inference_time':       data.get('inference_time', 0),
            'original_image_path':  data.get('original_image_path', ''),
            'result_image_path':    data.get('result_image_path', ''),
        }

        inspection_id = db.create_inspection(inspection_data)

        for det in detections:
            bbox = det.get('bbox', [0, 0, 0, 0])
            db.create_detection({
                'inspection_id': inspection_id,
                'defect_type':   det.get('class', 'rust'),
                'confidence':    det.get('confidence', 0),
                'bbox_x1':       bbox[0],
                'bbox_y1':       bbox[1],
                'bbox_x2':       bbox[2],
                'bbox_y2':       bbox[3],
            })

        return jsonify({'success': True, 'inspection_id': inspection_id})

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/search')
def search():
    """Search inspections"""
    query = request.args.get('q', '').strip()

    if query:
        inspections = db.search_inspections(query)
    else:
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
                cursor.execute("DELETE FROM inspections")
                conn.commit()
                deleted_count = cursor.rowcount

        return jsonify({'success': True, 'message': f'Cleared {deleted_count} inspection(s)'})

    except Exception as e:
        print(f"Error clearing history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats')
def get_stats():
    """API endpoint for dashboard statistics"""
    try:
        stats = db.get_dashboard_stats()
        return jsonify({
            'total_inspections':  stats['total_inspections'] or 0,
            'total_detections':   stats['total_detections'] or 0,
            'total_rust':         stats['total_rust'] or 0,
            'total_low':          stats['total_low'] or 0,
            'total_medium':       stats['total_medium'] or 0,
            'total_high':         stats['total_high'] or 0,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🌉 RUSTWATCH - STEEL BRIDGE CORROSION DETECTION (MySQL)")
    print("=" * 70)
    print(f"✅ Flask server starting...")
    print(f"🔗 Open your browser to: http://127.0.0.1:5000")
    print(f"📊 Dashboard: http://127.0.0.1:5000/dashboard")
    print(f"📋 Inspections: http://127.0.0.1:5000/inspections")
    print("=" * 70 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
