"""
SafeHer Data Models
Provides object-oriented interface for Users, Emergency Contacts,
Emergency Alerts, Notification Logs, and Safe Locations.
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from database import db

class User:
    def __init__(self, data):
        self.id = data.get('id')
        self.name = data.get('name')
        self.email = data.get('email')
        self.phone = data.get('phone')
        self.password_hash = data.get('password_hash')
        self.blood_group = data.get('blood_group', '')
        self.address = data.get('address', '')
        self.medical_notes = data.get('medical_notes', '')
        self.role = data.get('role', 'user')
        self.created_at = data.get('created_at')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_contacts(self):
        return EmergencyContact.find_by_user(self.id)

    def get_alerts(self):
        rows = db.query_all('SELECT * FROM emergency_alerts WHERE user_id = ? ORDER BY id DESC', (self.id,))
        return [EmergencyAlert(r) for r in rows]

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'blood_group': self.blood_group,
            'address': self.address,
            'medical_notes': self.medical_notes,
            'role': self.role,
            'created_at': str(self.created_at) if self.created_at else None,
            'contact_count': len(self.get_contacts())
        }

    @classmethod
    def create(cls, name, email, phone, password, blood_group='', address='', medical_notes='', role='user'):
        pw_hash = generate_password_hash(password)
        user_id = db.execute('''
            INSERT INTO users (name, email, phone, password_hash, blood_group, address, medical_notes, role)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, email.lower().strip(), phone.strip(), pw_hash, blood_group, address, medical_notes, role))
        return cls.find_by_id(user_id)

    @classmethod
    def find_by_id(cls, user_id):
        row = db.query_one('SELECT * FROM users WHERE id = ?', (user_id,))
        return cls(row) if row else None

    @classmethod
    def find_by_email(cls, email):
        row = db.query_one('SELECT * FROM users WHERE LOWER(email) = ?', (email.lower().strip(),))
        return cls(row) if row else None

    @classmethod
    def all(cls):
        rows = db.query_all('SELECT * FROM users ORDER BY id DESC')
        return [cls(r) for r in rows]

    @classmethod
    def update_profile(cls, user_id, name, phone, blood_group, address, medical_notes):
        db.execute('''
            UPDATE users SET name = ?, phone = ?, blood_group = ?, address = ?, medical_notes = ?
            WHERE id = ?
        ''', (name, phone, blood_group, address, medical_notes, user_id))


class EmergencyContact:
    def __init__(self, data):
        self.id = data.get('id')
        self.user_id = data.get('user_id')
        self.name = data.get('name')
        self.phone = data.get('phone')
        self.email = data.get('email', '')
        self.relationship = data.get('relationship', 'Guardian')
        self.is_primary = bool(data.get('is_primary', 0))
        self.created_at = data.get('created_at')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'relationship': self.relationship,
            'is_primary': self.is_primary,
            'created_at': str(self.created_at) if self.created_at else None
        }

    @classmethod
    def create(cls, user_id, name, phone, email='', relationship='Guardian', is_primary=False):
        if is_primary:
            # Unset existing primary
            db.execute('UPDATE emergency_contacts SET is_primary = 0 WHERE user_id = ?', (user_id,))
        
        cid = db.execute('''
            INSERT INTO emergency_contacts (user_id, name, phone, email, relationship, is_primary)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, name.strip(), phone.strip(), email.strip(), relationship.strip(), 1 if is_primary else 0))
        return cls.find_by_id(cid)

    @classmethod
    def find_by_id(cls, contact_id):
        row = db.query_one('SELECT * FROM emergency_contacts WHERE id = ?', (contact_id,))
        return cls(row) if row else None

    @classmethod
    def find_by_user(cls, user_id):
        rows = db.query_all('SELECT * FROM emergency_contacts WHERE user_id = ? ORDER BY is_primary DESC, id ASC', (user_id,))
        return [cls(r) for r in rows]

    @classmethod
    def set_primary(cls, contact_id, user_id):
        db.execute('UPDATE emergency_contacts SET is_primary = 0 WHERE user_id = ?', (user_id,))
        db.execute('UPDATE emergency_contacts SET is_primary = 1 WHERE id = ? AND user_id = ?', (contact_id, user_id))

    @classmethod
    def delete(cls, contact_id, user_id):
        db.execute('DELETE FROM emergency_contacts WHERE id = ? AND user_id = ?', (contact_id, user_id))


class EmergencyAlert:
    def __init__(self, data):
        self.id = data.get('id')
        self.user_id = data.get('user_id')
        self.alert_type = data.get('alert_type', 'Immediate Distress')
        self.latitude = float(data.get('latitude', 0.0))
        self.longitude = float(data.get('longitude', 0.0))
        self.accuracy = float(data.get('accuracy', 0.0)) if data.get('accuracy') is not None else 10.0
        self.location_address = data.get('location_address') or f"Coordinates ({self.latitude:.4f}, {self.longitude:.4f})"
        self.status = data.get('status', 'ACTIVE')  # ACTIVE, IN_PROGRESS, RESOLVED, CANCELLED
        self.notes = data.get('notes', '')
        self.responded_by = data.get('responded_by')
        self.resolved_at = data.get('resolved_at')
        self.created_at = data.get('created_at')

    def get_user(self):
        return User.find_by_id(self.user_id)

    def get_notifications(self):
        return AlertNotificationLog.find_by_alert(self.id)

    def to_dict(self):
        user = self.get_user()
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': user.name if user else 'Unknown',
            'user_phone': user.phone if user else 'N/A',
            'user_blood_group': user.blood_group if user else 'N/A',
            'alert_type': self.alert_type,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'accuracy': self.accuracy,
            'location_address': self.location_address,
            'status': self.status,
            'notes': self.notes,
            'responded_by': self.responded_by,
            'resolved_at': str(self.resolved_at) if self.resolved_at else None,
            'created_at': str(self.created_at) if self.created_at else None,
            'notifications_count': len(self.get_notifications())
        }

    @classmethod
    def create(cls, user_id, alert_type, latitude, longitude, accuracy=None, location_address=None, notes=''):
        aid = db.execute('''
            INSERT INTO emergency_alerts (user_id, alert_type, latitude, longitude, accuracy, location_address, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
        ''', (user_id, alert_type, latitude, longitude, accuracy, location_address, notes))
        return cls.find_by_id(aid)

    @classmethod
    def find_by_id(cls, alert_id):
        row = db.query_one('SELECT * FROM emergency_alerts WHERE id = ?', (alert_id,))
        return cls(row) if row else None

    @classmethod
    def find_active_by_user(cls, user_id):
        row = db.query_one("SELECT * FROM emergency_alerts WHERE user_id = ? AND status = 'ACTIVE' ORDER BY id DESC LIMIT 1", (user_id,))
        return cls(row) if row else None

    @classmethod
    def get_all_recent(cls, limit=100):
        rows = db.query_all('SELECT * FROM emergency_alerts ORDER BY id DESC LIMIT ?', (limit,))
        return [cls(r) for r in rows]

    @classmethod
    def get_active_alerts(cls):
        rows = db.query_all("SELECT * FROM emergency_alerts WHERE status IN ('ACTIVE', 'IN_PROGRESS') ORDER BY id DESC")
        return [cls(r) for r in rows]

    @classmethod
    def update_status(cls, alert_id, status, notes=None, responded_by=None):
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if status in ['RESOLVED', 'CANCELLED']:
            db.execute('''
                UPDATE emergency_alerts SET status = ?, notes = COALESCE(?, notes), responded_by = COALESCE(?, responded_by), resolved_at = ?
                WHERE id = ?
            ''', (status, notes, responded_by, now_str, alert_id))
        else:
            db.execute('''
                UPDATE emergency_alerts SET status = ?, notes = COALESCE(?, notes), responded_by = COALESCE(?, responded_by)
                WHERE id = ?
            ''', (status, notes, responded_by, alert_id))

    @classmethod
    def get_stats(cls):
        total_alerts = db.query_one('SELECT COUNT(*) as count FROM emergency_alerts')['count']
        active_alerts = db.query_one("SELECT COUNT(*) as count FROM emergency_alerts WHERE status = 'ACTIVE'")['count']
        in_progress = db.query_one("SELECT COUNT(*) as count FROM emergency_alerts WHERE status = 'IN_PROGRESS'")['count']
        resolved = db.query_one("SELECT COUNT(*) as count FROM emergency_alerts WHERE status = 'RESOLVED'")['count']
        total_users = db.query_one('SELECT COUNT(*) as count FROM users')['count']
        total_contacts = db.query_one('SELECT COUNT(*) as count FROM emergency_contacts')['count']
        total_safe_places = db.query_one('SELECT COUNT(*) as count FROM safe_locations')['count']

        # Category breakdown
        type_rows = db.query_all('''
            SELECT alert_type, COUNT(*) as count FROM emergency_alerts GROUP BY alert_type
        ''')
        types_dist = {r['alert_type']: r['count'] for r in type_rows}

        return {
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'in_progress': in_progress,
            'resolved': resolved,
            'total_users': total_users,
            'total_contacts': total_contacts,
            'total_safe_places': total_safe_places,
            'types_dist': types_dist
        }


class AlertNotificationLog:
    def __init__(self, data):
        self.id = data.get('id')
        self.alert_id = data.get('alert_id')
        self.recipient_name = data.get('recipient_name')
        self.recipient_phone = data.get('recipient_phone')
        self.recipient_email = data.get('recipient_email', '')
        self.channel = data.get('channel', 'SMS')
        self.delivery_status = data.get('delivery_status', 'DELIVERED')
        self.message_body = data.get('message_body', '')
        self.sent_at = data.get('sent_at')

    def to_dict(self):
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'recipient_name': self.recipient_name,
            'recipient_phone': self.recipient_phone,
            'recipient_email': self.recipient_email,
            'channel': self.channel,
            'delivery_status': self.delivery_status,
            'message_body': self.message_body,
            'sent_at': str(self.sent_at) if self.sent_at else None
        }

    @classmethod
    def create(cls, alert_id, recipient_name, recipient_phone, recipient_email='', channel='SMS', message_body='', delivery_status='DELIVERED'):
        nid = db.execute('''
            INSERT INTO alert_notification_logs (alert_id, recipient_name, recipient_phone, recipient_email, channel, message_body, delivery_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (alert_id, recipient_name, recipient_phone, recipient_email, channel, message_body, delivery_status))
        row = db.query_one('SELECT * FROM alert_notification_logs WHERE id = ?', (nid,))
        return cls(row) if row else None

    @classmethod
    def find_by_alert(cls, alert_id):
        rows = db.query_all('SELECT * FROM alert_notification_logs WHERE alert_id = ? ORDER BY id ASC', (alert_id,))
        return [cls(r) for r in rows]


class SafeLocation:
    def __init__(self, data):
        self.id = data.get('id')
        self.name = data.get('name')
        self.category = data.get('category')  # police, hospital, pharmacy, metro, safe_haven
        self.latitude = float(data.get('latitude', 0.0))
        self.longitude = float(data.get('longitude', 0.0))
        self.address = data.get('address', '')
        self.contact_number = data.get('contact_number', '')
        self.is_24x7 = bool(data.get('is_24x7', 1))
        self.description = data.get('description', '')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'address': self.address,
            'contact_number': self.contact_number,
            'is_24x7': self.is_24x7,
            'description': self.description
        }

    @classmethod
    def create(cls, name, category, latitude, longitude, address, contact_number, is_24x7=True, description=''):
        sid = db.execute('''
            INSERT INTO safe_locations (name, category, latitude, longitude, address, contact_number, is_24x7, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name.strip(), category.strip(), float(latitude), float(longitude), address.strip(), contact_number.strip(), 1 if is_24x7 else 0, description.strip()))
        return cls.find_by_id(sid)

    @classmethod
    def find_by_id(cls, loc_id):
        row = db.query_one('SELECT * FROM safe_locations WHERE id = ?', (loc_id,))
        return cls(row) if row else None

    @classmethod
    def all(cls, category=None):
        if category and category != 'all':
            rows = db.query_all('SELECT * FROM safe_locations WHERE category = ? ORDER BY name ASC', (category,))
        else:
            rows = db.query_all('SELECT * FROM safe_locations ORDER BY name ASC')
        return [cls(r) for r in rows]

    @classmethod
    def delete(cls, loc_id):
        db.execute('DELETE FROM safe_locations WHERE id = ?', (loc_id,))
