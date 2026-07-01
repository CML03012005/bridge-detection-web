# Database Configuration
# Update these settings based on your XAMPP MySQL setup

DB_CONFIG = {
    'host': 'localhost',
    'port': 3307,
    'user': 'root',          # Default XAMPP user
    'password': '',          # Default XAMPP has no password (leave empty)
    'database': 'bridge_inspection',
    'charset': 'utf8mb4',
    'cursorclass': 'DictCursor'  # Return results as dictionaries
}

# Flask Configuration
FLASK_CONFIG = {
    'SECRET_KEY': 'your-secret-key-change-this-in-production',
    'UPLOAD_FOLDER': 'static/uploads',
    'RESULTS_FOLDER': 'static/results',
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB max file size
    'ALLOWED_EXTENSIONS': {'png', 'jpg', 'jpeg'}
}

# Inference Configuration — must match RPi5 corrosion_detection.py
CONFIDENCE_THRESHOLD = 0.05
IOU_THRESHOLD = 0.45

# RPi5 live camera stream (MJPEG served by detect_lcd.py on the Pi).
# Uses the Pi's Tailscale IP (eaglekim) so it works on any network without changing.
# Get it with `tailscale ip -4` on the Pi. Leave blank to hide the Live Camera button.
PI_STREAM_URL = 'http://100.102.61.125:8000/video_feed'