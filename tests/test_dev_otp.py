import unittest
import os
import sys
import io
from unittest.mock import patch, MagicMock

# Add project root to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app

class TestDevOtp(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = app.test_client()

    @patch('backend.auth.get_user_by_email')
    @patch('backend.auth.get_db_connection')
    @patch('backend.auth.send_verification_email')
    def test_register_prints_dev_otp_when_dev_mode_true(self, mock_send_email, mock_get_db, mock_get_user):
        mock_get_user.return_value = None
        mock_send_email.return_value = (True, "http://confirm")
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 123
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            with patch.dict(os.environ, {'DEV_MODE': 'true'}):
                response = self.client.post('/register', data={
                    'name': 'Dev User',
                    'email': 'dev@mouverse.com',
                    'phone': '1234567890',
                    'password': 'password123'
                }, follow_redirects=False)
                
            output_str = captured_output.getvalue()
            self.assertIn("Development OTP:", output_str)
        finally:
            sys.stdout = sys.__stdout__

    @patch('backend.auth.get_user_by_email')
    @patch('backend.auth.get_db_connection')
    @patch('backend.auth.send_verification_email')
    def test_register_does_not_print_dev_otp_when_dev_mode_false(self, mock_send_email, mock_get_db, mock_get_user):
        mock_get_user.return_value = None
        mock_send_email.return_value = (True, "http://confirm")
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 123
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            with patch.dict(os.environ, {'DEV_MODE': 'false'}):
                response = self.client.post('/register', data={
                    'name': 'Dev User',
                    'email': 'dev@mouverse.com',
                    'phone': '1234567890',
                    'password': 'password123'
                }, follow_redirects=False)
                
            output_str = captured_output.getvalue()
            self.assertNotIn("Development OTP:", output_str)
        finally:
            sys.stdout = sys.__stdout__

if __name__ == "__main__":
    unittest.main()
