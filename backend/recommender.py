import os
import sqlite3
import json
import requests
import re
import logging
from datetime import datetime
from backend.extended_dataset import extended_dataset

# Genre and language mappings for TMDB
TMDB_GENRES = {
    "Action": 28,
    "Adventure": 12,
    "Animation": 16,
    "Comedy": 35,
    "Crime": 80,
    "Documentary": 99,
    "Drama": 18,
    "Family": 10751,
    "Fantasy": 14,
    "History": 36,
    "Horror": 27,
    "Music": 10402,
    "Mystery": 9648,
    "Romance": 10749,
    "Sci-Fi": 878,
    "Thriller": 53,
    "War": 10752,
    "Western": 37
}

LANG_MAP = {
    "English": "en",
    "Hindi": "hi",
    "Bengali": "bn",
    "Tamil": "ta",
    "Telugu": "te",
    "Malayalam": "ml",
    "Kannada": "kn",
    "Marathi": "mr",
    "Punjabi": "pa",
    "Korean": "ko",
    "Japanese": "ja",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Urdu": "ur"
}

# Mood-to-genre/keyword mappings
MOOD_GENRES = {
    "happy": ["Comedy", "Family", "Feel Good"],
    "sad": ["Drama", "Emotional"],
    "excited": ["Adventure", "Action"],
    "romantic": ["Romance"],
    "thrilled": ["Thriller", "Mystery"],
    "thrilling": ["Thriller", "Mystery"],
    "motivated": ["Biography", "Sports", "Inspirational"],
    "dark": ["Crime", "Psychological", "Noir"],
    "funny": ["Comedy"]
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "mouverse.db")

logger = logging.getLogger(__name__)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def is_region_match(movie_or_region, selected_region):
    """
    Match a movie's region against the selected region with simplified logic.
    Supports either a movie dictionary or a raw region string.
    """
    if not selected_region:
        return True
    
    sr = selected_region.strip().lower()
    
    if isinstance(movie_or_region, dict):
        movie = movie_or_region
    else:
        movie = {
            "region": movie_or_region,
            "country": movie_or_region,
            "origin_country": "IN" if movie_or_region.strip().lower() == "india" else ("US" if movie_or_region.strip().lower() in ["usa", "united states", "us"] else ""),
            "language": ""
        }
    
    movie_region = (movie.get("region") or "").strip().lower()
    movie_country = (movie.get("country") or "").strip().lower()
    movie_origin_country = (movie.get("origin_country") or "").strip().lower()
    movie_language = (movie.get("language") or "").strip().lower()
    
    # Parse list format or comma-separated format for countries
    origin_countries = [c.strip() for c in movie_origin_country.replace("[", "").replace("]", "").replace("'", "").replace('"', '').split(",") if c.strip()]
    countries = [c.strip() for c in movie_country.split(",") if c.strip()]
    
    is_match = False
    
    # Simplified region matching logic
    if sr == "india":
        is_india = (
            movie_region == "india" or
            "india" in countries or
            "in" in origin_countries
        )
        allowed_indian_langs = {"hindi", "bengali", "tamil", "telugu", "marathi", "urdu", "malayalam", "kannada", "punjabi"}
        is_match = is_india and (movie_language in allowed_indian_langs or movie_language == "")
        
    elif sr in ["usa", "united states", "us"]:
        # Fixed: Removed UK from USA match
        is_usa = (
            movie_region in ["usa", "united states", "us", "international"] or
            any(c in countries for c in ["usa", "united states", "united states of america"]) or
            "us" in origin_countries
        )
        is_indian_lang = movie_language in {"hindi", "bengali", "tamil", "telugu", "marathi", "urdu", "malayalam", "kannada", "punjabi"}
        is_indian_region = (
            movie_region == "india" or
            "india" in countries or
            "in" in origin_countries
        )
        is_match = is_usa and not is_indian_lang and not is_indian_region
        
    elif sr in ["uk", "united kingdom"]:
        is_uk = (
            movie_region in ["uk", "united kingdom", "international"] or
            any(c in countries for c in ["united kingdom", "uk"]) or
            "gb" in origin_countries
        )
        is_match = is_uk and movie_language == "english"
        
    elif sr == "korea":
        is_korea = (
            movie_region in ["korea", "south korea"] or
            "korea" in countries or
            "south korea" in countries or
            "kr" in origin_countries
        )
        is_match = is_korea and movie_language == "korean"
        
    elif sr == "japan":
        is_japan = (
            movie_region == "japan" or
            "japan" in countries or
            "jp" in origin_countries
        )
        is_match = is_japan and movie_language == "japanese"
        
    elif sr == "bangladesh":
        is_bangladesh = (
            movie_region == "bangladesh" or
            "bangladesh" in countries or
            "bd" in origin_countries
        )
        is_match = is_bangladesh and movie_language == "bengali"
        
    elif sr == "pakistan":
        is_pakistan = (
            movie_region == "pakistan" or
            "pakistan" in countries or
            "pk" in origin_countries
        )
        is_match = is_pakistan and movie_language in ["urdu", "punjabi"]
        
    else:
        is_match = (movie_region == sr or sr in countries or sr in origin_countries)
    
    # Use proper logging instead of print
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Region Match - Selected: {selected_region}, Movie Country: {movie_country or 'N/A'}, Movie Language: {movie_language or 'N/A'}, Match: {is_match}")
    
    return is_match

def is_mood_match(movie, mood):
    if not mood:
        return True
    mood_lower = mood.lower()
    
    # 1. Check keywords / mood tags
    keywords = movie.get("keywords")
    if isinstance(keywords, str):
        try:
            k_list = json.loads(keywords)
        except Exception:
            k_list = keywords.split()
    elif isinstance(keywords, list):
        k_list = keywords
    else:
        k_list = []
    
    if any(mood_lower == k.lower() for k in k_list):
        return True
        
    # 2. Check associated genres
    associated_genres = MOOD_GENRES.get(mood_lower, [])
        
    movie_genres = movie.get("genres", [])
    if any(ag.lower() in [mg.lower() for mg in movie_genres] for ag in associated_genres):
        return True
        
    # 3. Check overview
    if mood_lower in (movie.get("overview") or "").lower():
        return True
        
    return False

