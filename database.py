import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from config import DB_CONFIG

class Database:
    """Database connection and operations manager"""
    
    def __init__(self):
        self.config = DB_CONFIG
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        connection = None
        try:
            connection = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset=self.config['charset'],
                cursorclass=DictCursor
            )
            yield connection
        except pymysql.Error as e:
            print(f"Database connection error: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    def test_connection(self):
        """Test database connection"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    # ==========================================
    # INSPECTION CRUD OPERATIONS
    # ==========================================
    
    def create_inspection(self, inspection_data):
        """Create a new inspection record"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO inspections (
                    timestamp, filename, model, bridge_name, bridge_location,
                    bridge_type, inspector_name, weather_condition, temperature,
                    inspection_notes, severity_rating, total_detections,
                    crack_count, corrosion_count, inference_time,
                    original_image_path, result_image_path
                ) VALUES (
                    %(timestamp)s, %(filename)s, %(model)s, %(bridge_name)s,
                    %(bridge_location)s, %(bridge_type)s, %(inspector_name)s,
                    %(weather_condition)s, %(temperature)s, %(inspection_notes)s,
                    %(severity_rating)s, %(total_detections)s, %(crack_count)s,
                    %(corrosion_count)s, %(inference_time)s,
                    %(original_image_path)s, %(result_image_path)s
                )
                """
                cursor.execute(sql, inspection_data)
                conn.commit()
                return cursor.lastrowid
    
    def get_inspection(self, inspection_id):
        """Get a single inspection by ID"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                sql = "SELECT * FROM inspections WHERE id = %s"
                cursor.execute(sql, (inspection_id,))
                return cursor.fetchone()
    
    def get_all_inspections(self, limit=None, offset=0):
        """Get all inspections with optional pagination"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                if limit:
                    sql = """
                    SELECT * FROM inspections 
                    ORDER BY created_at DESC 
                    LIMIT %s OFFSET %s
                    """
                    cursor.execute(sql, (limit, offset))
                else:
                    sql = "SELECT * FROM inspections ORDER BY created_at DESC"
                    cursor.execute(sql)
                return cursor.fetchall()
    
    def update_inspection(self, inspection_id, update_data):
        """Update an existing inspection"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Build dynamic UPDATE query
                set_clause = ", ".join([f"{key} = %({key})s" for key in update_data.keys()])
                sql = f"UPDATE inspections SET {set_clause} WHERE id = %(id)s"
                update_data['id'] = inspection_id
                cursor.execute(sql, update_data)
                conn.commit()
                return cursor.rowcount > 0
    
    def delete_inspection(self, inspection_id):
        """Delete an inspection (cascades to detections)"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                sql = "DELETE FROM inspections WHERE id = %s"
                cursor.execute(sql, (inspection_id,))
                conn.commit()
                return cursor.rowcount > 0
    
    # ==========================================
    # DETECTION CRUD OPERATIONS
    # ==========================================
    
    def create_detection(self, detection_data):
        """Create a new detection record"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO detections (
                    inspection_id, defect_type, confidence,
                    bbox_x1, bbox_y1, bbox_x2, bbox_y2
                ) VALUES (
                    %(inspection_id)s, %(defect_type)s, %(confidence)s,
                    %(bbox_x1)s, %(bbox_y1)s, %(bbox_x2)s, %(bbox_y2)s
                )
                """
                cursor.execute(sql, detection_data)
                conn.commit()
                return cursor.lastrowid
    
    def get_detections_by_inspection(self, inspection_id):
        """Get all detections for a specific inspection"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                sql = "SELECT * FROM detections WHERE inspection_id = %s"
                cursor.execute(sql, (inspection_id,))
                return cursor.fetchall()
    
    # ==========================================
    # STATISTICS & REPORTS
    # ==========================================
    
    def get_dashboard_stats(self):
        """Get statistics for dashboard"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                sql = """
                SELECT 
                    COUNT(*) as total_inspections,
                    SUM(total_detections) as total_detections,
                    SUM(crack_count) as total_cracks,
                    SUM(corrosion_count) as total_corrosion,
                    AVG(inference_time) as avg_inference_time
                FROM inspections
                """
                cursor.execute(sql)
                return cursor.fetchone()
    
    def get_recent_inspections(self, limit=10):
        """Get recent inspections"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                sql = """
                SELECT * FROM inspections 
                ORDER BY created_at DESC 
                LIMIT %s
                """
                cursor.execute(sql, (limit,))
                return cursor.fetchall()
    
    def get_inspections_by_severity(self, severity):
        """Get inspections filtered by severity rating"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                sql = """
                SELECT * FROM inspections 
                WHERE severity_rating = %s 
                ORDER BY created_at DESC
                """
                cursor.execute(sql, (severity,))
                return cursor.fetchall()
    
    def get_inspections_by_bridge(self, bridge_name):
        """Get all inspections for a specific bridge"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                sql = """
                SELECT * FROM inspections 
                WHERE bridge_name = %s 
                ORDER BY created_at DESC
                """
                cursor.execute(sql, (bridge_name,))
                return cursor.fetchall()
    
    def search_inspections(self, search_term):
        """Search inspections by bridge name, location, or notes"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                sql = """
                SELECT * FROM inspections 
                WHERE bridge_name LIKE %s 
                   OR bridge_location LIKE %s 
                   OR inspection_notes LIKE %s
                ORDER BY created_at DESC
                """
                search_pattern = f"%{search_term}%"
                cursor.execute(sql, (search_pattern, search_pattern, search_pattern))
                return cursor.fetchall()
    
    def get_inspection_count(self):
        """Get total number of inspections"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM inspections")
                result = cursor.fetchone()
                return result['count'] if result else 0


# Initialize database instance
db = Database()