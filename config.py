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