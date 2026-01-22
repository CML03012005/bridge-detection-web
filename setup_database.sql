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
    location VARCHAR(255),
    bridge_type VARCHAR(100) DEFAULT 'Steel Bridge',
    
    -- Inspection Details
    inspector_name VARCHAR(100),
    weather_condition VARCHAR(50),
    temperature DECIMAL(5,2),
    inspection_notes TEXT,
    
    -- DPWH Severity Rating
    severity_rating ENUM('Good', 'Fair', 'Poor', 'Bad') DEFAULT 'Good',
    
    -- Detection Statistics
    total_detections INT DEFAULT 0,
    crack_count INT DEFAULT 0,
    corrosion_count INT DEFAULT 0,
    
    -- Performance Metrics
    inference_time DECIMAL(10,2),
    
    -- Image Paths
    original_image_path VARCHAR(500),
    result_image_path VARCHAR(500),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Indexes for faster queries
    INDEX idx_timestamp (timestamp),
    INDEX idx_severity (severity_rating),
    INDEX idx_bridge_name (bridge_name),
    INDEX idx_location (location)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Create detections table (one-to-many with inspections)
CREATE TABLE detections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    inspection_id INT NOT NULL,
    
    -- Defect Information
    defect_type ENUM('crack', 'corrosion') NOT NULL,
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
    INDEX idx_defect_type (defect_type),
    INDEX idx_confidence (confidence)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert sample data for testing (optional)
INSERT INTO inspections (
    timestamp, filename, model, bridge_name, location, 
    inspector_name, severity_rating, total_detections, 
    crack_count, corrosion_count, inference_time,
    original_image_path, result_image_path
) VALUES (
    NOW(), 'sample_bridge.jpg', 'YOLOv8', 
    'San Juanico Bridge', 'Leyte-Samar', 
    'Test Inspector', 'Good', 0, 0, 0, 150.5,
    '/static/uploads/sample.jpg', '/static/results/sample.jpg'
);

-- Verify tables created
SHOW TABLES;

-- Display structure
DESCRIBE inspections;
DESCRIBE detections;