class MovieRecommender:
    def __init__(self):
        # Base setup
        logger.info("Upgraded Hybrid MovieRecommender Initialized!")
        tmdb_key = os.getenv("TMDB_API_KEY")
        omdb_key = os.getenv("OMDB_API_KEY")
        logger.info(f"TMDB API key loaded: {'YES' if tmdb_key else 'NO'}")
        logger.info(f"OMDb API key loaded: {'YES' if omdb_key else 'NO'}")
        self.tmdb_enabled = True if tmdb_key else False
        self.omdb_enabled = True if omdb_key else False
    
    def _get_extended_dataset_fallback(self, genre, mood, min_rating, max_runtime, limit):
        """
        Fallback to extended dataset when main dataset doesn't have enough results.
        This doesn't hamper the main project as it only activates when needed.
        """
        try:
            # Get movies from extended dataset based on genre or top-rated
            if genre and genre.strip():
                extended_results = extended_dataset.get_movies_by_genre(genre, limit * 3)
            else:
                extended_results = extended_dataset.get_top_rated(limit * 3, min_ratings=1)
            
            # Convert to standard format and apply filters
            converted_movies = []
            for movie in extended_results:
                standard_movie = extended_dataset.convert_to_standard_format(movie)
                
                # Apply mood filter if specified
                if mood and mood.strip():
                    if not is_mood_match(standard_movie, mood):
                        continue
                
                # Apply rating filter (relaxed for extended dataset)
                if min_rating and standard_movie.get('rating', 0) < min_rating:
                    continue
                
                # Apply runtime filter
                if max_runtime and standard_movie.get('runtime', 120) > max_runtime:
                    continue
                
                # Generate a unique ID for extended movies
                standard_movie['id'] = f"ext_{movie.get('movieId', '')}"
                
                converted_movies.append(standard_movie)
                
                if len(converted_movies) >= limit:
                    break
            
            return converted_movies
        except Exception as e:
            logger.error(f"Error getting extended dataset fallback: {e}")
            return []

    def populate_fallback_dataset(self):
        """Populate database with fallback dataset if empty"""
        logger.info("Seeding database with real fallback movie dataset")
        
        fallback_movies = [
            # INDIA MOVIES
            {
                "id": "1", "title": "3 Idiots", "language": "Hindi", "region": "India",
                "genre": ["Comedy", "Drama"], "runtime": 170, "year": "2009",
                "rating": 8.9, "overview": "Two friends search for their long lost companion.",
                "poster": "/posters/3-idiots.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=K0eDlFX9GMc",
                "cast": ["Aamir Khan", "Madhavan", "Sharman Joshi"],
                "director": "Rajkumar Hirani", "keywords": ["happy", "funny", "motivated"]
            },
            {
                "id": "2", "title": "Sholay", "language": "Hindi", "region": "India",
                "genre": ["Action", "Adventure"], "runtime": 204, "year": "1975",
                "rating": 9.0, "overview": "A retired police officer sets out to capture a dacoit.",
                "poster": "/posters/sholay.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=R8a0f7bYf2M",
                "cast": ["Amitabh Bachchan", "Dharmendra", "Hema Malini"],
                "director": "Ramesh Sippy", "keywords": ["action", "thrilling", "excited"]
            },
            {
                "id": "3", "title": "Zindagi Na Milegi Dobara", "language": "Hindi", "region": "India",
                "genre": ["Comedy", "Drama"], "runtime": 155, "year": "2011",
                "rating": 8.8, "overview": "Three friends decide to turn their fantasy vacation into reality.",
                "poster": "/posters/zindagi-na-milegi-dobara.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=KXe8y1k6qXc",
                "cast": ["Hrithik Roshan", "Farhan Akhtar", "Abhay Deol"],
                "director": "Zoya Akhtar", "keywords": ["happy", "excited", "funny"]
            },
            {
                "id": "4", "title": "Dangal", "language": "Hindi", "region": "India",
                "genre": ["Biography", "Drama", "Sports"], "runtime": 161, "year": "2016",
                "rating": 8.9, "overview": "A former wrestler trains his daughters to become world-class wrestlers.",
                "poster": "/posters/dangal.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=x_7YlGv9u1g",
                "cast": ["Aamir Khan", "Fatima Sana Shaikh", "Sanya Malhotra"],
                "director": "Nitesh Tiwari", "keywords": ["motivated", "inspirational", "sports"]
            },
            {
                "id": "5", "title": "RRR", "language": "Telugu", "region": "India",
                "genre": ["Action", "Drama"], "runtime": 187, "year": "2022",
                "rating": 8.7, "overview": "A fearless revolutionary and an officer in the British force become friends.",
                "poster": "/posters/rrr.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=NgBoMJy386M",
                "cast": ["N.T. Rama Rao Jr.", "Ram Charan", "Ajay Devgn"],
                "director": "S.S. Rajamouli", "keywords": ["excited", "motivated", "action"]
            },
            {
                "id": "6", "title": "Drishyam", "language": "Malayalam", "region": "India",
                "genre": ["Thriller", "Crime"], "runtime": 160, "year": "2013",
                "rating": 8.9, "overview": "A man covers up a crime committed by his family.",
                "poster": "/posters/drishyam.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=5XOzJH8I3L0",
                "cast": ["Mohanlal", "Meena", "Asha Sarath"],
                "director": "Jeethu Joseph", "keywords": ["thrilling", "mystery", "dark"]
            },
            {
                "id": "7", "title": "The Dark Knight", "language": "English", "region": "International",
                "genre": ["Action", "Crime", "Drama"], "runtime": 152, "year": "2008",
                "rating": 9.0, "overview": "Batman raises the stakes in his war on crime.",
                "poster": "/posters/the-dark-knight.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=EXeTwQWrcwY",
                "cast": ["Christian Bale", "Heath Ledger", "Aaron Eckhart"],
                "director": "Christopher Nolan", "keywords": ["dark", "thrilling", "motivated"]
            },
            {
                "id": "8", "title": "Inception", "language": "English", "region": "International",
                "genre": ["Action", "Adventure", "Sci-Fi"], "runtime": 148, "year": "2010",
                "rating": 8.8, "overview": "A thief who steals corporate secrets through dream-sharing.",
                "poster": "/posters/inception.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=YoHD9XEInc0",
                "cast": ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Ellen Page"],
                "director": "Christopher Nolan", "keywords": ["excited", "motivated", "thrilling"]
            },
            {
                "id": "9", "title": "The Shawshank Redemption", "language": "English", "region": "International",
                "genre": ["Drama"], "runtime": 142, "year": "1994",
                "rating": 9.3, "overview": "Two imprisoned men bond over a number of years.",
                "poster": "/posters/the-shawshank-redemption.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=6hB3S9bIaco",
                "cast": ["Tim Robbins", "Morgan Freeman", "Bob Gunton"],
                "director": "Frank Darabont", "keywords": ["motivated", "sad", "happy"]
            },
            {
                "id": "10", "title": "Interstellar", "language": "English", "region": "International",
                "genre": ["Adventure", "Drama", "Sci-Fi"], "runtime": 169, "year": "2014",
                "rating": 8.7, "overview": "A team of explorers travel through a wormhole.",
                "poster": "/posters/interstellar.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=zSWdZVtXT7E",
                "cast": ["Matthew McConaughey", "Anne Hathaway", "Jessica Chastain"],
                "director": "Christopher Nolan", "keywords": ["sad", "motivated", "excited"]
            },
            {
                "id": "11", "title": "Baahubali: The Beginning", "language": "Telugu", "region": "India",
                "genre": ["Action", "Adventure"], "runtime": 159, "year": "2015",
                "rating": 8.0, "overview": "A young man learns about his royal heritage.",
                "poster": "/posters/baahubali-the-beginning.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=sOEg_YZQsTI",
                "cast": ["Prabhas", "Rana Daggubati", "Anushka Shetty"],
                "director": "S.S. Rajamouli", "keywords": ["excited", "motivated", "thrilling"]
            },
            {
                "id": "12", "title": "Kumbalangi Nights", "language": "Malayalam", "region": "India",
                "genre": ["Comedy", "Drama", "Romance"], "runtime": 135, "year": "2019",
                "rating": 8.6, "overview": "Four brothers share a love-hate relationship.",
                "poster": "/posters/kumbalangi-nights.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=5XOzJH8I3L0",
                "cast": ["Fahadh Faasil", "Soubin Shahir", "Dileesh Pothan"],
                "director": "Madhu C. Narayanan", "keywords": ["happy", "funny", "romantic"]
            },
            {
                "id": "13", "title": "Pather Panchali", "language": "Bengali", "region": "India",
                "genre": ["Drama"], "runtime": 125, "year": "1955",
                "rating": 8.3, "overview": "A young boy Apu grows up in a poor village in Bengal.",
                "poster": "/posters/pather-panchali.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=kXoOeaJ6uL4",
                "cast": ["Subir Banerjee", "Kanu Banerjee"],
                "director": "Satyajit Ray", "keywords": ["sad", "dark", "motivated"]
            },
            {
                "id": "14", "title": "Apur Sansar", "language": "Bengali", "region": "India",
                "genre": ["Drama"], "runtime": 105, "year": "1959",
                "rating": 8.2, "overview": "The final part of Satyajit Ray's acclaimed Apu Trilogy.",
                "poster": "/posters/apur-sansar.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=0w51p_SUpD0",
                "cast": ["Soumitra Chatterjee", "Sharmila Tagore"],
                "director": "Satyajit Ray", "keywords": ["emotional", "deep", "classic"]
            },
            {
                "id": "15", "title": "Charulata", "language": "Bengali", "region": "India",
                "genre": ["Drama", "Romance"], "runtime": 117, "year": "1964",
                "rating": 8.1, "overview": "A lonely housewife in Bengal falls in love with her husband's cousin.",
                "poster": "/posters/charulata.jpg",
                "trailer_url": "",
                "cast": ["Madhabi Mukherjee", "Soumitra Chatterjee"],
                "director": "Satyajit Ray", "keywords": ["romantic", "love", "emotional"]
            },
            {
                "id": "16", "title": "Mahanagar", "language": "Bengali", "region": "India",
                "genre": ["Drama"], "runtime": 131, "year": "1963",
                "rating": 8.2, "overview": "A housewife challenges social norms by getting a job in Calcutta.",
                "poster": "/posters/mahanagar.jpg",
                "trailer_url": "",
                "cast": ["Madhabi Mukherjee", "Anil Chatterjee"],
                "director": "Satyajit Ray", "keywords": ["motivated", "social", "classic"]
            },
            # USA MOVIES
            {
                "id": "17", "title": "The Godfather", "language": "English", "region": "USA",
                "genre": ["Crime", "Drama"], "runtime": 175, "year": "1972",
                "rating": 9.2, "overview": "The aging patriarch of an organized crime dynasty transfers control to his reluctant son.",
                "poster": "/posters/the-godfather.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=sY1S34973zA",
                "cast": ["Marlon Brando", "Al Pacino", "James Caan"],
                "director": "Francis Ford Coppola", "keywords": ["dark", "thrilling", "motivated"]
            },
            {
                "id": "18", "title": "Pulp Fiction", "language": "English", "region": "USA",
                "genre": ["Crime", "Drama"], "runtime": 154, "year": "1994",
                "rating": 8.9, "overview": "The lives of two mob hitmen, a boxer, and a gangster's wife intertwine.",
                "poster": "/posters/pulp-fiction.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=s7EdQ4FqbhY",
                "cast": ["John Travolta", "Uma Thurman", "Samuel L. Jackson"],
                "director": "Quentin Tarantino", "keywords": ["dark", "thrilling", "excited"]
            },
            {
                "id": "19", "title": "Forrest Gump", "language": "English", "region": "USA",
                "genre": ["Drama", "Romance"], "runtime": 142, "year": "1994",
                "rating": 8.8, "overview": "The presidencies of Kennedy and Johnson through the eyes of an Alabama man.",
                "poster": "/posters/forrest-gump.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=bLVqTeFY4vY",
                "cast": ["Tom Hanks", "Robin Wright", "Gary Sinise"],
                "director": "Robert Zemeckis", "keywords": ["happy", "motivated", "emotional"]
            },
            {
                "id": "20", "title": "The Matrix", "language": "English", "region": "USA",
                "genre": ["Action", "Sci-Fi"], "runtime": 136, "year": "1999",
                "rating": 8.7, "overview": "A computer hacker learns about the true nature of reality and his role in the war against its controllers.",
                "poster": "/posters/the-matrix.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=vKQi3bBA1y8",
                "cast": ["Keanu Reeves", "Laurence Fishburne", "Carrie-Anne Moss"],
                "director": "The Wachowskis", "keywords": ["excited", "motivated", "thrilling"]
            },
            {
                "id": "21", "title": "Fight Club", "language": "English", "region": "USA",
                "genre": ["Drama"], "runtime": 139, "year": "1999",
                "rating": 8.8, "overview": "An insomniac office worker and a devil-may-care soap maker form an underground fight club.",
                "poster": "/posters/fight-club.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=SUXWAEX2jlg",
                "cast": ["Brad Pitt", "Edward Norton", "Helena Bonham Carter"],
                "director": "David Fincher", "keywords": ["dark", "thrilling", "excited"]
            },
            {
                "id": "22", "title": "The Silence of the Lambs", "language": "English", "region": "USA",
                "genre": ["Crime", "Drama", "Thriller"], "runtime": 118, "year": "1991",
                "rating": 8.6, "overview": "A young FBI cadet must receive the help of an incarcerated cannibalistic serial killer.",
                "poster": "/posters/the-silence-of-the-lambs.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=U1f_s7n2p3o",
                "cast": ["Jodie Foster", "Anthony Hopkins", "Scott Glenn"],
                "director": "Jonathan Demme", "keywords": ["dark", "thrilling", "mystery"]
            },
            {
                "id": "23", "title": "Saving Private Ryan", "language": "English", "region": "USA",
                "genre": ["Drama", "War"], "runtime": 169, "year": "1998",
                "rating": 8.6, "overview": "Following the Normandy Landings, a group of U.S. soldiers go behind enemy lines.",
                "poster": "/posters/saving-private-ryan.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=BFhGvDk4kYI",
                "cast": ["Tom Hanks", "Matt Damon", "Tom Sizemore"],
                "director": "Steven Spielberg", "keywords": ["motivated", "dark", "emotional"]
            },
            {
                "id": "24", "title": "Gladiator", "language": "English", "region": "USA",
                "genre": ["Action", "Adventure", "Drama"], "runtime": 155, "year": "2000",
                "rating": 8.5, "overview": "A former Roman General sets out to exact vengeance against the corrupt emperor.",
                "poster": "/posters/gladiator.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=owK1Qp9T8cE",
                "cast": ["Russell Crowe", "Joaquin Phoenix", "Connie Nielsen"],
                "director": "Ridley Scott", "keywords": ["motivated", "excited", "thrilling"]
            },
            {
                "id": "25", "title": "The Departed", "language": "English", "region": "USA",
                "genre": ["Crime", "Drama", "Thriller"], "runtime": 151, "year": "2006",
                "rating": 8.5, "overview": "An undercover cop and a mole in the police attempt to identify each other.",
                "poster": "/posters/the-departed.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=io5qm-4r8k0",
                "cast": ["Leonardo DiCaprio", "Matt Damon", "Jack Nicholson"],
                "director": "Martin Scorsese", "keywords": ["dark", "thrilling", "excited"]
            },
            # UK MOVIES
            {
                "id": "26", "title": "The King's Speech", "language": "English", "region": "UK",
                "genre": ["Biography", "Drama"], "runtime": 118, "year": "2010",
                "rating": 8.1, "overview": "King George VI tries to overcome his stammer with the help of a speech therapist.",
                "poster": "/posters/the-kings-speech.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=pKcp2avt5eI",
                "cast": ["Colin Firth", "Geoffrey Rush", "Helena Bonham Carter"],
                "director": "Tom Hooper", "keywords": ["motivated", "emotional", "inspirational"]
            },
            {
                "id": "27", "title": "Slumdog Millionaire", "language": "English", "region": "UK",
                "genre": ["Drama", "Romance"], "runtime": 120, "year": "2008",
                "rating": 8.0, "overview": "A Mumbai teen reflects on his life after being accused of cheating on the Indian version of Who Wants to Be a Millionaire?",
                "poster": "/posters/slumdog-millionaire.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=AI3wWxSFT4c",
                "cast": ["Dev Patel", "Freida Pinto", "Anil Kapoor"],
                "director": "Danny Boyle", "keywords": ["motivated", "happy", "excited"]
            },
            {
                "id": "28", "title": "Love Actually", "language": "English", "region": "UK",
                "genre": ["Comedy", "Drama", "Romance"], "runtime": 135, "year": "2003",
                "rating": 7.6, "overview": "Follows the lives of eight very different couples in dealing with their love lives.",
                "poster": "/posters/love-actually.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=Sz7PvqT_9Lc",
                "cast": ["Hugh Grant", "Liam Neeson", "Colin Firth"],
                "director": "Richard Curtis", "keywords": ["happy", "romantic", "funny"]
            },
            {
                "id": "29", "title": "The Theory of Everything", "language": "English", "region": "UK",
                "genre": ["Biography", "Drama", "Romance"], "runtime": 123, "year": "2014",
                "rating": 7.7, "overview": "A look at the relationship between the famous physicist Stephen Hawking and his wife.",
                "poster": "/posters/the-theory-of-everything.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=Salz7uGp72c",
                "cast": ["Eddie Redmayne", "Felicity Jones", "Tom Prior"],
                "director": "James Marsh", "keywords": ["motivated", "emotional", "inspirational"]
            },
            {
                "id": "30", "title": "Dunkirk", "language": "English", "region": "UK",
                "genre": ["Action", "Drama", "History"], "runtime": 106, "year": "2017",
                "rating": 7.9, "overview": "Allied soldiers from Belgium, the British Empire and France are surrounded by the German Army.",
                "poster": "/posters/dunkirk.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=F-eMt3SrfFg",
                "cast": ["Fionn Whitehead", "Barry Keoghan", "Mark Rylance"],
                "director": "Christopher Nolan", "keywords": ["thrilling", "motivated", "dark"]
            },
            {
                "id": "31", "title": "1917", "language": "English", "region": "UK",
                "genre": ["Action", "Drama", "War"], "runtime": 119, "year": "2019",
                "rating": 7.9, "overview": "Two British soldiers are sent to deliver a message deep in enemy territory.",
                "poster": "/posters/1917.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=YmGG6-xv4ek",
                "cast": ["George MacKay", "Dean-Charles Chapman", "Mark Strong"],
                "director": "Sam Mendes", "keywords": ["thrilling", "motivated", "dark"]
            },
            {
                "id": "32", "title": "The Imitation Game", "language": "English", "region": "UK",
                "genre": ["Biography", "Drama", "Thriller"], "runtime": 114, "year": "2014",
                "rating": 8.0, "overview": "Alan Turing attempts to crack the enigma code with help from fellow mathematicians.",
                "poster": "/posters/the-imitation-game.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=nu5P_K2yFMY",
                "cast": ["Benedict Cumberbatch", "Keira Knightley", "Matthew Goode"],
                "director": "Morten Tyldum", "keywords": ["motivated", "thrilling", "inspirational"]
            },
            {
                "id": "33", "title": "Atonement", "language": "English", "region": "UK",
                "genre": ["Drama", "Mystery", "Romance"], "runtime": 123, "year": "2007",
                "rating": 7.9, "overview": "Thirteen-year-old fledgling writer Briony Tallis irrevocably changes the course of several lives.",
                "poster": "/posters/atonement.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=S8DwA5Oq8L0",
                "cast": ["James McAvoy", "Keira Knightley", "Saoirse Ronan"],
                "director": "Joe Wright", "keywords": ["emotional", "romantic", "dark"]
            },
            {
                "id": "34", "title": "The Grand Budapest Hotel", "language": "English", "region": "UK",
                "genre": ["Adventure", "Comedy", "Crime"], "runtime": 99, "year": "2014",
                "rating": 8.1, "overview": "A writer encounters the owner of an aging high-class hotel, who tells him of his early years.",
                "poster": "/posters/the-grand-budapest-hotel.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=1Fg5iWmQjwk",
                "cast": ["Ralph Fiennes", "F. Murray Abraham", "Mathieu Amalric"],
                "director": "Wes Anderson", "keywords": ["funny", "excited", "happy"]
            },
            {
                "id": "35", "title": "Skyfall", "language": "English", "region": "UK",
                "genre": ["Action", "Adventure", "Thriller"], "runtime": 143, "year": "2012",
                "rating": 7.8, "overview": "James Bond's loyalty to M is tested when her past comes back to haunt her.",
                "poster": "/posters/skyfall.jpg",
                "trailer_url": "https://www.youtube.com/watch?v=6kw1UVovByM",
                "cast": ["Daniel Craig", "Judi Dench", "Javier Bardem"],
                "director": "Sam Mendes", "keywords": ["excited", "thrilling", "dark"]
            },
            {
                "id": "36", "title": "Aparajito", "language": "Bengali", "region": "India",
                "genre": ["Drama"], "runtime": 110, "year": "1956",
                "rating": 8.4, "overview": "Apu and his mother move to Varanasi and then a Bengali village.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Pinaki Sengupta", "Smaran Ghosal"],
                "director": "Satyajit Ray", "keywords": ["emotional", "deep", "moving"]
            },
            {
                "id": "37", "title": "Nayak", "language": "Bengali", "region": "India",
                "genre": ["Drama"], "runtime": 120, "year": "1966",
                "rating": 8.2, "overview": "A superstar actor reveals his secrets during a train journey.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Uttam Kumar", "Sharmila Tagore"],
                "director": "Satyajit Ray", "keywords": ["moving", "classic", "deep"]
            },
            {
                "id": "54", "title": "Chokher Bali", "language": "Bengali", "region": "India",
                "genre": ["Romance", "Drama"], "runtime": 145, "year": "2003",
                "rating": 7.1, "overview": "A tale of passion, lies, and betrayal in early 20th-century Bengal.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Aishwarya Rai", "Raima Sen"],
                "director": "Rituparno Ghosh", "keywords": ["romantic", "love", "emotional", "dark"]
            },
            {
                "id": "55", "title": "Hera Pheri", "language": "Hindi", "region": "India",
                "genre": ["Comedy"], "runtime": 138, "year": "2000",
                "rating": 8.2, "overview": "Three unemployed men find an answer to their financial problems.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Akshay Kumar", "Suniel Shetty", "Paresh Rawal"],
                "director": "Priyadarshan", "keywords": ["happy", "funny", "classic"]
            },
            {
                "id": "56", "title": "Andaz Apna Apna", "language": "Hindi", "region": "India",
                "genre": ["Comedy"], "runtime": 160, "year": "1994",
                "rating": 8.1, "overview": "Two slackers compete to win the heart of a rich heiress.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Aamir Khan", "Salman Khan"],
                "director": "Rajkumar Santoshi", "keywords": ["happy", "funny", "classic"]
            },
            {
                "id": "57", "title": "Welcome", "language": "Hindi", "region": "India",
                "genre": ["Comedy"], "runtime": 146, "year": "2007",
                "rating": 7.0, "overview": "A man falls in love with a woman whose brothers are gangsters.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Akshay Kumar", "Katrina Kaif", "Nana Patekar"],
                "director": "Anees Bazmee", "keywords": ["happy", "funny"]
            },
            {
                "id": "58", "title": "Dhamaal", "language": "Hindi", "region": "India",
                "genre": ["Comedy"], "runtime": 136, "year": "2007",
                "rating": 7.5, "overview": "Four lazy friends race to find hidden treasure.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Sanjay Dutt", "Arshad Warsi", "Riteish Deshmukh"],
                "director": "Indra Kumar", "keywords": ["happy", "funny"]
            },
            {
                "id": "59", "title": "Bhool Bhulaiyaa", "language": "Hindi", "region": "India",
                "genre": ["Comedy", "Thriller"], "runtime": 159, "year": "2007",
                "rating": 7.4, "overview": "An eccentric psychiatrist investigates a supposedly haunted palace.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Akshay Kumar", "Vidya Balan", "Shiney Ahuja"],
                "director": "Priyadarshan", "keywords": ["thrilling", "funny", "mystery"]
            },
            {
                "id": "60", "title": "Garam Masala", "language": "Hindi", "region": "India",
                "genre": ["Comedy"], "runtime": 145, "year": "2005",
                "rating": 7.2, "overview": "Two photographer friends play with the hearts of three air hostesses.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Akshay Kumar", "John Abraham"],
                "director": "Priyadarshan", "keywords": ["happy", "funny"]
            },
            {
                "id": "61", "title": "Dilwale Dulhania Le Jayenge", "language": "Hindi", "region": "India",
                "genre": ["Romance", "Drama"], "runtime": 189, "year": "1995",
                "rating": 8.0, "overview": "Raj and Simran meet on a trip to Europe and fall in love.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Shah Rukh Khan", "Kajol"],
                "director": "Aditya Chopra", "keywords": ["happy", "romantic", "funny"]
            },
            {
                "id": "62", "title": "Lagaan", "language": "Hindi", "region": "India",
                "genre": ["Drama", "Sports"], "runtime": 224, "year": "2001",
                "rating": 8.1, "overview": "A group of Indian villagers challenge British officers to a game of cricket.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Aamir Khan", "Gracy Singh"],
                "director": "Ashutosh Gowariker", "keywords": ["motivated", "inspirational", "sports"]
            },
            {
                "id": "63", "title": "Taare Zameen Par", "language": "Hindi", "region": "India",
                "genre": ["Drama", "Family"], "runtime": 165, "year": "2007",
                "rating": 8.4, "overview": "An art teacher helps a dyslexic child discover his true potential.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Aamir Khan", "Darsheel Safary"],
                "director": "Aamir Khan", "keywords": ["emotional", "deep", "moving"]
            },
            {
                "id": "64", "title": "Swades", "language": "Hindi", "region": "India",
                "genre": ["Drama"], "runtime": 189, "year": "2004",
                "rating": 8.2, "overview": "A NASA scientist returns to his native village in India.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Shah Rukh Khan", "Gayatri Joshi"],
                "director": "Ashutosh Gowariker", "keywords": ["motivated", "emotional", "deep"]
            },
            {
                "id": "65", "title": "Chak De! India", "language": "Hindi", "region": "India",
                "genre": ["Drama", "Sports"], "runtime": 153, "year": "2007",
                "rating": 8.2, "overview": "A disgraced hockey player seeks redemption by coaching the women's national team.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Shah Rukh Khan", "Vidya Malvade"],
                "director": "Shimit Amin", "keywords": ["motivated", "excited", "sports"]
            },
            {
                "id": "66", "title": "Munna Bhai M.B.B.S.", "language": "Hindi", "region": "India",
                "genre": ["Comedy", "Drama"], "runtime": 156, "year": "2003",
                "rating": 8.1, "overview": "A gangster pretends to be a medical student to please his father.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Sanjay Dutt", "Arshad Warsi"],
                "director": "Rajkumar Hirani", "keywords": ["happy", "funny", "emotional"]
            },
            {
                "id": "67", "title": "Super Deluxe", "language": "Tamil", "region": "India",
                "genre": ["Thriller", "Drama"], "runtime": 176, "year": "2019",
                "rating": 8.3, "overview": "An unexpected group of people find themselves in extraordinary situations.",
                "poster": "/posters/super-deluxe.jpg",
                "trailer_url": "",
                "cast": ["Vijay Sethupathi", "Fahadh Faasil", "Samantha Ruth Prabhu"],
                "director": "Thiagarajan Kumararaja", "keywords": ["dark", "thrilling", "funny"]
            },
            {
                "id": "68", "title": "Nayagan", "language": "Tamil", "region": "India",
                "genre": ["Crime", "Drama"], "runtime": 145, "year": "1987",
                "rating": 8.6, "overview": "A common man becomes a powerful crime boss in Mumbai.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Kamal Haasan", "Saranya Ponvannan"],
                "director": "Mani Ratnam", "keywords": ["dark", "motivated", "sad"]
            },
            {
                "id": "69", "title": "Anbe Sivam", "language": "Tamil", "region": "India",
                "genre": ["Comedy", "Drama"], "runtime": 160, "year": "2003",
                "rating": 8.7, "overview": "Two men form a strong bond on a journey from Bhubaneswar to Chennai.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Kamal Haasan", "Madhavan"],
                "director": "Sundar C.", "keywords": ["happy", "funny", "emotional"]
            },
            {
                "id": "70", "title": "Eega", "language": "Telugu", "region": "India",
                "genre": ["Action", "Fantasy"], "runtime": 145, "year": "2012",
                "rating": 7.7, "overview": "A man is reincarnated as a housefly and seeks revenge on his killer.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Nani", "Samantha Ruth Prabhu", "Sudeep"],
                "director": "S.S. Rajamouli", "keywords": ["action", "thrilling", "excited"]
            },
            {
                "id": "71", "title": "Mahanati", "language": "Telugu", "region": "India",
                "genre": ["Biography", "Drama"], "runtime": 177, "year": "2018",
                "rating": 8.5, "overview": "Biography of Savitri, the legendary South Indian actress.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Keerthy Suresh", "Dulquer Salmaan"],
                "director": "Nag Ashwin", "keywords": ["emotional", "deep", "biography"]
            },
            {
                "id": "72", "title": "Kantara", "language": "Kannada", "region": "India",
                "genre": ["Action", "Drama", "Thriller"], "runtime": 150, "year": "2022",
                "rating": 8.3, "overview": "A conflict between a forest officer and a local rebel.",
                "poster": "/posters/kantara.jpg",
                "trailer_url": "",
                "cast": ["Rishab Shetty", "Sapthami Gowda"],
                "director": "Rishab Shetty", "keywords": ["excited", "thrilling", "action"]
            },
            {
                "id": "73", "title": "Sairat", "language": "Marathi", "region": "India",
                "genre": ["Romance", "Drama"], "runtime": 174, "year": "2016",
                "rating": 8.3, "overview": "Two college students fall in love across caste lines.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Rinku Rajguru", "Akash Thosar"],
                "director": "Nagraj Manjule", "keywords": ["romantic", "sad", "emotional"]
            },
            {
                "id": "74", "title": "Court", "language": "Marathi", "region": "India",
                "genre": ["Drama"], "runtime": 116, "year": "2014",
                "rating": 7.7, "overview": "A social activist is accused of inciting a sewer worker's suicide.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Vira Sathidar", "Vivek Gomber"],
                "director": "Chaitanya Tamhane", "keywords": ["deep", "classic"]
            },
            {
                "id": "75", "title": "Maula Jatt", "language": "Punjabi", "region": "Pakistan",
                "genre": ["Action", "Drama"], "runtime": 153, "year": "2022",
                "rating": 8.2, "overview": "An legendary action film representing Pakistani Punjabi cinema.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Fawad Khan", "Hamza Ali Abbasi"],
                "director": "Bilal Lashari", "keywords": ["excited", "thrilled", "motivated"]
            },
            {
                "id": "76", "title": "Carry on Jatta", "language": "Punjabi", "region": "India",
                "genre": ["Comedy"], "runtime": 141, "year": "2012",
                "rating": 7.6, "overview": "A hilarious comedy of confusion and romance.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Gippy Grewal", "Mahie Gill"],
                "director": "Smeep Kang", "keywords": ["happy", "funny"]
            },
            {
                "id": "77", "title": "The Godfather", "language": "English", "region": "International",
                "genre": ["Drama"], "runtime": 175, "year": "1972",
                "rating": 9.2, "overview": "The aging patriarch of an organized crime dynasty transfers control.",
                "poster": "/posters/the-godfather.jpg",
                "trailer_url": "",
                "cast": ["Marlon Brando", "Al Pacino"],
                "director": "Francis Ford Coppola", "keywords": ["dark", "emotional", "deep"]
            },
            {
                "id": "78", "title": "Forrest Gump", "language": "English", "region": "International",
                "genre": ["Drama", "Romance"], "runtime": 142, "year": "1994",
                "rating": 8.8, "overview": "Historical events unfold from the perspective of an Alabama man.",
                "poster": "/posters/forrest-gump.jpg",
                "trailer_url": "",
                "cast": ["Tom Hanks", "Robin Wright"],
                "director": "Robert Zemeckis", "keywords": ["happy", "emotional", "moving"]
            },
            {
                "id": "79", "title": "Pulp Fiction", "language": "English", "region": "International",
                "genre": ["Thriller", "Crime"], "runtime": 154, "year": "1994",
                "rating": 8.9, "overview": "The lives of two mob hitmen, a boxer, and a gangster.",
                "poster": "/posters/pulp-fiction.jpg",
                "trailer_url": "",
                "cast": ["John Travolta", "Uma Thurman", "Samuel L. Jackson"],
                "director": "Quentin Tarantino", "keywords": ["dark", "thrilled", "excited"]
            },
            {
                "id": "80", "title": "Goodfellas", "language": "English", "region": "International",
                "genre": ["Drama"], "runtime": 146, "year": "1990",
                "rating": 8.7, "overview": "The story of Henry Hill and his life in the mob.",
                "poster": "/posters/goodfellas.jpg",
                "trailer_url": "",
                "cast": ["Robert De Niro", "Ray Liotta", "Joe Pesci"],
                "director": "Martin Scorsese", "keywords": ["dark", "thrilled", "excited"]
            },
            {
                "id": "81", "title": "The Lion King", "language": "English", "region": "International",
                "genre": ["Animation", "Adventure", "Drama"], "runtime": 88, "year": "1994",
                "rating": 8.5, "overview": "A young lion cub Simba searches for his destiny.",
                "poster": "/posters/the-lion-king.jpg",
                "trailer_url": "",
                "cast": ["Matthew Broderick", "Jeremy Irons"],
                "director": "Roger Allers", "keywords": ["happy", "sad", "motivated"]
            },
            {
                "id": "82", "title": "Avengers Endgame", "language": "English", "region": "International",
                "genre": ["Action", "Adventure"], "runtime": 181, "year": "2019",
                "rating": 8.4, "overview": "The Avengers assemble once more to reverse Thanos' actions.",
                "poster": "/posters/avengers-endgame.jpg",
                "trailer_url": "",
                "cast": ["Robert Downey Jr.", "Chris Evans", "Mark Ruffalo"],
                "director": "Anthony Russo", "keywords": ["excited", "thrilling", "happy"]
            },
            {
                "id": "83", "title": "Titanic", "language": "English", "region": "International",
                "genre": ["Romance", "Drama"], "runtime": 194, "year": "1997",
                "rating": 7.9, "overview": "Two members of different social classes fall in love on the ship.",
                "poster": "/posters/titanic.jpg",
                "trailer_url": "",
                "cast": ["Leonardo DiCaprio", "Kate Winslet"],
                "director": "James Cameron", "keywords": ["romantic", "emotional", "sad"]
            },
            {
                "id": "84", "title": "The Matrix", "language": "English", "region": "International",
                "genre": ["Action", "Sci-Fi"], "runtime": 136, "year": "1999",
                "rating": 8.7, "overview": "A computer hacker learns about the true nature of his reality.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Keanu Reeves", "Laurence Fishburne"],
                "director": "Lana Wachowski", "keywords": ["excited", "motivated", "thrilling"]
            },
            {
                "id": "85", "title": "Gladiator", "language": "English", "region": "International",
                "genre": ["Action", "Drama"], "runtime": 155, "year": "2000",
                "rating": 8.5, "overview": "A former Roman General sets out to exact vengeance against the corrupt emperor.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Russell Crowe", "Joaquin Phoenix"],
                "director": "Ridley Scott", "keywords": ["excited", "motivated", "thrilling"]
            },
            {
                "id": "86", "title": "Roma", "language": "Spanish", "region": "International",
                "genre": ["Drama"], "runtime": 135, "year": "2018",
                "rating": 7.7, "overview": "A year in the life of a middle-class family's maid in Mexico City.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Yalitza Aparicio", "Marina de Tavira"],
                "director": "Alfonso Cuarón", "keywords": ["sad", "emotional", "deep"]
            },
            {
                "id": "87", "title": "The Lord of the Rings: The Fellowship of the Ring", "language": "English", "region": "International",
                "genre": ["Adventure", "Fantasy", "Action"], "runtime": 178, "year": "2001",
                "rating": 8.9, "overview": "An ancient Ring thought lost for centuries has been found.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Elijah Wood", "Ian McKellen"],
                "director": "Peter Jackson", "keywords": ["excited", "motivated", "thrilling"]
            },
            {
                "id": "88", "title": "The Dark Knight Rises", "language": "English", "region": "International",
                "genre": ["Action", "Thriller"], "runtime": 165, "year": "2012",
                "rating": 8.4, "overview": "Batman returns to save Gotham City.",
                "poster": "/posters/default-poster.jpg",
                "trailer_url": "",
                "cast": ["Christian Bale", "Gary Oldman"],
                "director": "Christopher Nolan", "keywords": ["excited", "thrilling", "dark"]
            }
        ]
        
        conn = get_db_connection()
        c = conn.cursor()
        for movie in fallback_movies:
            try:
                if movie["region"] == "India":
                    country = "India"
                    origin_country = "IN"
                elif movie["region"] == "Pakistan":
                    country = "Pakistan"
                    origin_country = "PK"
                else:
                    country = "United States of America"
                    origin_country = "US"
                c.execute(
                    """INSERT OR REPLACE INTO movies (
                        id, title, language, region, country, origin_country, genre, runtime, year, rating, 
                        overview, poster, trailer_url, cast, director, keywords, 
                        average_review_score, review_count
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        movie["id"], movie["title"], movie["language"], movie["region"],
                        country, origin_country,
                        json.dumps(movie["genre"]), movie["runtime"], movie["year"], movie["rating"],
                        movie["overview"], movie["poster"], movie["trailer_url"],
                        json.dumps(movie["cast"]), movie["director"], json.dumps(movie["keywords"]),
                        None, 0
                    )
                )
            except Exception as e:
                logger.error(f"Error inserting fallback movie {movie['title']}: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"Populated database with {len(fallback_movies)} fallback movies")

    def fetch_movies_from_tmdb(self, genre_name, lang_name, page=1):
        """Fetch popular movies from TMDB matching genre and language with pagination support"""
        if not getattr(self, "tmdb_enabled", True):
            return []
            
        api_key = os.getenv("TMDB_API_KEY")
        if not api_key:
            logger.error("TMDB API key not configured")
            self.tmdb_enabled = False
            return []
            
        genre_id = TMDB_GENRES.get(genre_name)
        lang_code = LANG_MAP.get(lang_name)
        
        url = "https://api.tmdb.org/3/discover/movie"
        params = {
            "api_key": api_key,
            "sort_by": "popularity.desc",
            "page": page,
            "vote_count.gte": 10,
            "vote_average.gte": 4.0
        }
        if genre_id:
            params["with_genres"] = genre_id
        if lang_code:
            params["with_original_language"] = lang_code
            
        try:
            logger.debug(f"API request sent: TMDB discover URL={url}")
            response = requests.get(url, params=params, timeout=8)
            logger.debug(f"API response received: status={response.status_code}")
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                logger.info(f"TMDB Fetch Success: returned {len(results)} movies (page {page})")
                return results
            elif response.status_code == 401:
                logger.warning("TMDB API key is invalid (status 401). Disabling TMDB integration.")
                self.tmdb_enabled = False
                return []
            else:
                logger.debug(f"TMDB Fetch Failed: Status {response.status_code} - {response.text}")
        except requests.exceptions.Timeout:
            logger.error("TMDB Fetch Timeout")
        except requests.exceptions.RequestException as e:
            logger.error(f"TMDB Fetch Exception: {e}")
        except Exception as e:
            logger.error(f"Unexpected TMDB Fetch Exception: {e}")
        return []

    def fetch_trending_movies(self, time_window="day"):
        """Fetch trending movies from TMDB (day or week)"""
        if not getattr(self, "tmdb_enabled", True):
            return []
            
        api_key = os.getenv("TMDB_API_KEY")
        if not api_key:
            logger.error("TMDB API key not configured")
            self.tmdb_enabled = False
            return []
            
        url = f"https://api.tmdb.org/3/trending/movie/{time_window}"
        params = {
            "api_key": api_key,
            "page": 1
        }
        
        try:
            logger.debug(f"API request sent: TMDB trending URL={url}")
            response = requests.get(url, params=params, timeout=8)
            logger.debug(f"API response received: status={response.status_code}")
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                logger.info(f"TMDB Trending Fetch Success: returned {len(results)} movies ({time_window})")
                return results
            elif response.status_code == 401:
                logger.warning("TMDB API key is invalid (status 401). Disabling TMDB trending requests.")
                self.tmdb_enabled = False
                return []
            else:
                logger.debug(f"TMDB Trending Fetch Failed: Status {response.status_code}")
        except requests.exceptions.Timeout:
            logger.error("TMDB Trending Fetch Timeout")
        except requests.exceptions.RequestException as e:
            logger.error(f"TMDB Trending Fetch Exception: {e}")
        except Exception as e:
            logger.error(f"Unexpected TMDB Trending Fetch Exception: {e}")
        return []

    def fetch_tmdb_movie_details(self, tmdb_id):
        """Get detailed credits, videos, and keywords for a TMDB movie"""
        if not getattr(self, "tmdb_enabled", True):
            return None
            
        api_key = os.getenv("TMDB_API_KEY")
        if not api_key:
            self.tmdb_enabled = False
            return None
        url = f"https://api.tmdb.org/3/movie/{tmdb_id}"
        params = {
            "api_key": api_key,
            "append_to_response": "videos,credits,keywords"
        }
        try:
            logger.debug(f"API request sent: TMDB details URL={url}")
            response = requests.get(url, params=params, timeout=4)
            logger.debug(f"API response received: status={response.status_code}")
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                logger.warning("TMDB API key is invalid (status 401) during details fetch. Disabling TMDB.")
                self.tmdb_enabled = False
        except Exception as e:
            logger.debug(f"Exception fetching TMDB details for ID {tmdb_id}: {e}")
        return None

    def enrich_movie_with_omdb(self, title, year=""):
        """Enrich movie using OMDb API with database caching support"""
        if not getattr(self, "omdb_enabled", True):
            return None
            
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT data FROM movie_omdb_cache WHERE LOWER(title) = LOWER(?)", (title,))
        row = c.fetchone()
        if row:
            conn.close()
            return json.loads(row[0])
            
        omdb_key = os.getenv("OMDB_API_KEY")
        if not omdb_key:
            self.omdb_enabled = False
            conn.close()
            return None
            
        url = "http://www.omdbapi.com/"
        params = {"apikey": omdb_key, "t": title}
        if year:
            params["y"] = year
            
        try:
            logger.debug(f"API request sent: OMDb URL={url} title={title}")
            response = requests.get(url, params=params, timeout=4)
            logger.debug(f"API response received: status={response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if data.get("Response") == "True":
                    c.execute("INSERT OR REPLACE INTO movie_omdb_cache (title, data) VALUES (?, ?)", (title, json.dumps(data)))
                    conn.commit()
                    conn.close()
                    logger.debug("OMDb Enrichment Success")
                    return data
                elif "Invalid API key" in data.get("Error", ""):
                    logger.warning("OMDb API key is invalid. Disabling OMDb integration.")
                    self.omdb_enabled = False
            elif response.status_code == 401:
                logger.warning("OMDb API key is unauthorized (401). Disabling OMDb integration.")
                self.omdb_enabled = False
        except Exception as e:
            logger.debug(f"Exception in OMDb enrichment for '{title}': {e}")
        conn.close()
        return None

    def cache_movie_to_db(self, movie_details, omdb_details=None, language_pref=None, region_pref=None):
        """Save TMDB/OMDB data locally in database cache following the unified schema"""
        conn = get_db_connection()
        c = conn.cursor()
        try:
            tmdb_id = str(movie_details.get("id"))
            title = movie_details.get("title")
            
            orig_lang = movie_details.get("original_language")
            lang_name = next((k for k, v in LANG_MAP.items() if v == orig_lang), "English")
            if language_pref and orig_lang == LANG_MAP.get(language_pref):
                lang_name = language_pref
                
            # Verify language tags: Never mark Hollywood movies as Hindi
            production_countries = movie_details.get("production_countries", [])
            is_us_uk = any(country.get("iso_3166_1") in ["US", "GB"] for country in production_countries) if isinstance(production_countries, list) else False
            if orig_lang == "en" or is_us_uk:
                if lang_name == "Hindi":
                    logger.debug(f"Hollywood movie '{title}' cannot be marked as Hindi. Setting to English.")
                    lang_name = "English"

            region = region_pref or "International"
            genres = [g.get("name") for g in movie_details.get("genres", [])]
            runtime = movie_details.get("runtime") or 120
            
            release_date = movie_details.get("release_date", "")
            year = release_date[:4] if release_date else ""
            
            rating = movie_details.get("vote_average", 0.0)
            if omdb_details and omdb_details.get("imdbRating") not in [None, "N/A"]:
                try:
                    rating = float(omdb_details.get("imdbRating"))
                except:
                    pass
                    
            overview = movie_details.get("overview", "")
            poster_path = movie_details.get("poster_path")
            poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
            if not poster and omdb_details:
                poster = omdb_details.get("Poster", "")
                
            # Trailer URL
            trailer_url = ""
            videos = movie_details.get("videos", {}).get("results", [])
            for v in videos:
                if v.get("site") == "YouTube" and v.get("type") == "Trailer":
                    trailer_url = f"https://www.youtube.com/watch?v={v.get('key')}"
                    if v.get("official"):
                        break
            if not trailer_url:
                trailer_url = f"https://www.youtube.com/results?search_query={title.replace(' ', '+')}+trailer"
                
            # Cast & Director
            cast = []
            director = ""
            credits = movie_details.get("credits", {})
            for actor in credits.get("cast", [])[:5]:
                cast.append(actor.get("name"))
            for crew_member in credits.get("crew", []):
                if crew_member.get("job") == "Director":
                    director = crew_member.get("name")
                    break
                    
            if not director and omdb_details:
                director = omdb_details.get("Director", "")
            if not cast and omdb_details:
                cast = [a.strip() for a in omdb_details.get("Actors", "").split(",") if a.strip()]
                
            # Keywords
            keywords = []
            tmdb_keywords = movie_details.get("keywords", {}).get("keywords", [])
            if not tmdb_keywords:
                tmdb_keywords = movie_details.get("keywords", {}).get("results", [])
            for kw in tmdb_keywords[:10]:
                keywords.append(kw.get("name"))
                
            # Country mapping
            countries_list = []
            if isinstance(production_countries, list):
                for c_item in production_countries:
                    c_name = c_item.get("name")
                    if c_name:
                        countries_list.append(c_name)
            if omdb_details and omdb_details.get("Country"):
                omdb_countries = [c_strip.strip() for c_strip in omdb_details.get("Country").split(",")]
                for c_name in omdb_countries:
                    if c_name not in countries_list:
                        countries_list.append(c_name)
            country = ", ".join(countries_list)

            # Origin country mapping
            origin_country_list = movie_details.get("origin_country") or []
            origin_countries_list = []
            if isinstance(origin_country_list, list):
                origin_countries_list.extend(origin_country_list)
            for c_item in production_countries:
                code = c_item.get("iso_3166_1")
                if code and code not in origin_countries_list:
                    origin_countries_list.append(code)
            origin_country = ", ".join(origin_countries_list)

            c.execute(
                """INSERT OR REPLACE INTO movies (
                    id, title, language, region, country, origin_country, genre, runtime, year, rating, 
                    overview, poster, trailer_url, cast, director, keywords, 
                    average_review_score, review_count
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tmdb_id, title, lang_name, region, country, origin_country, json.dumps(genres), runtime, year, rating,
                    overview, poster, trailer_url, json.dumps(cast), director, json.dumps(keywords),
                    None, 0
                )
            )
            conn.commit()
            conn.close()
            return tmdb_id
        except Exception as e:
            logger.error(f"Error caching movie to DB: {e}")
            if 'conn' in locals():
                conn.close()
        return None

    def recommend(self, mood, genre, language, region, min_rating=0.0, max_runtime=240, n=20, user_id=None):
        """Generate recommendation scores based on weighted formula with relaxation logic"""
        n = max(n, 15)  # Enforce minimum recommendation count constraint of 15
        logger.debug(f"Recommendation request started: mood={mood}, genre={genre}, language={language}, region={region}, min_rating={min_rating}, max_runtime={max_runtime}, user_id={user_id}")
        
        # Helper function for normalizing region
        def get_normalized_region(region_str):
            if not region_str:
                return None
            r = region_str.strip().lower()
            if r in ["usa", "united states", "us", "international"]:
                return "USA"
            if r in ["uk", "united kingdom"]:
                return "UK"
            if r in ["india"]:
                return "India"
            if r in ["korea", "south korea"]:
                return "Korea"
            if r in ["japan"]:
                return "Japan"
            if r in ["bangladesh"]:
                return "Bangladesh"
            if r in ["pakistan"]:
                return "Pakistan"
            return region_str.title()

        from backend.region import REGION_LANGUAGES
        
        # 1. Dynamically fetch matching movies from TMDB on the fly
        target_languages = []
        if language and language.strip() and language.lower() != "all languages":
            target_languages = [language]
        else:
            norm_region = get_normalized_region(region)
            target_languages = REGION_LANGUAGES.get(norm_region, ["English"])

        tmdb_results = []
        for lang in target_languages:
            # Fetch with genre
            results = self.fetch_movies_from_tmdb(genre, lang)
            if results:
                tmdb_results.extend(results)
            # If we need more movies, fetch popular ones without genre constraint to populate cache
            if not results or len(results) < 10:
                popular_results = self.fetch_movies_from_tmdb(None, lang)
                if popular_results:
                    tmdb_results.extend(popular_results)
                    
        # Filter duplicates from tmdb_results
        seen_ids = set()
        unique_tmdb_results = []
        for r in tmdb_results:
            rid = r.get("id")
            if rid and rid not in seen_ids:
                seen_ids.add(rid)
                unique_tmdb_results.append(r)
        tmdb_results = unique_tmdb_results

        # Process and cache each TMDB result
        if tmdb_results:
            for movie in tmdb_results:
                tmdb_id = movie.get("id")
                # Get full details if not already stored
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("SELECT id FROM movies WHERE id = ?", (str(tmdb_id),))
                exists = c.fetchone()
                conn.close()
                
                if not exists:
                    movie_details = self.fetch_tmdb_movie_details(tmdb_id)
                    if movie_details:
                        title = movie_details.get("title")
                        omdb_details = self.enrich_movie_with_omdb(title, movie_details.get("release_date", "")[:4])
                        self.cache_movie_to_db(movie_details, omdb_details, language_pref=language, region_pref=region)
        else:
            logger.debug("TMDB fetch failed, falling back to local database only")

        logger.debug(f"Movies fetched: {len(tmdb_results) if tmdb_results else 0}")

        # 2. Query all local cached movies from SQLite
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM movies")
        movies = [dict(row) for row in c.fetchall()]
        
        # If database is empty, populate with fallback dataset
        if not movies:
            logger.debug("Database empty, populating with fallback dataset")
            self.populate_fallback_dataset()
            c.execute("SELECT * FROM movies")
            movies = [dict(row) for row in c.fetchall()]
        conn.close()
        
        # Prepare the dataset
        dataset = []
        for m in movies:
            try:
                g_val = m.get("genre")
                if g_val:
                    try:
                        movie_genres = json.loads(g_val)
                        if not isinstance(movie_genres, list):
                            movie_genres = [movie_genres]
                    except Exception:
                        movie_genres = [g_val]
                else:
                    movie_genres = []
                
                k_val = m.get("keywords")
                if k_val:
                    try:
                        movie_keywords = json.loads(k_val)
                        if not isinstance(movie_keywords, list):
                            movie_keywords = [movie_keywords]
                    except Exception:
                        movie_keywords = k_val.split()
                else:
                    movie_keywords = []

                movie_obj = {
                    "id": str(m.get("id", "")),
                    "title": m.get("title", ""),
                    "language": m.get("language", ""),
                    "region": m.get("region", ""),
                    "country": m.get("country") or "",
                    "origin_country": m.get("origin_country") or "",
                    "genres": movie_genres,
                    "rating": float(m.get("rating")) if m.get("rating") is not None else 0.0,
                    "runtime": int(m.get("runtime")) if m.get("runtime") is not None else 120,
                    "overview": m.get("overview") or "",
                    "poster": m.get("poster") or "",
                    "trailer_url": m.get("trailer_url") or "",
                    "cast": m.get("cast") or "[]",
                    "director": m.get("director") or "",
                    "keywords": movie_keywords,
                    "year": m.get("year") or "",
                    "average_review_score": m.get("average_review_score"),
                    "review_count": m.get("review_count") or 0
                }
                dataset.append(movie_obj)
            except Exception as e:
                logger.debug(f"Error mapping movie {m.get('title')}: {e}")

        # Strict Region filter (Mandatory)
        movies_after_region = []
        for m in dataset:
            if is_region_match(m, region):
                movies_after_region.append(m)

        # Strict Language filter (Mandatory)
        movies_after_language = []
        norm_region = get_normalized_region(region)
        allowed_langs = REGION_LANGUAGES.get(norm_region, []) if norm_region else []
        allowed_langs_lower = [al.lower() for al in allowed_langs]
        if language and language.strip() and language.lower() != "all languages":
            for m in movies_after_region:
                if m.get("language") and m["language"].lower() == language.lower():
                    movies_after_language.append(m)
        elif allowed_langs_lower:
            for m in movies_after_region:
                if (m.get("language") or "").lower() in allowed_langs_lower:
                    movies_after_language.append(m)
        else:
            movies_after_language = list(movies_after_region)
            
        # Genre filter (Soft preference)
        genre_filtered = []
        if genre and genre.strip():
            genre_filtered = [m for m in movies_after_language if any(genre.lower() == g.lower() for g in m["genres"])]
        else:
            genre_filtered = list(movies_after_language)
            
        # Mood filter (Soft preference)
        mood_filtered = []
        if mood and mood.strip():
            mood_filtered = [m for m in genre_filtered if is_mood_match(m, mood)]
        else:
            mood_filtered = list(genre_filtered)
            
        # Rating filter (Soft preference)
        rating_filtered = []
        if min_rating:
            rating_filtered = [m for m in mood_filtered if m["rating"] >= min_rating]
        else:
            rating_filtered = list(mood_filtered)
            
        # Runtime filter (Soft preference)
        runtime_filtered = []
        if max_runtime:
            runtime_filtered = [m for m in rating_filtered if m["runtime"] <= max_runtime]
        else:
            runtime_filtered = list(rating_filtered)

        # Log initial pipeline counts
        logger.debug(f"Pipeline - Movies Loaded: {len(dataset)}")
        logger.debug(f"Pipeline - After Region Filter: {len(movies_after_region)}")
        logger.debug(f"Pipeline - After Language Filter: {len(movies_after_language)}")
        logger.debug(f"Pipeline - After Genre Filter: {len(genre_filtered)}")
        logger.debug(f"Pipeline - After Mood Filter: {len(mood_filtered)}")
        logger.debug(f"Pipeline - After Runtime Filter: {len(runtime_filtered)}")
        logger.debug(f"Pipeline - After Rating Filter: {len(rating_filtered)}")

        # Identify which filter removes most movies
        drops = {
            "Region Filter": len(dataset) - len(movies_after_region),
            "Language Filter": len(movies_after_region) - len(movies_after_language),
            "Genre Filter": len(movies_after_language) - len(genre_filtered),
            "Mood Filter": len(genre_filtered) - len(mood_filtered),
            "Rating Filter": len(mood_filtered) - len(rating_filtered),
            "Runtime Filter": len(rating_filtered) - len(runtime_filtered)
        }
        most_restrictive_filter = max(drops, key=drops.get)
        most_restrictive_drop = drops[most_restrictive_filter]
        logger.debug(f"Pipeline - Most restrictive filter: {most_restrictive_filter} (removed {most_restrictive_drop} movies)")

        # Relaxation Loop (Never relax Region and Language)
        applied_filters = {"genre": True, "mood": True, "rating": True, "runtime": True}
        filtered = list(runtime_filtered)
        warning_message = None
        
        # Step 1: Relax Runtime
        if len(filtered) < 15:
            applied_filters["runtime"] = False
            filtered = [
                m for m in movies_after_language
                if (not applied_filters["genre"] or not genre or any(genre.lower() == g.lower() for g in m["genres"]))
                and (not applied_filters["mood"] or not mood or is_mood_match(m, mood))
                and (not applied_filters["rating"] or not min_rating or m["rating"] >= min_rating)
            ]
            logger.debug(f"Relaxed Runtime filter. Movies found: {len(filtered)}")
            
        # Step 2: Relax Mood
        if len(filtered) < 15:
            applied_filters["mood"] = False
            filtered = [
                m for m in movies_after_language
                if (not applied_filters["genre"] or not genre or any(genre.lower() == g.lower() for g in m["genres"]))
                and (not applied_filters["rating"] or not min_rating or m["rating"] >= min_rating)
            ]
            logger.debug(f"Relaxed Mood filter. Movies found: {len(filtered)}")
            
        # Step 3: Relax Rating
        if len(filtered) < 15:
            applied_filters["rating"] = False
            filtered = [
                m for m in movies_after_language
                if (not applied_filters["genre"] or not genre or any(genre.lower() == g.lower() for g in m["genres"]))
            ]
            logger.debug(f"Relaxed Rating filter. Movies found: {len(filtered)}")
            
        # Step 4: Relax Genre
        if len(filtered) < 15:
            applied_filters["genre"] = False
            filtered = list(movies_after_language)
            logger.debug(f"Relaxed Genre filter. Movies found: {len(filtered)}")
        
        # Step 5: Fallback to extended dataset if still not enough movies
        if len(filtered) < 15:
            logger.info(f"Main dataset exhausted ({len(filtered)} movies). Supplementing with extended dataset...")
            extended_movies = self._get_extended_dataset_fallback(genre, mood, min_rating, max_runtime, n - len(filtered))
            if extended_movies:
                filtered.extend(extended_movies)
                logger.info(f"Added {len(extended_movies)} movies from extended dataset. Total: {len(filtered)}")
        
        # Remove duplicate recommendations by unique movie ID
        seen_ids = set()
        unique_filtered = []
        for m in filtered:
            mid = m.get("id")
            if mid and mid not in seen_ids:
                seen_ids.add(mid)
                unique_filtered.append(m)
        filtered = unique_filtered

        warning_message = None
        if len(filtered) == 0:
            warning_message = "No movies found for these filters."

        # Build User taste profile if user_id is provided
        fav_genres = []
        fav_langs = []
        if user_id:
            try:
                conn = get_db_connection()
                c = conn.cursor()
                
                # Clicks
                c.execute("""
                    SELECT m.genre, m.language 
                    FROM user_clicks c 
                    JOIN movies m ON c.movie_id = m.id 
                    WHERE c.user_id = ?
                """, (user_id,))
                clicks = c.fetchall()
                
                # Searches
                c.execute("SELECT genre, language FROM user_searches WHERE user_id = ?", (user_id,))
                searches = c.fetchall()
                
                # History
                c.execute("""
                    SELECT m.genre, m.language, h.rating_given 
                    FROM user_history h 
                    JOIN movies m ON h.movie_id = m.id 
                    WHERE h.user_id = ?
                """, (user_id,))
                history = c.fetchall()
                
                # Reviews
                c.execute("""
                    SELECT m.genre, r.rating 
                    FROM reviews r 
                    JOIN movies m ON r.movie_id = m.id OR LOWER(r.movie_title) = LOWER(m.title) 
                    WHERE r.user_id = ?
                """, (user_id,))
                reviews = c.fetchall()
                conn.close()
                
                genre_scores = {}
                lang_scores = {}
                
                for r in history:
                    g_list = json.loads(r[0]) if isinstance(r[0], str) and r[0].startswith('[') else ([r[0]] if r[0] else [])
                    mult = (r[2] / 3.0) if r[2] else 1.0
                    for g in g_list:
                        genre_scores[g] = genre_scores.get(g, 0.0) + 3.0 * mult
                    if r[1]:
                        lang_scores[r[1]] = lang_scores.get(r[1], 0.0) + 3.0 * mult
                        
                for r in reviews:
                    g_list = json.loads(r[0]) if isinstance(r[0], str) and r[0].startswith('[') else ([r[0]] if r[0] else [])
                    mult = (r[1] / 5.0) if r[1] else 1.0
                    for g in g_list:
                        genre_scores[g] = genre_scores.get(g, 0.0) + 4.0 * mult
                        
                for r in searches:
                    if r[0]:
                        genre_scores[r[0]] = genre_scores.get(r[0], 0.0) + 1.0
                    if r[1]:
                        lang_scores[r[1]] = lang_scores.get(r[1], 0.0) + 1.0
                        
                for r in clicks:
                    g_list = json.loads(r[0]) if isinstance(r[0], str) and r[0].startswith('[') else ([r[0]] if r[0] else [])
                    for g in g_list:
                        genre_scores[g] = genre_scores.get(g, 0.0) + 1.0
                    if r[1]:
                        lang_scores[r[1]] = lang_scores.get(r[1], 0.0) + 1.0
                        
                fav_genres = [g for g, _ in sorted(genre_scores.items(), key=lambda x: x[1], reverse=True)[:3]]
                fav_langs = [l for l, _ in sorted(lang_scores.items(), key=lambda x: x[1], reverse=True)[:2]]
                
                logger.debug(f"Taste Profile Compiled - Favorite Genres: {fav_genres}, Languages: {fav_langs}")
            except Exception as taste_err:
                logger.debug(f"Error compiling taste profile in recommender: {taste_err}")

        # Calculate final recommendations score ranking
        scored_movies = []
        conn = get_db_connection()
        c = conn.cursor()
        for m in filtered:
            try:
                movie_genres = m["genres"]
                movie_keywords = m["keywords"]
                movie_lang = m["language"]
                runtime = m["runtime"]
                rating = m["rating"]

                c.execute("SELECT AVG(rating), COUNT(*) FROM reviews WHERE movie_id = ? OR LOWER(movie_title) = LOWER(?)", (m["id"], m["title"]))
                rev_row = c.fetchone()
                avg_rev = rev_row[0] if rev_row and rev_row[0] is not None else None
                rev_count = rev_row[1] if rev_row else 0

                # 1. Genre similarity (40%)
                genre_score = 0.0
                if genre:
                    if any(genre.lower() == mg.lower() for mg in movie_genres):
                        genre_score = 1.0
                    else:
                        genre_score = 0.2
                else:
                    genre_score = 1.0

                # 2. Mood match (20%)
                mood_score = 0.0
                if mood:
                    if is_mood_match(m, mood):
                        mood_score = 1.0
                    else:
                        mood_score = 0.1
                else:
                    mood_score = 1.0

                # 3. Rating preference (15%)
                rating_score = 1.0
                if min_rating and min_rating > 0:
                    if rating >= min_rating:
                        rating_score = 1.0
                    else:
                        rating_score = max(0.0, 1.0 - (min_rating - rating) / 2.0)
                else:
                    rating_score = rating / 10.0

                # 4. Popularity (10%)
                popularity_score = min(rev_count / 5.0, 1.0) * 0.3 + (rating / 10.0) * 0.7

                # 5. Runtime Preference (10%)
                runtime_score = 1.0
                if max_runtime and max_runtime < 240:
                    if runtime <= max_runtime:
                        runtime_score = 1.0
                    else:
                        runtime_score = max(0.0, 1.0 - (runtime - max_runtime) / 60.0)
                else:
                    runtime_score = 1.0 - abs(120 - runtime) / 180.0
                    runtime_score = max(0.2, min(1.0, runtime_score))

                # 6. Review score (5%)
                if avg_rev is not None:
                    review_score = avg_rev / 10.0
                else:
                    review_score = rating / 10.0

                final_score = (
                    0.40 * genre_score +
                    0.20 * mood_score +
                    0.15 * rating_score +
                    0.10 * popularity_score +
                    0.10 * runtime_score +
                    0.05 * review_score
                )

                # Personalization taste profile boost
                if fav_genres:
                    for i, fg in enumerate(fav_genres):
                        if any(fg.lower() == mg.lower() for mg in movie_genres):
                            boost = 0.10 - i * 0.03
                            final_score += boost
                            break
                if fav_langs:
                    if any(fl.lower() == movie_lang.lower() for fl in fav_langs):
                        final_score += 0.05

                m["ml_score"] = min(1.0, final_score)
                m["average_review_score"] = round(avg_rev, 1) if avg_rev is not None else None
                m["review_count"] = rev_count

                # Restore original serializable fields back for app.py
                m["genre"] = json.dumps(m["genres"])
                m["keywords"] = json.dumps(m["keywords"])

                scored_movies.append(m)
            except Exception as e:
                logger.debug(f"Error scoring movie {m.get('title')}: {e}")

        conn.close()

        # Sort recommendations in DESCENDING order of recommendation score
        scored_movies.sort(key=lambda x: x["ml_score"], reverse=True)
        final_recs = scored_movies[:n]

        logger.debug(f"Final Recommendations: {[m['title'] for m in final_recs]}")
        logger.debug(f"Pipeline - Final Count: {len(final_recs)}")
        logger.debug("Recommendation Request Completed")
        
        # Recommender Debug Logs
        logger.debug(f"Recommender - Region: {region}")
        logger.debug(f"Recommender - Language: {language}")
        logger.debug(f"Recommender - Movies Found: {len(final_recs)}")
        logger.debug(f"Recommender - Movies Filtered: {len(dataset) - len(final_recs)}")

        # Define aliases for diagnostics report
        apply_genre = applied_filters["genre"]
        apply_mood = applied_filters["mood"]
        apply_rating = applied_filters["rating"]
        apply_runtime = applied_filters["runtime"]
        movies_after_genre = genre_filtered
        movies_after_mood = mood_filtered
        movies_after_rating = rating_filtered
        movies_after_runtime = runtime_filtered

        # Generate recommendation diagnostics report
        movies_filtered_report = []
        for m in dataset:
            if not is_region_match(m, region):
                reason = f"Region mismatch (Selected: {region}, Movie Region: {m.get('region')})"
            elif language and m["language"].lower() != language.lower():
                reason = f"Language mismatch (Selected: {language}, Movie Language: {m['language']})"
            elif apply_genre and genre and not any(genre.lower() == g.lower() for g in m["genres"]):
                reason = f"Genre mismatch (Selected: {genre}, Movie Genres: {m['genres']})"
            elif apply_mood and mood and not is_mood_match(m, mood):
                reason = f"Mood mismatch (Selected: {mood})"
            elif apply_rating and min_rating and m["rating"] < max(0.0, min_rating - 1.5):
                reason = f"Rating below threshold (Min Rating requested: {min_rating}, Movie Rating: {m['rating']})"
            elif apply_runtime and max_runtime and m["runtime"] > max_runtime:
                reason = f"Runtime exceeds limit (Max Runtime: {max_runtime}, Movie Runtime: {m['runtime']})"
            else:
                reason = "Not filtered (candidate)"

            if reason != "Not filtered (candidate)":
                movies_filtered_report.append({
                    "title": m["title"],
                    "reason": reason
                })

        report_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "inputs": {
                "mood": mood,
                "genre": genre,
                "language": language,
                "region": region,
                "min_rating": min_rating,
                "max_runtime": max_runtime
            },
            "pipeline_trace": {
                "total_movies_loaded": len(dataset),
                "after_region_filter": len(movies_after_region),
                "after_language_filter": len(movies_after_language),
                "after_genre_filter": len(movies_after_genre),
                "after_mood_filter": len(movies_after_mood),
                "after_rating_filter": len(movies_after_rating),
                "after_runtime_filter": len(movies_after_runtime),
                "final_recommendation_count": len(final_recs)
            },
            "most_restrictive_filter": f"{most_restrictive_filter} (removed {most_restrictive_drop} movies)",
            "movies_loaded": [m["title"] for m in dataset],
            "movies_filtered": movies_filtered_report,
            "recommendations": [m["title"] for m in final_recs]
        }

        try:
            report_path = os.path.join(BASE_DIR, "recommendation_report.json")
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)
            logger.debug(f"Diagnostics report generated successfully at {report_path}")
        except Exception as e:
            logger.error(f"Failed to generate diagnostics report: {e}")

        return final_recs, warning_message
