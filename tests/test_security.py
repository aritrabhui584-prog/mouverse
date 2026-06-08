import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock

# Add project root to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app

class TestSecurity(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = app.test_client()

    def test_debug_otp_endpoint_forbidden_in_production(self):
        # Force production mode (no debug, no DEV_MODE)
        app.debug = False
        with patch.dict(os.environ, {'DEV_MODE': 'false'}):
            response = self.client.get('/api/debug/otp')
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.data.decode('utf-8'))
        self.assertFalse(data['success'])
        self.assertIn("Access denied", data['error'])


    def test_debug_otp_endpoint_allowed_in_development_not_found(self):
        # Force development mode
        app.debug = True
        # Without any pending verification, it should return 404
        response = self.client.get('/api/debug/otp')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data.decode('utf-8'))
        self.assertFalse(data['success'])

    @patch('backend.auth.get_user_by_email')
    @patch('backend.auth.get_db_connection')
    def test_registration_exception_sanitized(self, mock_get_db, mock_get_user_by_email):
        # Mock user email check to return None (user doesn't exist yet)
        mock_get_user_by_email.return_value = None

        # Make database execution throw a raw exception
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("RAW DATABASE ERROR: TABLE CRASHED!")
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        # Attempt to register
        response = self.client.post('/register', data={
            'name': 'Test User',
            'email': 'nonexistent_sec@mouverse.com',
            'phone': '1234567890',
            'password': 'password123'
        }, follow_redirects=True)

        # Ensure the response HTML does NOT leak the raw exception text
        html_content = response.data.decode('utf-8')
        self.assertNotIn("RAW DATABASE ERROR", html_content)
        self.assertIn("A database error occurred during registration", html_content)

    @patch('backend.app.get_db_connection')
    def test_debug_otp_endpoint_enriched_in_development(self, mock_get_db):
        # Force development mode
        app.debug = True
        
        # Mock database row
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_row = {'otp_code': '987654', 'expires_at': '2026-06-06 20:50:00'}
        mock_cursor.fetchone.return_value = mock_row
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn
        
        # Set session variable for pending verification email
        with self.client.session_transaction() as sess:
            sess['pending_verification_email'] = 'test_sec@mouverse.com'
            
        with patch.dict(os.environ, {'DEV_MODE': 'true'}):
            response = self.client.get('/api/debug/otp')
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data.decode('utf-8'))
            self.assertTrue(data['success'])
            self.assertEqual(data['otp'], '987654')
            self.assertIn('created_at', data)
            self.assertEqual(data['expires_at'], '2026-06-06 20:50:00')
            self.assertEqual(data['created_at'], '2026-06-06 20:45:00')
            self.assertTrue(data['dev_mode'])

if __name__ == "__main__":
    unittest.main()
