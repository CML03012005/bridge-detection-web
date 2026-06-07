-- Use the database
USE bridge_inspection;

-- Drop tables if they exist (for clean reinstall)
DROP TABLE IF EXISTS detections;
DROP TABLE IF EXISTS inspections;


-- Create inspections table
CREATE TABLE inspections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    filename VARCHAR(255) NOT NULL,
    model VARCHAR(50) NOT NULL,

    -- Bridge Information
    bridge_name VARCHAR(255),
    bridge_location VARCHAR(255),
    bridge_type VARCHAR(100) DEFAULT 'Steel Bridge',

    -- Inspection Details
    inspector_name VARCHAR(100),
    weather_condition VARCHAR(50),
    temperature DECIMAL(5,2),
    inspection_notes TEXT,

    -- DPWH Severity Rating (inspector-facing)
    severity_rating ENUM('Good', 'Fair', 'Poor', 'Bad') DEFAULT 'Good',

    -- Detection Statistics
    total_detections INT DEFAULT 0,
    rust_count INT DEFAULT 0,

    -- Severity Analysis (from severity.py)
    severity_level ENUM('NONE', 'LOW', 'MEDIUM', 'HIGH') DEFAULT 'NONE',
    blur_score DECIMAL(8,2) DEFAULT NULL,

    -- Upload Source
    upload_source ENUM('rpi5', 'web') DEFAULT 'web',

    -- Performance Metrics
    inference_time DECIMAL(10,2),

    -- Image Paths
    original_image_path VARCHAR(500),
    result_image_path VARCHAR(500),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_timestamp (timestamp),
    INDEX idx_severity_rating (severity_rating),
    INDEX idx_severity_level (severity_level),
    INDEX idx_bridge_name (bridge_name),
    INDEX idx_bridge_location (bridge_location),
    INDEX idx_upload_source (upload_source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Create detections table (one-to-many with inspections)
CREATE TABLE detections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    inspection_id INT NOT NULL,

    -- Defect Information
    defect_type VARCHAR(50) NOT NULL DEFAULT 'rust',
    confidence DECIMAL(5,2) NOT NULL,

    -- Bounding Box Coordinates
    bbox_x1 DECIMAL(10,2),
    bbox_y1 DECIMAL(10,2),
    bbox_x2 DECIMAL(10,2),
    bbox_y2 DECIMAL(10,2),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign Key
    FOREIGN KEY (inspection_id) REFERENCES inspections(id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_inspection_id (inspection_id),
    INDEX idx_confidence (confidence)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Insert sample data for testing (optional)
INSERT INTO inspections (
    timestamp, filename, model, bridge_name, bridge_location,
    inspector_name, severity_rating, severity_level,
    total_detections, rust_count,
    inference_time, original_image_path, result_image_path, upload_source
) VALUES (
    NOW(), 'sample_bridge.jpg', 'YOLOv8n',
    'San Juanico Bridge', 'Leyte-Samar',
    'Test Inspector', 'Fair', 'LOW',
    2, 2,
    150.5,
    '/static/uploads/sample.jpg', '/static/results/sample.jpg',
    'web'
);

-- Verify tables created
SHOW TABLES;

-- Display structure
DESCRIBE inspections;
DESCRIBE detections;
