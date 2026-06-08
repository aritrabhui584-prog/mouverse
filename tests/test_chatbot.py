import unittest
import os
import sys
from unittest.mock import patch

# Add project root to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app, _chatbot_reply, _detect_language, _detect_emotion

class TestChatbotBackend(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = app.test_client()

    def test_language_detection(self):
        # English
        self.assertEqual(_detect_language("hello, what is the movie about?"), "english")
        # Bengali script range check
        self.assertEqual(_detect_language("আমি সিনেমা দেখতে চাই"), "bengali")
        # Hindi script range check
        self.assertEqual(_detect_language("मुझे एक अच्छी फिल्म बताओ"), "hindi")
        # Tamil script range check
        self.assertEqual(_detect_language("எனக்கு ஒரு படம் பரிந்துரைக்கவும்"), "tamil")

    def test_emotion_detection(self):
        self.assertEqual(_detect_emotion("i am feeling very sad today"), "sad")
        self.assertEqual(_detect_emotion("this is happy news"), "happy")
        self.assertEqual(_detect_emotion("so bored right now"), "bored")
        self.assertEqual(_detect_emotion("highly stressed out"), "stressed")

    def test_restricted_topics_safety(self):
        # Medical advice block - English
        reply_en = _chatbot_reply("can you give me some medical advice?", "happy", "USA")
        self.assertIn("not a professional advisor", reply_en)
        self.assertIn("medical, legal, or financial", reply_en)

        # Medical advice block - Bengali
        reply_bn = _chatbot_reply("আমাকে একটু medical advice দাও", "happy", "India")
        self.assertIn("আমি তোমার সিনেমা সঙ্গী, পেশাদার উপদেষ্টা নই", reply_bn)

        # Financial advice block - Hindi
        reply_hi = _chatbot_reply("मुझे financial advice दो", "happy", "India")
        self.assertIn("मैं आपका AI फिल्म साथी हूं, पेशेवर सलाहकार नहीं", reply_hi)

    def test_greetings_and_time(self):
        # Test greeting response matches structure
        reply_greet = _chatbot_reply("hi, hello there!", "happy", "USA", user_name="Test User", client_hour=10)
        reply_greet_lower = reply_greet.lower()
        self.assertTrue(any(g in reply_greet_lower for g in ["morning", "hello", "hi", "rise", "afternoon", "evening", "night"]))
        self.assertIn("Test User", reply_greet)

        # Test time response matches structure
        reply_time = _chatbot_reply("what time is it?", "happy", "India", user_name="Alex", client_time="11:30 PM", client_hour=23, timezone="Asia/Kolkata")
        self.assertIn("11:30 PM", reply_time)
        self.assertIn("Kolkata", reply_time)
        self.assertIn("Alex", reply_time)

    def test_dynamic_genre_recommendations(self):
        # Test comedy recommendations
        reply = _chatbot_reply("recommend me a comedy", "happy", "India")
        # Since comedy exists in the database, it should list dynamic comedies or fall back gracefully
        self.assertTrue(
            "Comedy" in reply or "comedy" in reply
        )
        self.assertTrue(
            "Great taste!" in reply or "I'm here to help" in reply
        )

if __name__ == "__main__":
    unittest.main()
