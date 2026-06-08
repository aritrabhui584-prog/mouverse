import unittest
import os
import sys
import json
import shutil
from unittest.mock import patch, MagicMock

# Add project root to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app, get_or_download_poster, load_poster_search_cache, save_poster_search_cache

class TestPosterPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.posters_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public", "posters")
        cls.new_cache_file = os.path.join(cls.posters_dir, "poster_search_cache.json")
        cls.old_cache_file = os.path.join(cls.posters_dir, "poster_cache.json")
        
        # Backup existing caches if they exist
        cls.new_cache_backup = None
        cls.old_cache_backup = None
        
        if os.path.exists(cls.new_cache_file):
            with open(cls.new_cache_file, "r", encoding="utf-8") as f:
                cls.new_cache_backup = f.read()
                
        if os.path.exists(cls.old_cache_file):
            with open(cls.old_cache_file, "r", encoding="utf-8") as f:
                cls.old_cache_backup = f.read()

    @classmethod
    def tearDownClass(cls):
        # Restore backups
        if cls.new_cache_backup is not None:
            with open(cls.new_cache_file, "w", encoding="utf-8") as f:
                f.write(cls.new_cache_backup)
        elif os.path.exists(cls.new_cache_file):
            os.remove(cls.new_cache_file)
            
        if cls.old_cache_backup is not None:
            with open(cls.old_cache_file, "w", encoding="utf-8") as f:
                f.write(cls.old_cache_backup)
        elif os.path.exists(cls.old_cache_file):
            os.remove(cls.old_cache_file)

    def setUp(self):
        # Clear cache files before each test to start fresh
        if os.path.exists(self.new_cache_file):
            os.remove(self.new_cache_file)
        if os.path.exists(self.old_cache_file):
            os.remove(self.old_cache_file)
            
        # Mock recommender API key attributes
        from backend.app import recommender
        self.recommender_tmdb_enabled = getattr(recommender, "tmdb_enabled", True)
        self.recommender_omdb_enabled = getattr(recommender, "omdb_enabled", True)
        recommender.tmdb_enabled = True
        recommender.omdb_enabled = True

    def tearDown(self):
        from backend.app import recommender
        recommender.tmdb_enabled = self.recommender_tmdb_enabled
        recommender.omdb_enabled = self.recommender_omdb_enabled

    @patch('requests.get')
    @patch('sys.stdout')
    def test_priority_tmdb_success(self, mock_stdout, mock_get):
        # Mock TMDB returning success
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"title": "Test Movie", "poster_path": "/test_tmdb_path.jpg"}
            ]
        }
        mock_get.return_value = mock_response

        # Execute
        with patch.dict(os.environ, {"TMDB_API_KEY": "valid_key", "OMDB_API_KEY": "valid_key"}):
            url = get_or_download_poster(movie_id="101", title="Test Movie", tmdb_poster_url=None, year="2026", language="English")
            
        self.assertEqual(url, "https://image.tmdb.org/t/p/w500/test_tmdb_path.jpg")
        
        # Verify cached entries
        cache = load_poster_search_cache()
        self.assertIn("101", cache)
        self.assertEqual(cache["101"]["poster_url"], "https://image.tmdb.org/t/p/w500/test_tmdb_path.jpg")
        self.assertEqual(cache["101"]["tmdb_result"], "https://image.tmdb.org/t/p/w500/test_tmdb_path.jpg")
        self.assertEqual(cache["101"]["omdb_result"], "None")

    @patch('requests.get')
    def test_priority_omdb_fallback(self, mock_get):
        # Mock TMDB returning no results, OMDb returning success
        def mock_requests_get(url, *args, **kwargs):
            r = MagicMock()
            r.status_code = 200
            if "api.tmdb.org" in url:
                r.json.return_value = {"results": []}
            elif "omdbapi.com" in url:
                r.json.return_value = {"Response": "True", "Poster": "http://example.com/omdb_poster.jpg"}
            return r
            
        mock_get.side_effect = mock_requests_get

        with patch.dict(os.environ, {"TMDB_API_KEY": "valid_key", "OMDB_API_KEY": "valid_key"}):
            url = get_or_download_poster(movie_id="102", title="OMDb Movie", tmdb_poster_url=None, year="2026", language="English")
            
        self.assertEqual(url, "http://example.com/omdb_poster.jpg")
        
        # Verify cached entries
        cache = load_poster_search_cache()
        self.assertIn("102", cache)
        self.assertEqual(cache["102"]["poster_url"], "http://example.com/omdb_poster.jpg")
        self.assertEqual(cache["102"]["tmdb_result"], "None")
        self.assertEqual(cache["102"]["omdb_result"], "http://example.com/omdb_poster.jpg")

    @patch('requests.get')
    def test_local_folder_fallback_when_apis_fail(self, mock_get):
        # Mock both TMDB and OMDb returning nothing
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [], "Response": "False"}
        mock_get.return_value = mock_response

        # Create a mock local file
        local_file_path = os.path.join(self.posters_dir, "103.jpg")
        with open(local_file_path, "w") as f:
            f.write("dummy image content")
            
        try:
            with patch.dict(os.environ, {"TMDB_API_KEY": "valid_key", "OMDB_API_KEY": "valid_key"}):
                url = get_or_download_poster(movie_id="103", title="Local Movie", tmdb_poster_url=None, year="2026", language="English")
                
            self.assertEqual(url, "/posters/103.jpg")
            
            # Verify cached entries
            cache = load_poster_search_cache()
            self.assertIn("103", cache)
            self.assertEqual(cache["103"]["poster_url"], "/posters/103.jpg")
            self.assertEqual(cache["103"]["tmdb_result"], "None")
            self.assertEqual(cache["103"]["omdb_result"], "None")
        finally:
            if os.path.exists(local_file_path):
                os.remove(local_file_path)

    @patch('requests.get')
    def test_default_poster_fallback(self, mock_get):
        # Mock both TMDB and OMDb returning nothing
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [], "Response": "False"}
        mock_get.return_value = mock_response

        with patch.dict(os.environ, {"TMDB_API_KEY": "valid_key", "OMDB_API_KEY": "valid_key"}):
            url = get_or_download_poster(movie_id="104", title="Default Fallback Movie", tmdb_poster_url=None, year="2026", language="English")
            
        self.assertEqual(url, "/posters/default-poster.jpg")

    def test_backwards_compatibility_conversion(self):
        # Write old format cache file
        old_cache = {
            "Inception Old": "/posters/inception-old.jpg",
            "id_105": "/posters/105.jpg"
        }
        with open(self.old_cache_file, "w", encoding="utf-8") as f:
            json.dump(old_cache, f)
            
        # Trigger cache load
        cache = load_poster_search_cache()
        
        self.assertIn("Inception Old", cache)
        self.assertEqual(cache["Inception Old"]["poster_url"], "/posters/inception-old.jpg")
        self.assertEqual(cache["Inception Old"]["movie_title"], "Inception Old")
        
        self.assertIn("105", cache)
        self.assertEqual(cache["105"]["poster_url"], "/posters/105.jpg")
        self.assertEqual(cache["105"]["movie_id"], "105")

if __name__ == "__main__":
    unittest.main()
