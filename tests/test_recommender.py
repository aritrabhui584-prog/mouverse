import unittest
import sys
import os
import json
from dotenv import load_dotenv

# Add project root to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from backend.recommender import MovieRecommender, get_db_connection

class TestMovieRecommender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recommender = MovieRecommender()
        # Seed database if empty
        cls.recommender.populate_fallback_dataset()

    def test_usa_region_filter(self):
        # USA -> must not return Indian movies
        results, warning = self.recommender.recommend(
            mood="excited",
            genre="Sci-Fi",
            language="English",
            region="USA"
        )
        self.assertTrue(len(results) > 0, "Should return some movies for USA")
        for movie in results:
            region = movie.get("region", "")
            self.assertNotEqual(region.strip().lower(), "india", f"USA search should not return Indian movies: found {movie.get('title')}")

    def test_india_region_filter(self):
        # India -> must not return US-only movies
        results, warning = self.recommender.recommend(
            mood="happy",
            genre="Comedy",
            language="Hindi",
            region="India"
        )
        self.assertTrue(len(results) > 0, "Should return some movies for India")
        for movie in results:
            region = movie.get("region", "").strip().lower()
            self.assertNotIn(region, ["usa", "united states", "us"], f"India search should not return US movies: found {movie.get('title')}")

    def test_pakistan_region_filter_strict(self):
        # Pakistan -> must not return Indian movies unless fallback mode activates
        # Here we match "Maula Jatt" (Action, excited/thrilled/motivated, Punjabi/Urdu/etc.)
        # If we filter by Action/excited/motivated for Pakistan, Maula Jatt matches.
        # Fallback should NOT activate, and no Indian movies should be returned.
        results, warning = self.recommender.recommend(
            mood="excited",
            genre="Action",
            language="Punjabi",
            region="Pakistan"
        )
        self.assertTrue(len(results) > 0, "Should return some movies for Pakistan (strict)")
        self.assertIsNone(warning, "Warning should be None since Maula Jatt matches the criteria")
        for movie in results:
            region = movie.get("region", "").strip().lower()
            self.assertEqual(region, "pakistan", f"Should only return Pakistani movies: found {movie.get('title')} ({region})")

    def test_pakistan_region_filter_fallback(self):
        # Pakistan region is strictly Urdu/Punjabi. If we search for Hindi language in Pakistan,
        # since we removed fake movie generation, it should return 0 movies and warn the user.
        results, warning = self.recommender.recommend(
            mood="romantic",
            genre="Romance",
            language="Hindi",
            region="Pakistan"
        )
        self.assertEqual(len(results), 0, "Should return 0 recommendations since region/language matching is strict and fake movies are disabled")
        self.assertIsNotNone(warning, "Warning message should be returned when no movies are found")
        self.assertIn("No movies found for these filters", warning)

    def test_strict_region_language_usa(self):
        # USA region must strictly only allow English and Spanish language movies
        results, warning = self.recommender.recommend(
            mood="excited",
            genre="Action",
            language="English",
            region="USA"
        )
        self.assertTrue(len(results) >= 15, "Should return at least 15 recommendations")
        for movie in results:
            lang = movie.get("language", "")
            self.assertIn(lang, ["English", "Spanish"], f"USA recommendation should only return English or Spanish: found {movie.get('title')} ({lang})")

    def test_strict_region_language_india(self):
        # India region must strictly only allow Indian language movies
        results, warning = self.recommender.recommend(
            mood="happy",
            genre="Comedy",
            language="Hindi",
            region="India"
        )
        self.assertTrue(len(results) >= 15, "Should return at least 15 recommendations")
        indian_languages = ["Hindi", "Bengali", "Tamil", "Telugu", "Marathi", "Urdu", "Malayalam", "Kannada", "Punjabi"]
        for movie in results:
            lang = movie.get("language", "")
            self.assertIn(lang, indian_languages, f"India recommendation should only return Indian languages: found {movie.get('title')} ({lang})")

if __name__ == "__main__":
    unittest.main()
