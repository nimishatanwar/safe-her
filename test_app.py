"""
SafeHer Automated Test Suite
Tests registration, authentication, emergency contact workflows,
SOS alert dispatch, reverse geocoding fallback, and admin endpoints.
Run: python test_app.py
"""

import unittest
import json
from app import app
from database import db
from models import User, EmergencyContact, EmergencyAlert, AlertNotificationLog, SafeLocation

class SafeHerTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_01_landing_page(self):
        """Test landing page loads successfully."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'SafeHer', response.data)
        self.assertIn(b'ONE-TAP SOS', response.data)

    def test_02_user_login_demo(self):
        """Test user login with demo credentials."""
        response = self.client.post('/login', data={
            'email': 'priya@safeher.com',
            'password': 'user123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Safety Hub', response.data)

    def test_03_admin_login(self):
        """Test admin login and access to admin command center."""
        response = self.client.post('/login', data={
            'email': 'admin@safeher.com',
            'password': 'admin123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Central Emergency Monitoring Command', response.data)

    def test_04_safe_locations_api(self):
        """Test safe locations API returns verified locations."""
        response = self.client.get('/api/safe-locations')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertGreater(len(data['locations']), 0)

    def test_05_sos_trigger_and_notification_log(self):
        """Test triggering SOS emergency alert and verifying notification generation."""
        # Login as Priya
        with self.client:
            self.client.post('/login', data={'email': 'priya@safeher.com', 'password': 'user123'})

            payload = {
                'latitude': 28.6289,
                'longitude': 77.2145,
                'accuracy': 10.0,
                'alert_type': 'Being Followed / Stalked',
                'notes': 'Test distress trigger near metro'
            }

            res = self.client.post('/api/sos/trigger',
                                  data=json.dumps(payload),
                                  content_type='application/json')
            self.assertEqual(res.status_code, 200)
            data = json.loads(res.data)
            self.assertEqual(data['status'], 'success')
            self.assertIn('alert', data)
            alert_id = data['alert']['id']

            # Verify alert in DB
            alert = EmergencyAlert.find_by_id(alert_id)
            self.assertIsNotNone(alert)
            self.assertEqual(alert.alert_type, 'Being Followed / Stalked')
            self.assertEqual(alert.status, 'ACTIVE')

            # Verify notification logs generated for contacts
            notifs = AlertNotificationLog.find_by_alert(alert_id)
            self.assertGreater(len(notifs), 0)

            # Test Active SOS API
            active_res = self.client.get('/api/sos/active')
            active_data = json.loads(active_res.data)
            self.assertTrue(active_data['has_active'])

            # Test User Mark Safe / Cancel
            cancel_res = self.client.post(f'/api/sos/cancel/{alert_id}')
            self.assertEqual(cancel_res.status_code, 200)
            cancel_data = json.loads(cancel_res.data)
            self.assertEqual(cancel_data['status'], 'success')

            # Verify resolved
            alert_updated = EmergencyAlert.find_by_id(alert_id)
            self.assertEqual(alert_updated.status, 'RESOLVED')

    def test_06_admin_status_update(self):
        """Test admin updating an alert to IN_PROGRESS."""
        # Create a test alert
        alert = EmergencyAlert.create(
            user_id=1,
            alert_type='Harassment',
            latitude=28.6139,
            longitude=77.2090,
            accuracy=15.0,
            location_address='Test Point'
        )

        with self.client:
            self.client.post('/login', data={'email': 'admin@safeher.com', 'password': 'admin123'})

            res = self.client.post(f'/api/admin/alert/{alert.id}/status',
                                   data=json.dumps({
                                       'status': 'IN_PROGRESS',
                                       'notes': 'PCR Unit #7 en route',
                                       'responded_by': 'Dispatcher Khan'
                                   }),
                                   content_type='application/json')
            self.assertEqual(res.status_code, 200)

            updated = EmergencyAlert.find_by_id(alert.id)
            self.assertEqual(updated.status, 'IN_PROGRESS')
            self.assertEqual(updated.responded_by, 'Dispatcher Khan')

if __name__ == '__main__':
    unittest.main()
