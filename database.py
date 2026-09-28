"""
SafeHer Database Engine & Relational Abstraction Layer
Supports SQLite (default zero-config) and MySQL (via PyMySQL) natively,
with 100% pure Python execution and zero binary DLL dependencies.
"""

import os
import sqlite3
import pymysql
import pymysql.cursors
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class DatabaseManager:
    def __init__(self, db_url=None):
        base_dir = os.path.abspath(os.path.dirname(__file__))
        default_sqlite = f"sqlite:///{os.path.join(base_dir, 'safeher.db')}"
        self.db_url = db_url or os.environ.get('DATABASE_URL', default_sqlite)
        self.is_mysql = self.db_url.startswith('mysql')
        self._init_db()

    def get_connection(self):
        if self.is_mysql:
            # Parse mysql://user:password@host:port/dbname
            clean_url = self.db_url.replace('mysql+pymysql://', '').replace('mysql://', '')
            user_pass, host_db = clean_url.split('@')
            user, password = user_pass.split(':') if ':' in user_pass else (user_pass, '')
            
            if '/' in host_db:
                host_port, dbname = host_db.split('/', 1)
            else:
                host_port, dbname = host_db, 'safeher'

            port = 3306
            if ':' in host_port:
                host, port_str = host_port.split(':')
                port = int(port_str)
            else:
                host = host_port

            return pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=dbname,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
        else:
            # SQLite
            db_path = self.db_url.replace('sqlite:///', '')
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn

    def execute(self, query, params=None):
        """Execute INSERT, UPDATE, DELETE and return lastrowid / affected rows."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if self.is_mysql:
                # Replace SQLite parameter markers '?' with '%s' for MySQL if needed
                query = query.replace('?', '%s')
            cursor.execute(query, params or ())
            if not self.is_mysql:
                conn.commit()
            last_id = cursor.lastrowid
            cursor.close()
            return last_id
        finally:
            conn.close()

    def query_all(self, query, params=None):
        """Fetch all rows as a list of dicts."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if self.is_mysql:
                query = query.replace('?', '%s')
            cursor.execute(query, params or ())
            rows = cursor.fetchall()
            cursor.close()
            if self.is_mysql:
                return rows
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def query_one(self, query, params=None):
        """Fetch single row as a dict, or None."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if self.is_mysql:
                query = query.replace('?', '%s')
            cursor.execute(query, params or ())
            row = cursor.fetchone()
            cursor.close()
            if row is None:
                return None
            if self.is_mysql:
                return row
            return dict(row)
        finally:
            conn.close()

    def _init_db(self):
        """Create tables if they do not exist."""
        # 1. Users Table
        self.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                phone VARCHAR(20) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                blood_group VARCHAR(10) DEFAULT '',
                address TEXT DEFAULT '',
                medical_notes TEXT DEFAULT '',
                role VARCHAR(20) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''' if not self.is_mysql else '''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                phone VARCHAR(20) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                blood_group VARCHAR(10) DEFAULT '',
                address TEXT,
                medical_notes TEXT,
                role VARCHAR(20) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. Emergency Contacts Table
        self.execute('''
            CREATE TABLE IF NOT EXISTS emergency_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name VARCHAR(100) NOT NULL,
                phone VARCHAR(20) NOT NULL,
                email VARCHAR(120),
                relationship VARCHAR(50) DEFAULT 'Guardian',
                is_primary BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''' if not self.is_mysql else '''
            CREATE TABLE IF NOT EXISTS emergency_contacts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                name VARCHAR(100) NOT NULL,
                phone VARCHAR(20) NOT NULL,
                email VARCHAR(120),
                relationship VARCHAR(50) DEFAULT 'Guardian',
                is_primary BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # 3. Emergency Alerts Table
        self.execute('''
            CREATE TABLE IF NOT EXISTS emergency_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                alert_type VARCHAR(50) DEFAULT 'Immediate Distress',
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                accuracy REAL,
                location_address TEXT,
                status VARCHAR(30) DEFAULT 'ACTIVE',
                notes TEXT,
                responded_by VARCHAR(100),
                resolved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''' if not self.is_mysql else '''
            CREATE TABLE IF NOT EXISTS emergency_alerts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                alert_type VARCHAR(50) DEFAULT 'Immediate Distress',
                latitude DOUBLE NOT NULL,
                longitude DOUBLE NOT NULL,
                accuracy DOUBLE,
                location_address TEXT,
                status VARCHAR(30) DEFAULT 'ACTIVE',
                notes TEXT,
                responded_by VARCHAR(100),
                resolved_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # 4. Alert Notification Logs Table
        self.execute('''
            CREATE TABLE IF NOT EXISTS alert_notification_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                recipient_name VARCHAR(100) NOT NULL,
                recipient_phone VARCHAR(20) NOT NULL,
                recipient_email VARCHAR(120),
                channel VARCHAR(20) DEFAULT 'SMS',
                delivery_status VARCHAR(30) DEFAULT 'DELIVERED',
                message_body TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (alert_id) REFERENCES emergency_alerts(id) ON DELETE CASCADE
            )
        ''' if not self.is_mysql else '''
            CREATE TABLE IF NOT EXISTS alert_notification_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                alert_id INT NOT NULL,
                recipient_name VARCHAR(100) NOT NULL,
                recipient_phone VARCHAR(20) NOT NULL,
                recipient_email VARCHAR(120),
                channel VARCHAR(20) DEFAULT 'SMS',
                delivery_status VARCHAR(30) DEFAULT 'DELIVERED',
                message_body TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (alert_id) REFERENCES emergency_alerts(id) ON DELETE CASCADE
            )
        ''')

        # 5. Safe Locations Table
        self.execute('''
            CREATE TABLE IF NOT EXISTS safe_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(150) NOT NULL,
                category VARCHAR(50) NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                address TEXT NOT NULL,
                contact_number VARCHAR(50) NOT NULL,
                is_24x7 BOOLEAN DEFAULT 1,
                description TEXT
            )
        ''' if not self.is_mysql else '''
            CREATE TABLE IF NOT EXISTS safe_locations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                category VARCHAR(50) NOT NULL,
                latitude DOUBLE NOT NULL,
                longitude DOUBLE NOT NULL,
                address TEXT NOT NULL,
                contact_number VARCHAR(50) NOT NULL,
                is_24x7 BOOLEAN DEFAULT 1,
                description TEXT
            )
        ''')

        # 6. App Settings Table (for SMS Gateway API keys, Twilio, Fast2SMS)
        self.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                key VARCHAR(50) PRIMARY KEY,
                value TEXT
            )
        ''')

    def get_setting(self, key, default=''):
        row = self.query_one('SELECT value FROM app_settings WHERE key = ?', (key,))
        return row['value'] if row else default

    def set_setting(self, key, value):
        self.execute('''
            INSERT INTO app_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        ''' if not self.is_mysql else '''
            INSERT INTO app_settings (`key`, `value`) VALUES (?, ?)
            ON DUPLICATE KEY UPDATE `value` = VALUES(`value`)
        ''', (key, str(value)))


# Global DB instance
db = DatabaseManager()

