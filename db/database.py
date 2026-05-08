import sqlite3
import logging
from datetime import datetime
from config import DB_PATH

logger = logging.getLogger(__name__)


def get_connection():
    """Get a database connection with row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for concurrent read/write
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def setup_db():
    """Create tables if they don't exist."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_waste_usd REAL DEFAULT 0,
                    resources_found INTEGER DEFAULT 0
                )
            """)

            try:
                cursor.execute("ALTER TABLE scans ADD COLUMN ai_advice TEXT")
            except sqlite3.OperationalError:
                pass


            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id INTEGER NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    detail TEXT,
                    waste_usd REAL DEFAULT 0,
                    region TEXT,
                    status TEXT DEFAULT 'detected',
                    detected_at TEXT,
                    FOREIGN KEY (scan_id) REFERENCES scans(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    message TEXT,
                    total_waste REAL DEFAULT 0,
                    threshold REAL DEFAULT 0,
                    email_sent INTEGER DEFAULT 0
                )
            """)

            conn.commit()
            logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Database setup failed: {e}")
        raise


def save_alert(alert_type, message, total_waste, threshold, email_sent=False):
    """Save an alert record to the database."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO alerts (timestamp, alert_type, message, total_waste, threshold, email_sent)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (datetime.now().isoformat(), alert_type, message, total_waste, threshold, 1 if email_sent else 0)
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Failed to save alert: {e}")
        return None


def get_alerts(limit=50):
    """Return recent alerts, newest first."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Failed to fetch alerts: {e}")
        return []


def clear_all_alerts():
    """Clear all alerts from the database."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM alerts")
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to clear alerts: {e}")
        raise


def save_scan(total_waste=0, resources_found=0):
    """Save a scan record and return the scan ID."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO scans (timestamp, total_waste_usd, resources_found) VALUES (?, ?, ?)",
                (datetime.now().isoformat(), total_waste, resources_found)
            )
            scan_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Scan #{scan_id} initiated.")
            return scan_id
    except sqlite3.Error as e:
        logger.error(f"Failed to save scan: {e}")
        raise


def update_scan_totals(scan_id, total_waste, resources_found):
    """Update the totals for an existing scan."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE scans SET total_waste_usd = ?, resources_found = ? WHERE id = ?",
                (total_waste, resources_found, scan_id)
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to update scan totals for #{scan_id}: {e}")
        raise


def save_resource(scan_id, resource_type, resource_id, detail, waste_usd, region):
    """Save a detected resource to the database."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO resources 
                   (scan_id, resource_type, resource_id, detail, waste_usd, region, status, detected_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (scan_id, resource_type, resource_id, detail, waste_usd, region, "detected", datetime.now().isoformat())
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to save resource {resource_id}: {e}")
        raise


def get_all_scans():
    """Return all scan records, newest first."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scans ORDER BY timestamp DESC")
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Failed to fetch scans: {e}")
        return []


def clear_all_scans():
    """Clear all scans and associated resources from the database."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM resources")
            cursor.execute("DELETE FROM scans")
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to clear scans: {e}")
        raise


def get_scan_resources(scan_id):
    """Return all resources for a given scan."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM resources WHERE scan_id = ? ORDER BY waste_usd DESC", (scan_id,))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Failed to fetch resources for scan {scan_id}: {e}")
        return []


def get_all_active_resources():
    """Return all unique resources that are still in 'detected' status across all scans."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # Get latest status for each unique resource_id
            # We use a subquery to find the maximum ID (latest entry) for each resource_id
            cursor.execute("""
                SELECT r.* 
                FROM resources r
                INNER JOIN (
                    SELECT resource_id, MAX(id) as max_id 
                    FROM resources 
                    GROUP BY resource_id
                ) latest ON r.id = latest.max_id
                WHERE r.status NOT IN ('deleted', 'terminated')
                ORDER BY r.waste_usd DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Failed to fetch all active resources: {e}")
        return []


def get_latest_scan():
    """Return the most recent scan and its resources."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scans ORDER BY timestamp DESC LIMIT 1")
            scan = cursor.fetchone()
            if scan:
                scan = dict(scan)
                scan["resources"] = get_scan_resources(scan["id"])
                return scan
            return None
    except sqlite3.Error as e:
        logger.error(f"Failed to fetch latest scan: {e}")
        return None


def get_cost_trend(limit=30):
    """Return the last N scans for cost trend charting."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT timestamp, total_waste_usd, resources_found FROM scans ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            rows = [dict(row) for row in cursor.fetchall()]
            rows.reverse()  # oldest first for chart
            return rows
    except sqlite3.Error as e:
        logger.error(f"Failed to fetch cost trend: {e}")
        return []


def update_resource_status(resource_id, status):
    """Update the status of a resource (e.g., 'deleted', 'kept')."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE resources SET status = ? WHERE resource_id = ?",
                (status, resource_id)
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to update resource {resource_id}: {e}")
        raise


def update_scan_ai_advice(scan_id, advice):
    """Update the AI advice for a given scan."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE scans SET ai_advice = ? WHERE id = ?",
                (advice, scan_id)
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to update scan {scan_id} AI advice: {e}")
        raise

