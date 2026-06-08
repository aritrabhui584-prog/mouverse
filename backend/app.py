import os
import sys
import sqlite3
import json
import random
import re
import pandas as pd
import requests
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, login_required, current_user
from flask_mail import Mail
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# Add parent directory to path for ml_model import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.recommender import MovieRecommender, is_region_match

load_dotenv()

# Define BASE_DIR
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "mouverse.db")
CSV_PATH = os.path.join(BASE_DIR, "database", "movies.csv")
ENRICHED_CSV_PATH = os.path.join(BASE_DIR, "database", "movies_enriched.csv")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, 'app.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

recommender = MovieRecommender()

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static"
)

# Secret key configuration
secret_key = os.getenv("SECRET_KEY")
if not secret_key:
    logger.warning("SECRET_KEY not set, using a temporary key for development. Set SECRET_KEY in production!")
    secret_key = os.urandom(32).hex()
app.config["SECRET_KEY"] = secret_key

# Session management configuration (filesystem)
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(BASE_DIR, "flask_session")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
is_dev_env = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1") or \
             os.getenv("FLASK_ENV", "").lower() == "development" or \
             os.getenv("DEBUG", "false").lower() in ("true", "1") or \
             os.getenv("DEV_MODE", "false").lower() == "true"
app.config["SESSION_COOKIE_SECURE"] = not is_dev_env
app.config["REMEMBER_COOKIE_HTTPONLY"] = True
app.config["REMEMBER_COOKIE_SECURE"] = app.config["SESSION_COOKIE_SECURE"]
app.config["SESSION_PERMANENT"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)
app.config["SESSION_USE_SIGNER"] = True
Session(app)

# Flask-Mail configuration
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "True") == "True"
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER")
mail = Mail(app)

# Security headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# CORS configuration (if needed for API endpoints)
from flask_cors import CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# CSRF Protection
csrf = CSRFProtect(app)

# Rate Limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# AJAX POST endpoints are exempted from CSRF protection using @csrf.exempt decorators on their view functions

# Initialize Login Manager
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    from backend.auth import get_user_by_id
    return get_user_by_id(user_id)

# =========================================
# DATABASE INITIALIZATION
# =========================================

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# =========================================
# HEALTH CHECK ENDPOINT
# =========================================

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check database connection
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM movies')
        movie_count = c.fetchone()[0]
        conn.close()
        
        # Check API keys
        tmdb_key = os.getenv('TMDB_API_KEY')
        omdb_key = os.getenv('OMDB_API_KEY')
        
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'movie_count': movie_count,
            'tmdb_api_configured': bool(tmdb_key and tmdb_key != 'your_tmdb_api_key_here'),
            'omdb_api_configured': bool(omdb_key and omdb_key != 'your_omdb_api_key_here'),
            'version': '1.0.0'
        }
        
        return jsonify(health_status), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 503

# =========================================
# INPUT VALIDATION
# =========================================

def validate_movie_title(title):
    """Validate movie title input"""
    if not title or not isinstance(title, str):
        return False
    if len(title.strip()) < 2 or len(title.strip()) > 200:
        return False
    # Check for SQL injection patterns
    dangerous_patterns = ["'", '"', ";", "--", "/*", "*/", "xp_", "union", "select", "insert", "update", "delete", "drop"]
    title_lower = title.lower()
    for pattern in dangerous_patterns:
        if pattern in title_lower:
            return False
    return True

def validate_genre(genre):
    """Validate genre input"""
    if not genre or not isinstance(genre, str):
        return False
    valid_genres = ["Action", "Adventure", "Animation", "Biography", "Comedy", "Crime", "Drama", "Family", "Fantasy", "History", "Horror", "Music", "Mystery", "Romance", "Sci-Fi", "Sports", "Thriller", "War", "Western"]
    return genre.strip() in valid_genres

def validate_rating(rating):
    """Validate rating input"""
    try:
        rating_float = float(rating)
        return 0 <= rating_float <= 10
    except (ValueError, TypeError):
        return False

def validate_year(year):
    """Validate year input"""
    try:
        year_int = int(year)
        return 1900 <= year_int <= 2030
    except (ValueError, TypeError):
        return False

def validate_language(language):
    """Validate language input"""
    if not language or not isinstance(language, str):
        return False
    valid_languages = ["Hindi", "English", "Tamil", "Telugu", "Malayalam", "Bengali", "Kannada", "Marathi", "Punjabi", "Spanish", "French", "Japanese", "Korean"]
    return language.strip() in valid_languages

def validate_region(region):
    """Validate region input"""
    if not region or not isinstance(region, str):
        return False
    valid_regions = ["India", "USA", "UK", "International", "Korea", "Japan", "Bangladesh", "Pakistan"]
    return region.strip() in valid_regions

REGIONAL_SEEDS = [
    # Bengali
    {"title": "Pather Panchali", "genre": ["Drama"], "language": "Bengali", "region": "India", "runtime": 125, "rating": 8.3, "keywords": ["emotional", "deep", "moving"]},
    {"title": "Chokher Bali", "genre": ["Romance", "Drama"], "language": "Bengali", "region": "India", "runtime": 145, "rating": 7.1, "keywords": ["romantic", "love", "emotional", "dark"]},
    {"title": "Apur Sansar", "genre": ["Drama"], "language": "Bengali", "region": "India", "runtime": 105, "rating": 8.2, "keywords": ["emotional", "deep", "classic"]},
    {"title": "Charulata", "genre": ["Drama", "Romance"], "language": "Bengali", "region": "India", "runtime": 117, "rating": 8.1, "keywords": ["romantic", "love", "emotional"]},
    {"title": "Mahanagar", "genre": ["Drama"], "language": "Bengali", "region": "India", "runtime": 131, "rating": 8.2, "keywords": ["moving", "social", "classic"]},
    {"title": "Bhooter Bhabishyat", "genre": ["Comedy", "Fantasy"], "language": "Bengali", "region": "India", "runtime": 120, "rating": 8.1, "keywords": ["happy", "funny", "ghost"]},
    {"title": "Aparajito", "genre": ["Drama"], "language": "Bengali", "region": "India", "runtime": 110, "rating": 8.4, "keywords": ["emotional", "deep", "moving"]},
    {"title": "Nayak", "genre": ["Drama"], "language": "Bengali", "region": "India", "runtime": 120, "rating": 8.2, "keywords": ["moving", "classic", "deep"]},
    # Hindi
    {"title": "3 Idiots", "genre": ["Comedy", "Drama"], "language": "Hindi", "region": "India", "runtime": 170, "rating": 8.4, "keywords": ["happy", "funny", "motivated"]},
    {"title": "Dilwale Dulhania Le Jayenge", "genre": ["Romance", "Drama"], "language": "Hindi", "region": "India", "runtime": 189, "rating": 8.0, "keywords": ["happy", "romantic", "funny"]},
    {"title": "Sholay", "genre": ["Action", "Adventure"], "language": "Hindi", "region": "India", "runtime": 204, "rating": 8.1, "keywords": ["thrilling", "excited", "action"]},
    {"title": "Zindagi Na Milegi Dobara", "genre": ["Comedy", "Drama"], "language": "Hindi", "region": "India", "runtime": 155, "rating": 8.2, "keywords": ["happy", "excited", "funny"]},
    {"title": "Dangal", "genre": ["Biography", "Drama", "Sports"], "language": "Hindi", "region": "India", "runtime": 161, "rating": 8.4, "keywords": ["motivated", "inspirational", "sports"]},
    {"title": "Hera Pheri", "genre": ["Comedy"], "language": "Hindi", "region": "India", "runtime": 138, "rating": 8.2, "keywords": ["happy", "funny", "classic"]},
    {"title": "Andaz Apna Apna", "genre": ["Comedy"], "language": "Hindi", "region": "India", "runtime": 160, "rating": 8.1, "keywords": ["happy", "funny", "classic"]},
    {"title": "Welcome", "genre": ["Comedy"], "language": "Hindi", "region": "India", "runtime": 146, "rating": 7.0, "keywords": ["happy", "funny"]},
    {"title": "Dhamaal", "genre": ["Comedy"], "language": "Hindi", "region": "India", "runtime": 136, "rating": 7.5, "keywords": ["happy", "funny"]},
    {"title": "Bhool Bhulaiyaa", "genre": ["Comedy", "Thriller"], "language": "Hindi", "region": "India", "runtime": 159, "rating": 7.4, "keywords": ["thrilling", "funny", "mystery"]},
    {"title": "Garam Masala", "genre": ["Comedy"], "language": "Hindi", "region": "India", "runtime": 145, "rating": 7.2, "keywords": ["happy", "funny"]},
    # Tamil
    {"title": "Super Deluxe", "genre": ["Thriller", "Drama"], "language": "Tamil", "region": "India", "runtime": 176, "rating": 8.3, "keywords": ["dark", "thrilling", "funny"]},
    {"title": "Nayagan", "genre": ["Crime", "Drama"], "language": "Tamil", "region": "India", "runtime": 145, "rating": 8.6, "keywords": ["dark", "motivated", "sad"]},
    {"title": "Vikram Vedha", "genre": ["Action", "Crime", "Thriller"], "language": "Tamil", "region": "India", "runtime": 147, "rating": 8.2, "keywords": ["thrilled", "excited", "action"]},
    {"title": "Jai Bhim", "genre": ["Drama", "Crime"], "language": "Tamil", "region": "India", "runtime": 164, "rating": 8.8, "keywords": ["emotional", "deep", "moving", "motivated"]},
    {"title": "Anbe Sivam", "genre": ["Comedy", "Drama"], "language": "Tamil", "region": "India", "runtime": 160, "rating": 8.7, "keywords": ["happy", "funny", "emotional"]},
    # Telugu
    {"title": "Baahubali: The Beginning", "genre": ["Action", "Adventure"], "language": "Telugu", "region": "India", "runtime": 159, "rating": 8.0, "keywords": ["excited", "motivated", "thrilling"]},
    {"title": "Baahubali 2: The Conclusion", "genre": ["Action", "Adventure"], "language": "Telugu", "region": "India", "runtime": 167, "rating": 8.2, "keywords": ["excited", "motivated", "thrilling"]},
    {"title": "C/o Kancharapalem", "genre": ["Drama", "Romance"], "language": "Telugu", "region": "India", "runtime": 142, "rating": 8.9, "keywords": ["happy", "romantic", "sad"]},
    {"title": "RRR", "genre": ["Action", "Drama"], "language": "Telugu", "region": "India", "runtime": 187, "rating": 8.0, "keywords": ["excited", "motivated", "action"]},
    {"title": "Mahanati", "genre": ["Biography", "Drama"], "language": "Telugu", "region": "India", "runtime": 177, "rating": 8.5, "keywords": ["emotional", "deep", "biography"]},
    {"title": "Eega", "genre": ["Action", "Fantasy"], "language": "Telugu", "region": "India", "runtime": 145, "rating": 7.7, "keywords": ["action", "thrilling", "excited"]},
    # Malayalam
    {"title": "Drishyam", "genre": ["Thriller", "Crime"], "language": "Malayalam", "region": "India", "runtime": 160, "rating": 8.3, "keywords": ["thrilling", "mystery", "dark"]},
    {"title": "Kumbalangi Nights", "genre": ["Comedy", "Drama", "Romance"], "language": "Malayalam", "region": "India", "runtime": 135, "rating": 8.6, "keywords": ["happy", "funny", "romantic"]},
    # Kannada
    {"title": "Kantara", "genre": ["Action", "Drama", "Thriller"], "language": "Kannada", "region": "India", "runtime": 150, "rating": 8.3, "keywords": ["excited", "thrilling", "action"]},
    {"title": "777 Charlie", "genre": ["Drama", "Comedy", "Adventure"], "language": "Kannada", "region": "India", "runtime": 164, "rating": 8.9, "keywords": ["happy", "sad", "emotional"]},
    # Marathi
    {"title": "Sairat", "genre": ["Romance", "Drama"], "language": "Marathi", "region": "India", "runtime": 174, "rating": 8.3, "keywords": ["romantic", "sad", "emotional"]},
    {"title": "Natsamrat", "genre": ["Drama"], "language": "Marathi", "region": "India", "runtime": 166, "rating": 8.9, "keywords": ["emotional", "deep", "moving"]},
    {"title": "Court", "genre": ["Drama"], "language": "Marathi", "region": "India", "runtime": 116, "rating": 7.7, "keywords": ["deep", "classic"]},
    # Punjabi
    {"title": "Maula Jatt", "genre": ["Action", "Drama"], "language": "Punjabi", "region": "Pakistan", "runtime": 153, "rating": 8.2, "keywords": ["excited", "thrilled", "motivated"]},
    {"title": "Carry on Jatta", "genre": ["Comedy"], "language": "Punjabi", "region": "India", "runtime": 141, "rating": 7.6, "keywords": ["happy", "funny"]},
    {"title": "Qismat", "genre": ["Drama", "Romance"], "language": "Punjabi", "region": "India", "runtime": 137, "rating": 7.9, "keywords": ["romantic", "sad", "emotional"]}
]

def seed_reviews_from_csv(conn):
    try:
        import re
        c = conn.cursor()
        print("Seeding reviews from CSV...")
        csv_reviews_path = os.path.join(BASE_DIR, "database", "mouverse_review.csv")
        if not os.path.exists(csv_reviews_path):
            print(f"Warning: mouverse_review.csv not found at {csv_reviews_path}")
            return
            
        with open(csv_reviews_path, encoding="utf-8", errors="replace") as f:
            df = pd.read_csv(f)
            
        df = df.fillna("")
        reviews_to_insert = []
        for _, row in df.iterrows():
            movie_name_raw = row['Movie name']
            movie_title = re.sub(r'\s*\(\d{4}\)\s*$', '', str(movie_name_raw)).strip()
            
            rating_str = str(row['Rating'])
            q_count = rating_str.count('?')
            half = 1 if ('½' in rating_str or '\xbd' in rating_str) else 0
            rating = (q_count // 2) * 2 + half
            if rating == 0:
                rating = 8
            rating = min(max(rating, 1), 10)
            
            reviewer_name = str(row['Reviewer name']).strip()
            review_text = str(row['Review']).strip()
            created_at = str(row['Review date']).strip() or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            reviews_to_insert.append((
                movie_title,
                None, # movie_id
                None, # user_id
                reviewer_name,
                rating,
                review_text,
                created_at,
                0 # helpful_count
            ))
            
        if reviews_to_insert:
            c.executemany(
                """INSERT INTO reviews (movie_title, movie_id, user_id, reviewer_name, rating, review, created_at, helpful_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                reviews_to_insert
            )
            conn.commit()
            print(f"Successfully seeded {len(reviews_to_insert)} reviews from CSV.")
    except Exception as e:
        print(f"Error seeding reviews: {e}")

def init_db():
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = get_db_connection()
        c = conn.cursor()
        
        # Schema migration check
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='movies'")
        if c.fetchone():
            c.execute("PRAGMA table_info(movies)")
            columns = [col[1] for col in c.fetchall()]
            if "average_review_score" not in columns:
                print("Migrating database tables to new unified schema...")
                c.execute("DROP TABLE IF EXISTS reviews")
                c.execute("DROP TABLE IF EXISTS user_history")
                c.execute("DROP TABLE IF EXISTS movies")
                conn.commit()
            else:
                # Add country and origin_country columns if they are missing
                if "country" not in columns:
                    try:
                        c.execute("ALTER TABLE movies ADD COLUMN country TEXT")
                        print("Added country column to movies table.")
                    except sqlite3.OperationalError as e:
                        print(f"Error adding country column: {e}")
                if "origin_country" not in columns:
                    try:
                        c.execute("ALTER TABLE movies ADD COLUMN origin_country TEXT")
                        print("Added origin_country column to movies table.")
                    except sqlite3.OperationalError as e:
                        print(f"Error adding origin_country column: {e}")
                # Add poster_url column if missing
                if "poster_url" not in columns:
                    try:
                        c.execute("ALTER TABLE movies ADD COLUMN poster_url TEXT")
                        print("Added poster_url column to movies table.")
                    except sqlite3.OperationalError as e:
                        print(f"Error adding poster_url column: {e}")
                conn.commit()

        # 1. Users Table
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT NOT NULL,
                password TEXT NOT NULL,
                region TEXT,
                email_verified INTEGER DEFAULT 0,
                phone_verified INTEGER DEFAULT 0
            )
        """)
        
        # 2. Movies Table (SQLite store with Unified Schema)
        c.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id TEXT PRIMARY KEY,
                title TEXT UNIQUE NOT NULL,
                language TEXT,
                region TEXT,
                country TEXT,
                origin_country TEXT,
                genre TEXT, -- JSON list
                runtime INTEGER,
                year TEXT,
                rating REAL,
                overview TEXT,
                poster TEXT,
                poster_url TEXT,
                trailer_url TEXT,
                cast TEXT, -- JSON list
                director TEXT,
                keywords TEXT, -- JSON list
                average_review_score REAL,
                review_count INTEGER
            )
        """)
        
        # 3. OTP Verification Table
        c.execute("""
            CREATE TABLE IF NOT EXISTS otp_verification (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                otp_code TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL
            )
        """)
        
        # 4. User History Table
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_id TEXT NOT NULL,
                mood TEXT,
                watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                rating_given INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (movie_id) REFERENCES movies(id)
            )
        """)
        
        # 5. OMDb API Cache Table
        c.execute("""
            CREATE TABLE IF NOT EXISTS movie_omdb_cache (
                title TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 6. Unified Reviews Table
        c.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_id TEXT,
                movie_title TEXT NOT NULL,
                user_id INTEGER,
                reviewer_name TEXT, -- For CSV imported reviews
                rating INTEGER NOT NULL, -- Rating 1-10
                review TEXT,
                region TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                helpful_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 7. User Clicks Table
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_id TEXT NOT NULL,
                clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 8. User Searches Table
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                genre TEXT,
                mood TEXT,
                language TEXT,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        conn.commit()
        
        # Seed movies table
        c.execute("SELECT COUNT(*) FROM movies")
        movie_count = c.fetchone()[0]
        
        # First seed/update regional seeds list unconditionally on startup
        print("Seeding/updating regional seeds...")
        for m in REGIONAL_SEEDS:
            mock_id = "local_" + m["title"].lower().replace(" ", "_")
            if m["region"] == "India":
                country = "India"
                origin_country = "IN"
            elif m["region"] == "Pakistan":
                country = "Pakistan"
                origin_country = "PK"
            else:
                country = "United States of America"
                origin_country = "US"
            try:
                c.execute(
                    """INSERT OR REPLACE INTO movies (
                        id, title, language, region, country, origin_country, genre, runtime, year, rating, 
                        overview, poster, trailer_url, cast, director, keywords, 
                        average_review_score, review_count
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        mock_id, m["title"], m["language"], m["region"],
                        country, origin_country,
                        json.dumps(m["genre"]), m["runtime"], "2020", m["rating"],
                        "", "/posters/default-poster.jpg", "", json.dumps([]), "", json.dumps(m["keywords"]),
                        None, 0
                    )
                )
            except sqlite3.Error as e:
                print(f"Error seeding/updating regional movie {m['title']}: {e}")
        conn.commit()

        if movie_count == 0:
            print("Populating movies table with CSV seed data...")
            
            # First try to seed from movies_enriched.csv (has poster URLs)
            if os.path.exists(ENRICHED_CSV_PATH):
                df = pd.read_csv(ENRICHED_CSV_PATH)
                df = df.fillna("")
                for _, row in df.iterrows():
                    title = row['title']
                    mock_id = "local_" + title.lower().replace(" ", "_")
                    genres = [row['genre']]
                    runtime = int(row['runtime']) if row['runtime'] else 120
                    rating = float(row['rating']) if row['rating'] else 7.0
                    keywords = str(row['mood_tags']).split()
                    poster_url = row['poster_url'] if 'poster_url' in row and row['poster_url'] else ""
                    
                    try:
                        c.execute(
                            """INSERT OR IGNORE INTO movies (
                                id, title, language, region, country, origin_country, genre, runtime, year, rating, 
                                overview, poster, poster_url, trailer_url, cast, director, keywords, 
                                average_review_score, review_count
                               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                mock_id, title, row['language'], row['region'], 
                                "", "", json.dumps(genres), runtime, "", rating,
                                "", "/posters/default-poster.jpg", poster_url, "", json.dumps([]), "", json.dumps(keywords),
                                None, 0
                            )
                        )
                    except sqlite3.Error as e:
                        print(f"Error seeding enriched movie {title}: {e}")
                conn.commit()
                print("Movies seeding completed from enriched CSV.")
            # Fallback to movies.csv if enriched CSV not available
            elif os.path.exists(CSV_PATH):
                df = pd.read_csv(CSV_PATH)
                df = df.fillna("")
                for _, row in df.iterrows():
                    title = row['title']
                    mock_id = "local_" + title.lower().replace(" ", "_")
                    genres = [row['genre']]
                    runtime = int(row['runtime']) if row['runtime'] else 120
                    rating = float(row['rating']) if row['rating'] else 7.0
                    keywords = str(row['mood_tags']).split()
                    
                    try:
                        c.execute(
                            """INSERT OR IGNORE INTO movies (
                                id, title, language, region, country, origin_country, genre, runtime, year, rating, 
                                overview, poster, poster_url, trailer_url, cast, director, keywords, 
                                average_review_score, review_count
                               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                mock_id, title, row['language'], row['region'], 
                                "", "", json.dumps(genres), runtime, "", rating,
                                "", "/posters/default-poster.jpg", "", "", json.dumps([]), "", json.dumps(keywords),
                                None, 0
                            )
                        )
                    except sqlite3.Error as e:
                        print(f"Error seeding movie {title}: {e}")
                conn.commit()
                print("Movies seeding completed from basic CSV.")
            else:
                print(f"Warning: No CSV file found for seeding")
                
        # Seed reviews from CSV
        c.execute("SELECT COUNT(*) FROM reviews")
        reviews_count = c.fetchone()[0]
        if reviews_count == 0:
            seed_reviews_from_csv(conn)
            
        conn.close()
    except Exception as e:
        print(f"Database Initialization Error: {e}")

init_db()

# Register blueprints
from backend.auth import auth_bp
from backend.region import region_bp
app.register_blueprint(auth_bp)
app.register_blueprint(region_bp)

# =========================================
# INPUT VALIDATION & RATE LIMITING UTILITIES
# =========================================

from collections import defaultdict
from time import time
from functools import wraps

class RateLimiter:
    """Simple in-memory rate limiter for endpoints"""
    def __init__(self):
        self.requests = defaultdict(list)
        self.max_requests = 30  # max requests per minute
        self.window = 60  # seconds
    
    def is_allowed(self, user_id):
        now = time()
        # Clean old requests
        self.requests[user_id] = [t for t in self.requests[user_id] if now - t < self.window]
        
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        self.requests[user_id].append(now)
        return True

rate_limiter = RateLimiter()

def validate_region(region):
    """Validate region against allowed regions"""
    from backend.region import REGION_LANGUAGES
    if not region:
        return False
    return region in REGION_LANGUAGES

def validate_string_input(value, field_name, max_length=255):
    """Validate and sanitize string input"""
    if not value:
        return None
    
    sanitized = str(value).strip()
    if len(sanitized) == 0 or len(sanitized) > max_length:
        raise ValueError(f"{field_name} must be 1-{max_length} characters")
    return sanitized

def validate_movie_filters(mood=None, genre=None, language=None, min_rating=None, max_runtime=None):
    """Validate recommendation filters"""
    errors = []
    
    if mood:
        mood = validate_string_input(mood, "mood", 50)
    
    if genre:
        genre = validate_string_input(genre, "genre", 50)
    
    if language:
        language = validate_string_input(language, "language", 50)
    
    if min_rating is not None:
        try:
            min_rating = float(min_rating)
            if min_rating < 0 or min_rating > 10:
                errors.append("min_rating must be between 0 and 10")
        except (TypeError, ValueError):
            errors.append("min_rating must be a number")
    
    if max_runtime is not None:
        try:
            max_runtime = int(max_runtime)
            if max_runtime < 0 or max_runtime > 500:
                errors.append("max_runtime must be between 0 and 500")
        except (TypeError, ValueError):
            errors.append("max_runtime must be a number")
    
    if errors:
        raise ValueError("; ".join(errors))
    
    return mood, genre, language, min_rating, max_runtime

def rate_limit_chatbot(f):
    """Decorator to rate limit chatbot endpoint"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = current_user.id if current_user.is_authenticated else "anonymous"
        if not rate_limiter.is_allowed(user_id):
            return jsonify({"success": False, "error": "Rate limit exceeded. Maximum 30 messages per minute."}), 429
        return f(*args, **kwargs)
    return decorated_function

# =========================================
# OMDB API INTEGRATION WITH DATABASE CACHE
# =========================================

OMDB_API_KEY = os.getenv("OMDB_API_KEY")
if not OMDB_API_KEY or OMDB_API_KEY == "your_omdb_api_key_here":
    print("[WARNING] OMDB_API_KEY not configured. OMDb enrichment will be skipped.")
    OMDB_API_KEY = None

def fetch_movie_from_omdb(title):
    """Fetch movie details directly from OMDb API"""
    if not OMDB_API_KEY:
        return None
    if not title or len(str(title).strip()) == 0:
        return None
    try:
        safe_title = str(title).strip()[:100]  # Sanitize and limit length
        url = f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&t={safe_title}"
        response = requests.get(url, timeout=4)
        if response.status_code == 200:
            data = response.json()
            if data.get("Response") == "True":
                return data
    except Exception as e:
        print(f"[WARNING] OMDb Request Exception for '{title}': {e}")
    return None

def fetch_movie_with_cache(title):
    """OMDb lookup with SQLite cache for premium performance and API failure handling"""
    if not title or len(str(title).strip()) == 0:
        return None
    
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT data FROM movie_omdb_cache WHERE LOWER(title) = LOWER(?)", (str(title)[:100],))
        row = c.fetchone()
        
        if row:
            return json.loads(row[0])
            
        # Not cached, request OMDb API
        data = fetch_movie_from_omdb(title)
        if data:
            # Save to database cache
            try:
                c.execute(
                    "INSERT OR REPLACE INTO movie_omdb_cache (title, data) VALUES (?, ?)",
                    (str(title)[:100], json.dumps(data))
                )
                conn.commit()
            except Exception as e:
                print(f"[WARNING] Error caching movie: {e}")
            return data
    except Exception as e:
        print(f"[ERROR] fetch_movie_with_cache failed: {e}")
    finally:
        if conn:
            conn.close()
    return None

# =========================================
# APPLICATION ROUTING & API ENDPOINTS
# =========================================

def normalize_title(title):
    if not title:
        return ""
    # Normalize to lowercase, strip spaces
    normalized = title.lower().strip()
    # Replace non-alphanumeric character sequences with a single hyphen
    normalized = re.sub(r'[^a-z0-9]+', '-', normalized)
    # Remove leading and trailing hyphens
    normalized = normalized.strip('-')
    return normalized

import threading
poster_cache_lock = threading.Lock()

def load_poster_search_cache():
    posters_dir = os.path.join(BASE_DIR, "public", "posters")
    new_cache_file = os.path.join(posters_dir, "poster_search_cache.json")
    old_cache_file = os.path.join(posters_dir, "poster_cache.json")
    
    cache = {}
    
    if os.path.exists(new_cache_file):
        try:
            with open(new_cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    if isinstance(v, dict) and "poster_url" in v:
                        cache[k] = {
                            "movie_id": v.get("movie_id"),
                            "movie_title": v.get("movie_title"),
                            "poster_url": v.get("poster_url"),
                            "tmdb_result": v.get("tmdb_result"),
                            "omdb_result": v.get("omdb_result")
                        }
            return cache
        except Exception as e:
            print(f"[ERROR] Failed to read poster_search_cache.json: {e}")
            
    if os.path.exists(old_cache_file):
        try:
            with open(old_cache_file, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                for k, v in old_data.items():
                    if isinstance(v, str):
                        if k.startswith("id_"):
                            movie_id = k[3:]
                            cache[movie_id] = {
                                "movie_id": movie_id,
                                "movie_title": None,
                                "poster_url": v,
                                "tmdb_result": "None",
                                "omdb_result": "None"
                            }
                        else:
                            cache[k] = {
                                "movie_id": None,
                                "movie_title": k,
                                "poster_url": v,
                                "tmdb_result": "None",
                                "omdb_result": "None"
                            }
            # Save converted cache
            save_poster_search_cache(cache)
        except Exception as e:
            print(f"[ERROR] Failed to convert old poster cache: {e}")
            
    return cache

def save_poster_search_cache(cache):
    posters_dir = os.path.join(BASE_DIR, "public", "posters")
    new_cache_file = os.path.join(posters_dir, "poster_search_cache.json")
    os.makedirs(posters_dir, exist_ok=True)
    try:
        with open(new_cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save poster_search_cache.json: {e}")

def search_tmdb_poster(title, year=None, language=None):
    tmdb_key = os.getenv("TMDB_API_KEY")
    if not tmdb_key or tmdb_key == "your_tmdb_api_key_here" or not getattr(recommender, "tmdb_enabled", True):
        return None
    try:
        params = {
            "api_key": tmdb_key,
            "query": title
        }
        if year:
            match = re.search(r'\b(19\d{2}|20\d{2})\b', str(year))
            if match:
                params["primary_release_year"] = match.group(1)
        if language:
            from backend.recommender import LANG_MAP
            lang_code = LANG_MAP.get(language, language)
            params["language"] = lang_code
            
        url = "https://api.tmdb.org/3/search/movie"
        r = requests.get(url, params=params, timeout=3)
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                for match in results:
                    tmdb_title = match.get("title")
                    if tmdb_title and normalize_title(tmdb_title) == normalize_title(title):
                        poster_path = match.get("poster_path")
                        if poster_path:
                            return f"https://image.tmdb.org/t/p/w500{poster_path}"
                for match in results:
                    orig_title = match.get("original_title")
                    if orig_title and normalize_title(orig_title) == normalize_title(title):
                        poster_path = match.get("poster_path")
                        if poster_path:
                            return f"https://image.tmdb.org/t/p/w500{poster_path}"
                for match in results:
                    poster_path = match.get("poster_path")
                    if poster_path:
                        return f"https://image.tmdb.org/t/p/w500{poster_path}"
        elif r.status_code == 401:
            print("[WARNING] TMDB API key is invalid (status 401) in poster search. Disabling TMDB integration.")
            recommender.tmdb_enabled = False
    except Exception as e:
        print(f"[ERROR] TMDB poster search exception: {e}")
    return None

def search_omdb_poster(title, year=None):
    omdb_key = os.getenv("OMDB_API_KEY")
    if not omdb_key or not getattr(recommender, "omdb_enabled", True):
        return None
    try:
        params = {
            "apikey": omdb_key,
            "t": title
        }
        if year:
            match = re.search(r'\b(19\d{2}|20\d{2})\b', str(year))
            if match:
                params["y"] = match.group(1)
                
        url = "http://www.omdbapi.com/"
        r = requests.get(url, params=params, timeout=3)
        if r.status_code == 200:
            data = r.json()
            if data.get("Response") == "True":
                poster = data.get("Poster")
                if poster and poster != "N/A" and poster.startswith("http"):
                    return poster
    except Exception as e:
        print(f"[ERROR] OMDb poster search exception: {e}")
    return None

def bg_cache_poster_improved(movie_id, title, url_to_download, dest_path, local_url):
    try:
        movie_id_str = str(movie_id) if movie_id else None
        if url_to_download and url_to_download.startswith("http"):
            logger.info(f"Downloading poster for {title} (ID: {movie_id}) from {url_to_download}")
            r = requests.get(url_to_download, timeout=8)
            if r.status_code == 200:
                from PIL import Image
                import io
                img_data = r.content
                img_saved = False
                try:
                    img = Image.open(io.BytesIO(img_data))
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    img.thumbnail((500, 750), Image.Resampling.LANCZOS)
                    img.save(dest_path, format="JPEG", quality=85, optimize=True)
                    img_saved = True
                except Exception as img_err:
                    logger.warning(f"PIL compression failed for {title}: {img_err}, using raw save")
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    with open(dest_path, "wb") as f:
                        f.write(img_data)
                    img_saved = True
                
                if img_saved:
                    with poster_cache_lock:
                        try:
                            cache = load_poster_search_cache()
                            old_entry = None
                            if movie_id_str and movie_id_str in cache:
                                old_entry = cache[movie_id_str]
                            elif title and title in cache:
                                old_entry = cache[title]
                                
                            if old_entry:
                                old_entry["poster_url"] = local_url
                                entry = old_entry
                            else:
                                entry = {
                                    "movie_id": movie_id_str,
                                    "movie_title": title,
                                    "poster_url": local_url,
                                    "tmdb_result": url_to_download if "tmdb.org" in url_to_download or "api.tmdb" in url_to_download else "None",
                                    "omdb_result": url_to_download if "omdbapi" in url_to_download or "omdb" in url_to_download else "None"
                                }
                            
                            if movie_id_str:
                                cache[movie_id_str] = entry
                            if title:
                                cache[title] = entry
                                
                            save_poster_search_cache(cache)
                            logger.info(f"Saved and cached poster for {title} locally at {local_url}")
                        except Exception as cache_err:
                            logger.error(f"Failed to update poster cache for {title}: {cache_err}")
    except Exception as e:
        logger.error(f"Failed to cache poster for {title}: {e}")

def get_or_download_poster(movie_id, title, tmdb_poster_url=None, year=None, language=None):
    posters_dir = os.path.join(BASE_DIR, "public", "posters")
    default_poster = "/posters/default-poster.jpg"
    
    if not title:
        logger.debug(f"Poster lookup failed - No title provided. Using default poster.")
        return default_poster
        
    os.makedirs(posters_dir, exist_ok=True)
    movie_id_str = str(movie_id) if movie_id else None
    
    # Check cache — but SKIP any entry that only has default-poster.jpg (poisoned/stale)
    with poster_cache_lock:
        cache = load_poster_search_cache()
        
    cached_entry = None
    if movie_id_str and movie_id_str in cache:
        cached_entry = cache[movie_id_str]
    elif title and title in cache:
        cached_entry = cache[title]
        
    if cached_entry:
        url = cached_entry.get("poster_url")
        # Never trust a cached default-poster — always re-query APIs for real posters
        if url and url != default_poster:
            if url.startswith("/posters/"):
                filename = url.split("/")[-1]
                local_path = os.path.join(posters_dir, filename)
                if os.path.exists(local_path):
                    logger.debug(f"Poster cache hit for {title} - using local file")
                    return url
            elif url.startswith("http"):
                logger.debug(f"Poster cache hit for {title} - using remote URL")
                return url
                
    # Cache miss (or was default-poster) — search priority: TMDB -> OMDb -> Local -> Default
    tmdb_result = None
    if tmdb_poster_url and not tmdb_poster_url.startswith("https://placehold.co") and "placeholder" not in tmdb_poster_url:
        if tmdb_poster_url.startswith("http"):
            tmdb_result = tmdb_poster_url
        elif tmdb_poster_url.startswith("/") and not tmdb_poster_url.startswith("/posters/") and not tmdb_poster_url.startswith("/static/"):
            tmdb_result = f"https://image.tmdb.org/t/p/w500{tmdb_poster_url}"
            
    if not tmdb_result:
        tmdb_result = search_tmdb_poster(title, year, language)
        
    omdb_result = None
    final_url = None
    
    if tmdb_result:
        final_url = tmdb_result
        omdb_result = "None"
    else:
        tmdb_result = "None"
        omdb_result = search_omdb_poster(title, year)
        if omdb_result:
            final_url = omdb_result
        else:
            omdb_result = "None"
            # Check local folder by movie_id or normalized title
            if movie_id_str:
                filename = f"{movie_id_str}.jpg"
            else:
                filename = f"{normalize_title(title)}.jpg"
            local_dest_path = os.path.join(posters_dir, filename)
            local_url = f"/posters/{filename}"
            if os.path.exists(local_dest_path):
                final_url = local_url
            else:
                # Also check by normalized title when we have a movie_id
                normalized_filename = f"{normalize_title(title)}.jpg"
                normalized_path = os.path.join(posters_dir, normalized_filename)
                if os.path.exists(normalized_path):
                    final_url = f"/posters/{normalized_filename}"
                else:
                    final_url = default_poster
                
    # Logging
    logger.debug(f"Poster lookup for {title} - TMDB: {tmdb_result}, OMDb: {omdb_result}, Final: {final_url}")
    
    # Only cache if we found a real poster (not the default fallback)
    if final_url != default_poster:
        new_entry = {
            "movie_id": movie_id_str,
            "movie_title": title,
            "poster_url": final_url,
            "tmdb_result": tmdb_result,
            "omdb_result": omdb_result
        }
        with poster_cache_lock:
            cache = load_poster_search_cache()
            if movie_id_str:
                cache[movie_id_str] = new_entry
            if title:
                cache[title] = new_entry
            save_poster_search_cache(cache)
        
    # Kick off background download if it's a remote URL
    if final_url.startswith("http"):
        if movie_id_str:
            filename = f"{movie_id_str}.jpg"
        else:
            filename = f"{normalize_title(title)}.jpg"
        dest_path = os.path.join(posters_dir, filename)
        local_url = f"/posters/{filename}"
        
        t = threading.Thread(
            target=bg_cache_poster_improved,
            args=(movie_id, title, final_url, dest_path, local_url)
        )
        t.daemon = True
        t.start()
        
    return final_url

@app.route("/posters/<path:filename>")
def serve_poster(filename):
    posters_dir = os.path.join(BASE_DIR, "public", "posters")
    return send_from_directory(posters_dir, filename)

@app.route("/api/posters", methods=["GET"])
def api_posters():
    """Scans public/posters/ directory, reads poster_cache.json, and returns unified mapping"""
    posters_dir = os.path.join(BASE_DIR, "public", "posters")
    cache_file = os.path.join(posters_dir, "poster_cache.json")
    
    # Initialize mapping from cache file
    mapping = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                for title, path in cache_data.items():
                    normalized = normalize_title(title)
                    if normalized:
                        mapping[normalized] = path
        except Exception as e:
            print(f"[ERROR] Failed to read poster_cache.json: {e}")
            
    # Scan directory for newly added/untracked posters
    if os.path.exists(posters_dir):
        try:
            for filename in os.listdir(posters_dir):
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    name_without_ext = os.path.splitext(filename)[0]
                    normalized = normalize_title(name_without_ext)
                    if normalized and normalized not in mapping:
                        mapping[normalized] = f"/posters/{filename}"
        except Exception as e:
            print(f"[ERROR] Failed to scan posters directory: {e}")
            
    return jsonify(mapping)

@app.route("/")
@login_required
def home():
    # Force region selection if not configured
    region = session.get("region") or current_user.region
    if not region:
        flash("Please select your region first.", "info")
        return redirect(url_for("region.select_region"))
        
    # Clear recommendation session cache on page reload to ensure fresh database content is loaded
    keys_to_remove = [k for k in list(session.keys()) if k.startswith("recs_")]
    for k in keys_to_remove:
        session.pop(k, None)
        
    from backend.region import REGION_LANGUAGES
    languages = REGION_LANGUAGES.get(region, ["English"])
    return render_template(
        "index.html",
        user=current_user,
        region=region,
        languages=languages,
        user_id=current_user.id,
    )

@app.route("/api/trending", methods=["GET"])
@login_required
def api_trending():
    """Fetch trending movies from TMDB"""
    try:
        time_window = request.args.get("time_window", "day")  # "day" or "week"
        region = session.get("region") or current_user.region
        
        print(f"[DEBUG] Trending Request Started - time_window: {time_window}, region: {region}")
        
        # Fetch trending movies from TMDB
        trending_movies = recommender.fetch_trending_movies(time_window)
        
        if not trending_movies:
            return jsonify({"success": True, "movies": []})
        
        # Process and cache trending movies
        rich_recs = []
        for movie in trending_movies[:12]:  # Limit to 12 movies
            tmdb_id = movie.get("id")
            try:
                # Check if already cached
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("SELECT * FROM movies WHERE id = ?", (str(tmdb_id),))
                cached = c.fetchone()
                conn.close()
                
                if cached:
                    m = dict(cached)
                    # Parse JSON fields
                    genres = json.loads(m["genre"]) if isinstance(m["genre"], str) else (m["genre"] or [])
                    cast = json.loads(m["cast"]) if isinstance(m["cast"], str) else (m["cast"] or [])
                    
                    rich_recs.append({
                        "id": m["id"],
                        "title": m["title"],
                        "genre": ", ".join(genres) if isinstance(genres, list) else str(genres),
                        "language": m["language"],
                        "rating": m["rating"],
                        "poster": get_or_download_poster(m["id"], m["title"], m["poster"], year=m.get("year"), language=m.get("language")),
                        "overview": m["overview"] if m["overview"] else "Plot details are currently unavailable.",
                        "release_date": m["year"] if m["year"] else "N/A",
                        "popularity": movie.get("popularity", 0)
                    })
                else:
                    # Fetch details and cache
                    movie_details = recommender.fetch_tmdb_movie_details(tmdb_id)
                    if movie_details:
                        title = movie_details.get("title")
                        omdb_details = recommender.enrich_movie_with_omdb(title, movie_details.get("release_date", "")[:4])
                        recommender.cache_movie_to_db(movie_details, omdb_details, region_pref=region)
                        
                        # Add to results
                        genres = [g.get("name") for g in movie_details.get("genres", [])]
                        poster_path = movie_details.get("poster_path")
                        poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
                        
                        from backend.recommender import LANG_MAP
                        orig_lang = movie_details.get("original_language", "en")
                        lang_name = next((k for k, v in LANG_MAP.items() if v == orig_lang), "English")
                        
                        rich_recs.append({
                            "id": str(tmdb_id),
                            "title": title,
                            "genre": ", ".join(genres),
                            "language": lang_name,
                            "rating": movie_details.get("vote_average", 0.0),
                            "poster": get_or_download_poster(str(tmdb_id), title, poster, year=movie_details.get("release_date", "")[:4], language=lang_name),
                            "overview": movie_details.get("overview", ""),
                            "release_date": movie_details.get("release_date", "")[:4],
                            "popularity": movie.get("popularity", 0)
                        })
            except Exception as e:
                print(f"[ERROR] Error processing trending movie {tmdb_id}: {e}")
                continue
        
        print(f"[DEBUG] Trending Movies Returned Count: {len(rich_recs)}")
        return jsonify({"success": True, "movies": rich_recs})
    except Exception as e:
        print(f"[ERROR] api_trending failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": "An unexpected error occurred"}), 500

@app.route("/api/recommendations", methods=["GET"])
@login_required
def api_recommendations():
    try:
        # Validate and sanitize input parameters
        try:
            mood, genre, language, min_rating, max_runtime = validate_movie_filters(
                mood=request.args.get("mood", ""),
                genre=request.args.get("genre", ""),
                language=request.args.get("language", ""),
                min_rating=request.args.get("min_rating", 0),
                max_runtime=request.args.get("runtime", 240)
            )
        except ValueError as ve:
            return jsonify({"success": False, "error": str(ve)}), 400
        
        selected_region = request.args.get("selectedRegion", "").strip()
        if selected_region and not validate_region(selected_region):
            return jsonify({"success": False, "error": "Invalid region specified"}), 400
        
        region = selected_region or session.get("region") or current_user.region
        min_rating = float(min_rating) if min_rating else 0
        max_runtime = int(max_runtime) if max_runtime else 240
        
        print(f"[DEBUG] Recommendation Request Started - mood: {mood}, genre: {genre}, language: {language}, region: {region}, min_rating: {min_rating}, max_runtime: {max_runtime}")
        
        # Validate inputs
        if not region:
            print("[ERROR] Region not found in session or user profile")
            return jsonify({"success": False, "error": "Region not configured. Please select your region first."}), 400
        
        # Cache check — skip stale entries where posters are still default
        cache_key = f"recs_{mood}_{genre}_{language}_{region}_{min_rating}_{max_runtime}"
        if cache_key in session:
            cached_data = session[cache_key]
            movies_list = cached_data.get("movies", []) if isinstance(cached_data, dict) else cached_data
            has_stale = any(
                (m.get("omdb_poster") or m.get("poster", "")).endswith("default-poster.jpg")
                for m in movies_list
            )
            if not has_stale:
                print("[DEBUG] Returning cached recommendations")
                if isinstance(cached_data, dict):
                    return jsonify({"success": True, "movies": movies_list, "message": cached_data.get("message")})
                else:
                    return jsonify({"success": True, "movies": movies_list})
            else:
                print("[DEBUG] Session cache has stale default posters — re-fetching")
                session.pop(cache_key, None)
            
        # Log search query for personalization
        if current_user.is_authenticated:
            try:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute(
                    "INSERT INTO user_searches (user_id, genre, mood, language) VALUES (?, ?, ?, ?)",
                    (current_user.id, genre, mood, language)
                )
                conn.commit()
                conn.close()
            except Exception as search_err:
                print(f"[ERROR] Error logging search: {search_err}")

        # Call the upgraded recommender with error handling
        try:
            movies, warning_msg = recommender.recommend(
                mood=mood,
                genre=genre,
                language=language,
                region=region,
                min_rating=min_rating,
                max_runtime=max_runtime,
                n=20,
                user_id=current_user.id
            )
        except Exception as recommender_error:
            print(f"[ERROR] Recommender failed: {recommender_error}")
            return jsonify({"success": False, "error": "Recommendation engine failure. Please try again later."}), 500
        
        if not movies or not isinstance(movies, list):
            print("[WARNING] No movies returned from recommender")
            return jsonify({"success": True, "movies": []})
        
        # Build base records first (no poster fetch yet)
        base_recs = []
        for m in movies:
            try:
                title = m.get("title")
                lang = m.get("language")
                poster = m.get("poster")
                poster_url = m.get("poster_url")

                # Only title and language are required
                if not title or not lang:
                    print(f"[DEBUG] Skipping movie missing title or language: title={title}, lang={lang}")
                    continue

                # Prefer poster_url (enriched CSV) over poster field
                if poster_url and poster_url.strip() and poster_url not in ("null", "None", ""):
                    poster = poster_url
                elif not poster or poster == "/posters/default-poster.jpg":
                    posters_dir = os.path.join(BASE_DIR, "public", "posters")
                    normalized = title.lower().replace(" ", "-").replace("'", "").replace("!", "").replace(":", "").replace(",", "").replace("?", "").replace(".", "")
                    local_path = os.path.join(posters_dir, f"{normalized}.jpg")
                    poster = f"/posters/{normalized}.jpg" if os.path.exists(local_path) else None

                genres = json.loads(m["genre"]) if isinstance(m["genre"], str) else (m["genre"] or [])
                cast = json.loads(m["cast"]) if isinstance(m["cast"], str) else (m["cast"] or [])

                base_recs.append({
                    "_movie_id": m.get("id", ""),
                    "_poster_hint": poster,
                    "_year": m.get("year"),
                    "_lang": lang,
                    "id": m.get("id", ""),
                    "title": title,
                    "genre": ", ".join(genres) if isinstance(genres, list) else str(genres),
                    "language": lang,
                    "region": m.get("region", ""),
                    "runtime": m.get("runtime", 120),
                    "rating": m.get("rating", 0.0),
                    "ml_score": m.get("ml_score", 0),
                    "average_review_score": m.get("average_review_score"),
                    "review_count": m.get("review_count", 0),
                    "omdb_plot": m.get("overview") or "Plot details are currently unavailable.",
                    "omdb_cast": ", ".join(cast) if isinstance(cast, list) else str(cast),
                    "omdb_director": m.get("director") or "N/A",
                    "omdb_year": m.get("year") or "N/A",
                    "imdb_rating": str(m.get("rating")) if m.get("rating") else "N/A",
                    "trailer_url": m.get("trailer_url", "")
                })
            except Exception as movie_error:
                print(f"[ERROR] Error processing movie {m.get('title', 'unknown')}: {movie_error}")
                continue

        # Fetch all posters in parallel using ThreadPoolExecutor
        from concurrent.futures import ThreadPoolExecutor, as_completed
        def _resolve_poster(rec):
            return rec, get_or_download_poster(
                rec["_movie_id"], rec["title"], rec["_poster_hint"],
                year=rec["_year"], language=rec["_lang"]
            )

        rich_recs = []
        with ThreadPoolExecutor(max_workers=min(10, len(base_recs) or 1)) as pool:
            futures = {pool.submit(_resolve_poster, rec): rec for rec in base_recs}
            results = {}
            for fut in as_completed(futures):
                try:
                    rec, poster_url = fut.result(timeout=8)
                    results[rec["id"]] = (rec, poster_url)
                except Exception as fe:
                    rec = futures[fut]
                    print(f"[ERROR] Parallel poster fetch failed for {rec.get('title')}: {fe}")
                    results[rec["id"]] = (rec, "/posters/default-poster.jpg")

        # Preserve original order
        for rec in base_recs:
            entry, poster_url = results.get(rec["id"], (rec, "/posters/default-poster.jpg"))
            entry = dict(entry)  # copy
            entry["omdb_poster"] = poster_url
            # Remove internal helper keys
            for k in ("_movie_id", "_poster_hint", "_year", "_lang"):
                entry.pop(k, None)
            rich_recs.append(entry)

        # Cache in session only if no default posters remain
        has_stale = any(r.get("omdb_poster", "").endswith("default-poster.jpg") for r in rich_recs)
        if not has_stale:
            session[cache_key] = {"movies": rich_recs, "message": warning_msg}
        
        print(f"[DEBUG] Movies Returned Count: {len(rich_recs)}")
        print(f"[DEBUG] Recommendation Request Completed")
        print(f"[API LOG] Movies Rendered: {len(rich_recs)}")
        return jsonify({"success": True, "movies": rich_recs, "message": warning_msg})
    except ValueError as ve:
        print(f"[ERROR] Invalid parameter value: {ve}")
        return jsonify({"success": False, "error": "Invalid parameter value provided."}), 400
    except Exception as e:
        print(f"[ERROR] recommendations API failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": "An unexpected error occurred. Please try again."}), 500

@app.route("/api/watch", methods=["POST"])
@csrf.exempt
@login_required
def api_watch():
    try:
        data = request.get_json()
        if not data or "movie_id" not in data:
            return jsonify({"success": False, "error": "Missing movie_id"}), 400
            
        movie_id = data.get("movie_id")
        mood = data.get("mood", "")
        
        if not movie_id:
            return jsonify({"success": False, "error": "Invalid movie_id"}), 400
        
        # Save watched movie record to user history database
        conn = get_db_connection()
        c = conn.cursor()
        try:
            # Check if already watched recently to prevent duplicates in history
            c.execute(
                "SELECT id FROM user_history WHERE user_id = ? AND movie_id = ? LIMIT 1",
                (current_user.id, movie_id)
            )
            exists = c.fetchone()
            
            if not exists:
                c.execute(
                    "INSERT INTO user_history (user_id, movie_id, mood) VALUES (?, ?, ?)",
                    (current_user.id, movie_id, mood)
                )
                conn.commit()
                success_msg = "Movie added to watch history."
            else:
                success_msg = "Movie already in watch history."
                
            conn.close()
            return jsonify({"success": True, "message": success_msg})
        except sqlite3.Error as db_error:
            conn.close()
            print(f"[ERROR] Database error in api_watch: {db_error}")
            return jsonify({"success": False, "error": "Database error occurred"}), 500
    except Exception as e:
        print(f"[ERROR] api_watch failed: {e}")
        return jsonify({"success": False, "error": "An unexpected error occurred"}), 500

@app.route("/api/history", methods=["GET"])
@login_required
def api_history():
    try:
        # Fetch watch history list for logged in user
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute("""
                SELECT h.id as history_id, h.mood as watched_mood, h.watched_at, h.rating_given, m.* 
                FROM user_history h
                JOIN movies m ON h.movie_id = m.id
                WHERE h.user_id = ?
                ORDER BY h.watched_at DESC
            """, (current_user.id,))
            rows = c.fetchall()
        except sqlite3.Error as db_error:
            conn.close()
            print(f"[ERROR] Database error in api_history: {db_error}")
            return jsonify({"success": False, "error": "Database error occurred"}), 500
        
        conn.close()
        
        history_list = []
        base_history = []
        for r in rows:
            try:
                title = r["title"]
                poster_hint = r["poster"] if r["poster"] else None
                base_history.append({"row": dict(r), "title": title, "poster_hint": poster_hint})
            except Exception as item_error:
                print(f"[ERROR] Error processing history item: {item_error}")
                continue

        # Fetch posters in parallel
        from concurrent.futures import ThreadPoolExecutor, as_completed
        def _resolve_history_poster(item):
            r = item["row"]
            poster = get_or_download_poster(r["id"], item["title"], item["poster_hint"],
                                           year=r.get("year"), language=r.get("language"))
            return item["row"]["history_id"], poster

        poster_map = {}
        if base_history:
            with ThreadPoolExecutor(max_workers=min(8, len(base_history))) as pool:
                futures = {pool.submit(_resolve_history_poster, item): item for item in base_history}
                for fut in as_completed(futures):
                    try:
                        hid, purl = fut.result(timeout=8)
                        poster_map[hid] = purl
                    except Exception as fe:
                        item = futures[fut]
                        print(f"[ERROR] Poster fetch failed for history item: {fe}")
                        poster_map[item["row"]["history_id"]] = "/posters/default-poster.jpg"

        for item in base_history:
            r = item["row"]
            history_list.append({
                "history_id": r["history_id"],
                "movie_id": r["id"],
                "title": r["title"],
                "genre": r["genre"],
                "language": r["language"],
                "rating_given": r["rating_given"],
                "poster": poster_map.get(r["history_id"], "/posters/default-poster.jpg"),
                "watched_at": r["watched_at"]
            })
            
        return jsonify({"success": True, "history": history_list})
    except Exception as e:
        print(f"[ERROR] api_history failed: {e}")
        return jsonify({"success": False, "error": "An unexpected error occurred"}), 500

@app.route("/api/fetch-poster", methods=["GET"])
@login_required
def api_fetch_poster():
    """Lazy poster fetch endpoint — called by frontend for any card still showing default poster."""
    try:
        movie_id = request.args.get("id", "").strip()
        title = request.args.get("title", "").strip()
        year = request.args.get("year", "").strip()
        language = request.args.get("lang", "").strip()
        if not title:
            return jsonify({"success": False, "error": "title is required"}), 400
        poster_url = get_or_download_poster(movie_id or None, title, None, year=year or None, language=language or None)
        print(f"[FETCH-POSTER API] title={title} => {poster_url}")
        return jsonify({"success": True, "poster_url": poster_url})
    except Exception as e:
        print(f"[ERROR] api_fetch_poster failed: {e}")
        return jsonify({"success": False, "error": "Could not fetch poster"}), 500

@app.route("/api/rate", methods=["POST"])
@csrf.exempt
@login_required
def api_rate():
    try:
        data = request.get_json()
        if not data or "history_id" not in data or "rating" not in data:
            return jsonify({"success": False, "error": "Missing parameters"}), 400
            
        history_id = data.get("history_id")
        rating = int(data.get("rating"))
        
        if rating < 1 or rating > 5:
            return jsonify({"success": False, "error": "Rating must be between 1 and 5"}), 400
        
        if not history_id:
            return jsonify({"success": False, "error": "Invalid history_id"}), 400
        
        conn = get_db_connection()
        c = conn.cursor()
        try:
            # Verify ownership
            c.execute("SELECT user_id FROM user_history WHERE id = ?", (history_id,))
            row = c.fetchone()
            if not row or row["user_id"] != current_user.id:
                conn.close()
                return jsonify({"success": False, "error": "Unauthorized"}), 403
                
            c.execute(
                "UPDATE user_history SET rating_given = ? WHERE id = ?",
                (rating, history_id)
            )
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": "Rating updated successfully."})
        except sqlite3.Error as db_error:
            conn.close()
            print(f"[ERROR] Database error in api_rate: {db_error}")
            return jsonify({"success": False, "error": "Database error occurred"}), 500
    except ValueError as ve:
        print(f"[ERROR] Invalid rating value: {ve}")
        return jsonify({"success": False, "error": "Invalid rating value"}), 400
    except Exception as e:
        print(f"[ERROR] api_rate failed: {e}")
        return jsonify({"success": False, "error": "An unexpected error occurred"}), 500


@app.route("/api/click", methods=["POST"])
@csrf.exempt
@login_required
def api_click():
    try:
        data = request.get_json() or {}
        movie_id = data.get("movie_id")
        if not movie_id:
            return jsonify({"success": False, "error": "Missing movie_id"}), 400
            
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO user_clicks (user_id, movie_id) VALUES (?, ?)", (current_user.id, movie_id))
        conn.commit()
        conn.close()
        print(f"[DEBUG] Click logged for user {current_user.id}, movie {movie_id}")
        return jsonify({"success": True})
    except Exception as e:
        print(f"[ERROR] api_click failed: {e}")
        return jsonify({"success": False, "error": "Could not record click. Please try again later."}), 500


@app.route("/api/recommendations-personalized", methods=["GET"])
@login_required
def api_personalized_recommendations():
    try:
        region = session.get("region") or current_user.region
        if not region:
            return jsonify({"success": False, "error": "Region not configured"}), 400
            
        # Compile user's taste profile
        prefs = _get_user_preferences(current_user.id)
        fav_genres = prefs.get("favorite_genres", [])
        fav_langs = prefs.get("favorite_languages", [])
        highly_rated = prefs.get("highly_rated_genres", [])
        
        # If no preferences yet, return empty list or fallback to trending
        if not fav_genres and not fav_langs:
            return jsonify({"success": True, "movies": [], "reason": "No watch history or searches yet."})

        # Query all cached movies from database
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM movies")
        movies = [dict(row) for row in c.fetchall()]
        
        # Filter out movies already watched by the user
        c.execute("SELECT movie_id FROM user_history WHERE user_id = ?", (current_user.id,))
        watched_ids = {str(row[0]) for row in c.fetchall()}
        conn.close()
        
        # Filter by region constraint
        candidate_movies = []
        for m in movies:
            if m["id"] in watched_ids:
                continue
            if not is_region_match(m, region):
                continue
                
            # Parse genre
            try:
                m_genres = json.loads(m["genre"]) if isinstance(m["genre"], str) and m["genre"].startswith('[') else ([m["genre"]] if m["genre"] else [])
            except Exception:
                m_genres = []
                
            candidate_movies.append((m, m_genres))

        # Score candidates (poster fetch deferred)
        pre_scored = []
        for m, m_genres in candidate_movies:
            title = m.get("title")
            lang = m.get("language")
            if not title or not lang:
                continue

            poster = m.get("poster")
            poster_url = m.get("poster_url")
            if poster_url and poster_url.strip() and poster_url not in ("null", "None", ""):
                poster = poster_url
            elif not poster or poster == "/posters/default-poster.jpg":
                posters_dir = os.path.join(BASE_DIR, "public", "posters")
                normalized = title.lower().replace(" ", "-").replace("'", "").replace("!", "").replace(":", "").replace(",", "").replace("?", "").replace(".", "")
                local_path = os.path.join(posters_dir, f"{normalized}.jpg")
                poster = f"/posters/{normalized}.jpg" if os.path.exists(local_path) else None

            rating = m["rating"] or 5.0
            score = rating / 10.0
            reason = "Recommended because it's a popular choice in your region."
            matched_genre = None
            matched_lang = None

            for i, fg in enumerate(fav_genres):
                if any(fg.lower() == mg.lower() for mg in m_genres):
                    score += (0.30 - i * 0.08)
                    matched_genre = fg
                    break
            if fav_langs and any(m["language"].lower() == fl.lower() for fl in fav_langs):
                score += 0.20
                matched_lang = m["language"]
            for hg in highly_rated:
                if any(hg.lower() == mg.lower() for mg in m_genres):
                    score += 0.15
                    if not matched_genre:
                        matched_genre = hg
                    break

            if matched_genre and matched_lang:
                reason = f"Because you enjoy {matched_lang} {matched_genre.lower()}s..."
            elif matched_genre:
                reason = f"Because you highly rated {matched_genre.lower()} films..." if matched_genre in highly_rated else f"Because you frequently watch {matched_genre.lower()} movies..."
            elif matched_lang:
                reason = f"Because you frequently watch {matched_lang} films..."

            pre_scored.append({
                "_movie_id": m["id"],
                "_poster_hint": poster,
                "_year": m.get("year"),
                "_lang": lang,
                "id": m["id"],
                "title": title,
                "genre": ", ".join(m_genres) if isinstance(m_genres, list) else str(m_genres),
                "language": lang,
                "region": m["region"],
                "runtime": m["runtime"] or 120,
                "rating": m["rating"] or 0.0,
                "score": score,
                "reason": reason,
                "omdb_plot": m["overview"] or "Plot details are currently unavailable.",
                "omdb_cast": m["cast"] or "",
                "omdb_director": m["director"] or "N/A",
                "omdb_year": m["year"] or "N/A",
                "imdb_rating": str(m["rating"]) if m["rating"] else "N/A",
                "trailer_url": m["trailer_url"] or ""
            })

        # Sort and take top 8 before poster fetching
        pre_scored.sort(key=lambda x: x["score"], reverse=True)
        top8 = pre_scored[:8]

        # Fetch posters in parallel
        from concurrent.futures import ThreadPoolExecutor, as_completed
        def _resolve_poster_p(rec):
            return rec["id"], get_or_download_poster(
                rec["_movie_id"], rec["title"], rec["_poster_hint"],
                year=rec["_year"], language=rec["_lang"]
            )

        poster_map = {}
        with ThreadPoolExecutor(max_workers=min(8, len(top8) or 1)) as pool:
            futures = {pool.submit(_resolve_poster_p, rec): rec for rec in top8}
            for fut in as_completed(futures):
                try:
                    mid, purl = fut.result(timeout=8)
                    poster_map[mid] = purl
                except Exception as fe:
                    rec = futures[fut]
                    print(f"[ERROR] Parallel poster fetch failed for {rec.get('title')}: {fe}")
                    poster_map[rec["id"]] = "/posters/default-poster.jpg"

        scored_candidates = []
        for rec in top8:
            entry = dict(rec)
            entry["omdb_poster"] = poster_map.get(rec["id"], "/posters/default-poster.jpg")
            for k in ("_movie_id", "_poster_hint", "_year", "_lang"):
                entry.pop(k, None)
            scored_candidates.append(entry)

        return jsonify({"success": True, "movies": scored_candidates})
    except Exception as e:
        print(f"[ERROR] api_personalized_recommendations failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": "An unexpected error occurred"}), 500


# =========================================
# REVIEWS & CHATBOT
# =========================================

MOOD_RESPONSES = {
    "sad": [
        "I'm sorry you're feeling down 💙 It's okay to have tough days. Let me suggest something uplifting like '3 Idiots' — it never fails to lift spirits!",
        "Feeling blue? 🥺 That's completely valid. 'Taare Zameen Par' is emotional but so beautiful — sometimes a good cry is exactly what we need.",
        "I hear you, and I'm here for you 💙 How about 'The Pursuit of Happyness'? It's a powerful reminder that tough times don't last forever.",
    ],
    "happy": [
        "That's wonderful to hear! 🎉 Your positive energy is contagious! Keep it going with something fun like 'PK'!",
        "You're happy? Amazing! � Let's match that energy with 'DDLJ' — pure joy on screen!",
        "Love that vibe! � 'Zindagi Na Milegi Dobara' is perfect for celebrating good times!",
    ],
    "bored": [
        "Bored? Let's fix that right now! 😄 'Andhadhun' will keep you on the edge of your seat — you won't be bored for a second!",
        "I won't let you stay bored! 🎬 'Drishyam' is a masterpiece thriller that'll completely captivate you!",
        "Boredom ends here! 🍿 Try 'Kumbalangi Nights' — it's a beautiful blend of comedy and drama that'll engage you instantly!",
    ],
    "stressed": [
        "Take a deep breath with me 😌 You've got this. 'Zindagi Na Milegi Dobara' is literally medicine for stressed souls — it reminds us what matters.",
        "I can feel that stress 🫂 'Tamasha' will help you remember life's beauty. Sometimes we need cinema to help us breathe again.",
        "Stressed is tough, but you're tougher 💪 'The Shawshank Redemption' teaches us that hope is a good thing — maybe the best of things.",
    ],
    "lonely": [
        "You're never truly alone when you have great cinema 🎭 'Dil Chahta Hai' celebrates friendship in the most beautiful way — let it be your companion tonight.",
        "I'm here with you 💙 'Cast Away' might seem lonely, but it's ultimately about human connection and resilience. You'll feel less alone watching it.",
        "Feeling isolated? 🫂 'The Intouchables' is a heartwarming story about an unlikely friendship that'll warm your heart.",
    ],
    "excited": [
        "YESSS that energy!! 🔥 I love it! 'RRR' will absolutely match your enthusiasm — it's pure adrenaline!",
        "Excited? Perfect! ⚡ 'Baahubali' is epic in every sense — get ready for an incredible ride!",
        "Your energy is contagious! 🎉 'Mad Max: Fury Road' will channel that excitement perfectly!",
    ],
    "upset": [
        "I'm sorry something upset you 🥺 Let me help. '3 Idiots' has a way of making everything feel a little lighter — give it a try?",
        "That sounds tough 💙 Sometimes a good movie helps us process emotions. 'Inside Out' is literally about understanding our feelings — it might help.",
        "I hear you, and it's okay to feel upset 🫂 'The Perks of Being a Wallflower' reminds us we're not alone in feeling this way.",
    ],
    "tired": [
        "Long day? You deserve a break ☕🎬 'Chennai Express' is light and fun — perfect for unwinding without thinking too hard.",
        "Exhausted? 😴 'The Princess Bride' is comforting and delightful — like a warm hug for your tired mind.",
        "Time to recharge 🔋 'My Neighbor Totoro' is gentle and soothing — exactly what tired souls need.",
    ],
    "heartbroken": [
        "I'm so sorry 💔 Heartbreak is incredibly hard. 'Eternal Sunshine of the Spotless Mind' explores love and loss beautifully — sometimes art helps us heal.",
        "This too shall pass 🫂 '500 Days of Summer' might be about heartbreak, but it helps us understand and process these feelings.",
        "I'm here for you 💙 'La La Land' acknowledges the pain of lost dreams and love — sometimes we need to sit with those feelings.",
    ],
    "demotivated": [
        "I believe in you 💪 'Rocky' is the ultimate motivation booster — if Rocky can do it, so can you!",
        "Feeling stuck? 🚀 'The Pursuit of Happyness' shows us that resilience pays off. You've got more strength than you know!",
        "Demotivation is temporary 🌟 'Forrest Gump' teaches us that life is full of surprises — keep going, amazing things await!",
    ],
}

EMOTIONAL_KEYWORDS = {
    "sad": ["sad", "depressed", "down", "unhappy", "miserable", "gloomy", "blue", "crying", "tears"],
    "happy": ["happy", "joy", "excited", "great", "amazing", "wonderful", "fantastic", "good", "glad"],
    "bored": ["bored", "boring", "nothing to do", "uninteresting", "dull"],
    "stressed": ["stressed", "stress", "anxious", "worried", "overwhelmed", "pressure", "tense"],
    "lonely": ["lonely", "alone", "isolated", "by myself", "no one", "solitary"],
    "excited": ["excited", "thrilled", "pumped", "energetic", "hyped"],
    "upset": ["upset", "angry", "mad", "furious", "annoyed", "frustrated"],
    "tired": ["tired", "exhausted", "sleepy", "fatigued", "drained", "weary"],
    "heartbroken": ["heartbroken", "heartbreak", "broken heart", "dumped", "rejected", "lost love"],
    "demotivated": ["demotivated", "unmotivated", "giving up", "hopeless", "discouraged"],
}

GREETING_RESPONSES = [
    "Hey there! 🎬 I'm Moumi — your personal cinema companion! How are you feeling today?",
    "Hello, movie lover! 🍿 Ready to discover something amazing? Tell me your mood and I'll find the perfect film!",
    "Hey! 🌟 Welcome back to Mouverse! What kind of movie experience are you in the mood for today?",
    "Hi! 👋 I'm here to help you find your next favorite movie. What's on your mind?",
]

HOW_ARE_YOU_RESPONSES = [
    "I'm running at Oscar-worthy performance! 🏆 How about you — ready for a movie night?",
    "Feeling reel-y great! 🎞️ What genre are you in the mood for?",
    "Living my best cinematic life! 🎬 What's on your watchlist today?",
    "I'm fantastic! Ready to help you discover your next favorite film. What are you in the mood for?",
]

RECOMMEND_PROMPTS = [
    "I'd love to suggest something! 😊 Tell me your mood — happy, sad, bored, excited, stressed?",
    "Great question! 🍿 Pick a mood (happy, romantic, thrilling…) and I'll match you with a gem!",
    "Let me find the perfect movie for you! What are you feeling right now?",
]

TIME_GREETINGS = {
    "morning": ["Good morning", "Morning", "Rise and shine"],
    "afternoon": ["Good afternoon", "Afternoon", "Good day"],
    "evening": ["Good evening", "Evening"],
    "night": ["Good night", "Night", "Late night"],
}

RESTRICTED_TOPICS = [
    'medical advice',
    'legal advice',
    'financial advice',
    'therapy',
    'mental health treatment',
    'diagnosis'
]

RESTRICTED_RESPONSES = {
    'english': "I'm your AI movie companion, not a professional advisor. For medical, legal, or financial matters, please consult a qualified professional. However, I can suggest some comforting films if you'd like! 🎬",
    'bengali': "আমি তোমার সিনেমা সঙ্গী, পেশাদার উপদেষ্টা নই। চিকিৎসা, আইনি বা আর্থিক বিষয়ের জন্য দয়া করে যোগ্য পেশাদারের সাথে পরামর্শ করুন। তবে আমি কিছু আরামদায়ক সিনেমা সাজেস্ট করতে পারি! 🎬",
    'hindi': "मैं आपका AI फिल्म साथी हूं, पेशेवर सलाहकार नहीं। चिकित्सा, कानूनी या वित्तीय मामलों के लिए कृपया योग्य पेशेवर से परामर्श लें। हालांकि, मैं आपको कुछ आरामदायक फिल्में सुझा सकता हूं! 🎬",
    'tamil': "நான் உங்கள் AI திரைப்பட தோழர், தொழில்முறை ஆலோசகர் அல்ல. மருத்துவ, சட்ட அல்லது நிதி விவகாரங்களுக்கு தயவு செய்து தகுதியான தொழில்முறை நிபுணரை அணுகுங்கள். இருப்பினும், நான் சில ஆறுதலான படங்களை பரிந்துரைக்கலாம்! 🎬"
}

def _detect_language(text):
    """Detect text language based on script patterns matching the frontend"""
    text_lower = text.lower()
    if re.search(r"[\u0980-\u09ff]", text_lower):
        return "bengali"
    elif re.search(r"[\u0900-\u097f]", text_lower):
        return "hindi"
    elif re.search(r"[\u0b80-\u0bff]", text_lower):
        return "tamil"
    else:
        return "english"


def _detect_emotion(text):
    """Enhanced emotion detection with multiple keywords per emotion"""
    text_lower = text.lower()
    for emotion, keywords in EMOTIONAL_KEYWORDS.items():
        for keyword in keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", text_lower):
                return emotion
    return None


def _get_time_greeting():
    """Get time-appropriate greeting based on current time"""
    from datetime import datetime
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def _get_formatted_time():
    """Get formatted time with timezone awareness"""
    from datetime import datetime
    try:
        now = datetime.now()
        return now.strftime("%I:%M %p")
    except:
        return "now"


def _get_user_preferences(user_id):
    """Fetch user preferences from database for personalization, searches, clicks, reviews, and history"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Clicks
        c.execute("""
            SELECT m.genre, m.language, COUNT(*) as count
            FROM user_clicks c
            JOIN movies m ON c.movie_id = m.id
            WHERE c.user_id = ?
            GROUP BY m.genre, m.language
        """, (user_id,))
        click_data = c.fetchall()
        
        # Searches
        c.execute("""
            SELECT genre, language, COUNT(*) as count
            FROM user_searches
            WHERE user_id = ?
            GROUP BY genre, language
        """, (user_id,))
        search_data = c.fetchall()
        
        # Watch history
        c.execute("""
            SELECT m.genre, m.language, h.rating_given
            FROM user_history h
            JOIN movies m ON h.movie_id = m.id
            WHERE h.user_id = ?
        """, (user_id,))
        history_data = c.fetchall()
        
        # Reviews
        c.execute("""
            SELECT m.genre, AVG(r.rating) as avg_rating
            FROM reviews r
            JOIN movies m ON r.movie_id = m.id OR LOWER(r.movie_title) = LOWER(m.title)
            WHERE r.user_id = ?
            GROUP BY m.genre
        """, (user_id,))
        review_data = c.fetchall()
        
        conn.close()
        
        genre_scores = {}
        lang_scores = {}
        
        def add_genre_score(genre_name, weight):
            if not genre_name:
                return
            g = genre_name.strip()
            genre_scores[g] = genre_scores.get(g, 0.0) + weight
            
        def add_lang_score(lang_name, weight):
            if not lang_name:
                return
            l = lang_name.strip()
            lang_scores[l] = lang_scores.get(l, 0.0) + weight

        # 1. Process watch history
        for row in history_data:
            g_val = row["genre"]
            genres = json.loads(g_val) if isinstance(g_val, str) and g_val.startswith('[') else ([g_val] if g_val else [])
            rating_mult = 1.0
            if row["rating_given"]:
                rating_mult = row["rating_given"] / 3.0 # rating is 1-5 stars
            for g in genres:
                add_genre_score(g, 3.0 * rating_mult)
            add_lang_score(row["language"], 3.0 * rating_mult)
            
        # 2. Process reviews
        for row in review_data:
            g_val = row["genre"]
            genres = json.loads(g_val) if isinstance(g_val, str) and g_val.startswith('[') else ([g_val] if g_val else [])
            rating_mult = row["avg_rating"] / 5.0
            for g in genres:
                add_genre_score(g, 4.0 * rating_mult)
                
        # 3. Process searches
        for row in search_data:
            if row["genre"]:
                add_genre_score(row["genre"], 1.0 * row["count"])
            if row["language"]:
                add_lang_score(row["language"], 1.0 * row["count"])
                
        # 4. Process clicks
        for row in click_data:
            g_val = row["genre"]
            genres = json.loads(g_val) if isinstance(g_val, str) and g_val.startswith('[') else ([g_val] if g_val else [])
            for g in genres:
                add_genre_score(g, 1.0 * row["count"])
            add_lang_score(row["language"], 1.0 * row["count"])

        sorted_genres = [g for g, _ in sorted(genre_scores.items(), key=lambda x: x[1], reverse=True)]
        sorted_langs = [l for l, _ in sorted(lang_scores.items(), key=lambda x: x[1], reverse=True)]
        
        # Find highly rated genres (avg review rating >= 7)
        highly_rated_genres = []
        for row in review_data:
            if row["avg_rating"] >= 7.0:
                g_val = row["genre"]
                genres = json.loads(g_val) if isinstance(g_val, str) and g_val.startswith('[') else ([g_val] if g_val else [])
                for g in genres:
                    if g not in highly_rated_genres:
                        highly_rated_genres.append(g)

        return {
            "favorite_genres": sorted_genres[:5],
            "favorite_languages": sorted_langs[:3],
            "highly_rated_genres": highly_rated_genres,
            "all_favorite_genres": sorted_genres,
            "all_favorite_languages": sorted_langs
        }
    except Exception as e:
        print(f"[ERROR] Error fetching user preferences: {e}")
        return {
            "favorite_genres": [],
            "favorite_languages": [],
            "highly_rated_genres": [],
            "all_favorite_genres": [],
            "all_favorite_languages": []
        }


def _chatbot_reply(message, mood, region, user_id=None, user_name=None, client_time=None, client_hour=None, timezone=None):
    """Enhanced chatbot with emotional intelligence, time awareness, dynamic recommendations, and personalization"""
    text = (message or "").strip().lower()
    if not text:
        return "Say something — I'm all ears and popcorn! 🍿"

    # Backend safety check for restricted topics
    lang = _detect_language(text)
    for topic in RESTRICTED_TOPICS:
        if topic in text:
            return RESTRICTED_RESPONSES.get(lang, RESTRICTED_RESPONSES['english'])

    # Time queries (detecting local timezone, region, and showing local time)
    if "what time" in text or "current time" in text or "what's the time" in text:
        hour = client_hour
        if hour is None:
            from datetime import datetime
            hour = datetime.now().hour
            
        if 5 <= hour < 12:
            time_period = "morning"
        elif 12 <= hour < 17:
            time_period = "afternoon"
        elif 17 <= hour < 21:
            time_period = "evening"
        else:
            time_period = "night"
            
        time_greetings = TIME_GREETINGS.get(time_period, ["Hello"])
        time_greeting = random.choice(time_greetings)
        
        city = ""
        if timezone:
            parts = timezone.split('/')
            if len(parts) > 1:
                city = parts[-1].replace('_', ' ')
        if not city:
            city = "Kolkata" if (region and region.lower() == "india") else "London"

        formatted_time = client_time
        if not formatted_time:
            from datetime import datetime
            formatted_time = datetime.now().strftime("%I:%M %p")

        greeting_with_name = f" {user_name}" if user_name else ""
        return f"{time_greeting}{greeting_with_name}! 👋 It's currently {formatted_time} in {city}. Perfect time for a movie night! 🍿"

    # Greetings with time awareness
    if any(w in text for w in ("hi", "hello", "hey", "hola", "namaste")):
        hour = client_hour
        if hour is None:
            from datetime import datetime
            hour = datetime.now().hour
            
        if 5 <= hour < 12:
            time_period = "morning"
        elif 12 <= hour < 17:
            time_period = "afternoon"
        elif 17 <= hour < 21:
            time_period = "evening"
        else:
            time_period = "night"
            
        time_greeting = random.choice(TIME_GREETINGS.get(time_period, ["Hello"]))
        greeting_with_name = f" {user_name}" if user_name else ""
        base_greeting = random.choice(GREETING_RESPONSES)
        if "!" in base_greeting:
            base_greeting = base_greeting.split('!')[1].strip()
        return f"{time_greeting}{greeting_with_name}! 👋 {base_greeting}"

    # How are you
    if "how are you" in text or "how r u" in text:
        return random.choice(HOW_ARE_YOU_RESPONSES)



    # Emotional intelligence and Empathetic responses (Sad, Lonely, Stressed, Heartbroken, Demotivated, Feeling low)
    detected_emotion = _detect_emotion(text)
    emotional_states = ["sad", "lonely", "stressed", "heartbroken", "demotivated", "feeling low", "upset", "tired"]
    is_emotional = False
    for state in emotional_states:
        if state in text or (detected_emotion == state):
            detected_emotion = state
            is_emotional = True
            break
            
    if is_emotional:
        empathy_texts = {
            "sad": "I'm so sorry you're feeling down 💙 It's okay to have tough days. Let's find an uplifting film to bring a little comfort to your evening.",
            "lonely": "I hear you, and it's completely okay to feel lonely 🫂 Great cinema is a wonderful companion, and I'd love to suggest something heartwarming to keep you company.",
            "stressed": "Take a deep breath with me 😌 You've got this. Let's find something relaxing and light to help you unwind and destress.",
            "heartbroken": "I'm so incredibly sorry 💔 Heartbreak is one of the hardest things to go through. Let's find a comforting film that acknowledges these feelings or offers a gentle escape.",
            "demotivated": "I believe in you 💪 We all hit slumps, but they are temporary. Let's look at some highly motivational films to help spark that inner drive again!",
            "feeling low": "I'm sending you a big hug 🫂 It's perfectly fine to feel low. I'd love to recommend a warm, feel-good movie that never fails to lift spirits.",
            "upset": "I'm sorry something has upset you 🥺 Let me recommend something light and absorbing to give your mind a gentle break.",
            "tired": "It sounds like you've had a long day 😴 You deserve a nice, cozy rest. Let's pick a comforting, easy-to-watch movie to help you recharge."
        }
        
        empathy_msg = empathy_texts.get(detected_emotion, "I hear you, and I'm here for you 💙 Let's find a movie that matches what you need right now.")
        
        genre_mapping = {
            "sad": ["Comedy", "Family"],
            "lonely": ["Comedy", "Drama"],
            "stressed": ["Comedy", "Romance", "Fantasy"],
            "heartbroken": ["Romance", "Comedy"],
            "demotivated": ["Biography", "Sport", "Drama"],
            "feeling low": ["Comedy", "Family"],
            "upset": ["Comedy", "Adventure"],
            "tired": ["Comedy", "Animation"]
        }
        
        target_genres = genre_mapping.get(detected_emotion, ["Comedy"])
        suggested_movies = []
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM movies WHERE region = ? OR region = 'International' LIMIT 50", (region or "International",))
            movies = [dict(row) for row in c.fetchall()]
            conn.close()
            
            for m in movies:
                try:
                    m_genres = json.loads(m["genre"]) if isinstance(m["genre"], str) and m["genre"].startswith('[') else ([m["genre"]] if m["genre"] else [])
                except:
                    m_genres = []
                if any(tg.lower() == mg.lower() for tg in target_genres for mg in m_genres):
                    suggested_movies.append(m)
        except Exception as query_err:
            print(f"[ERROR] Chatbot failed querying movies: {query_err}")
            
        if suggested_movies:
            selected = random.sample(suggested_movies, min(2, len(suggested_movies)))
        else:
            selected = [{"title": "3 Idiots", "overview": "A wonderful comedy about friendship and life goals."}, {"title": "Zindagi Na Milegi Dobara", "overview": "A beautiful road trip film celebrating life and friendship."}]

        rec_details = []
        for sm in selected:
            explanation = ""
            if detected_emotion in ["sad", "feeling low", "upset"]:
                explanation = "it's a lighthearted comedy that is sure to bring a smile to your face"
            elif detected_emotion == "lonely":
                explanation = "it features a beautiful story of friendship and human connection to keep you company"
            elif detected_emotion == "stressed":
                explanation = "it is a relaxing, comforting watch to help you escape and unwind"
            elif detected_emotion == "heartbroken":
                explanation = "it offers a gentle and comforting story of healing and love"
            elif detected_emotion == "demotivated":
                explanation = "it is an incredibly inspiring story that will help boost your motivation"
            else:
                explanation = "it is a wonderful feel-good movie"
                
            rec_details.append(f"• *{sm['title']}* — I recommend this because {explanation}.")

        rec_str = "\n".join(rec_details)
        therapist_disclaimer = "\n\n*Please note: I am always here to chat and recommend movies, but remember I'm just an AI movie assistant, not a professional therapist. If you're going through a tough time, don't hesitate to reach out to loved ones or a professional.* 💙"
        
        return f"{empathy_msg}\n\nHere are some movies I think might help:\n{rec_str}{therapist_disclaimer}"

    # Genre recommendations with personalization and database search
    genre_words = {
        "action": "Action",
        "comedy": "Comedy",
        "romance": "Romance",
        "thriller": "Thriller",
        "horror": "Horror",
        "sci-fi": "Sci-Fi",
        "drama": "Drama",
        "animation": "Animation",
    }
    detected_genre = None
    for kw, genre_name in genre_words.items():
        if kw in text:
            detected_genre = genre_name
            break

    if detected_genre:
        target_region = region or "International"
        suggested_movies = []
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute(
                "SELECT * FROM movies WHERE region = ? OR region = 'International' LIMIT 100", 
                (target_region,)
            )
            movies = [dict(row) for row in c.fetchall()]
            conn.close()
            
            for m in movies:
                try:
                    m_genres = json.loads(m["genre"]) if isinstance(m["genre"], str) and m["genre"].startswith('[') else ([m["genre"]] if m["genre"] else [])
                except:
                    m_genres = []
                if any(detected_genre.lower() == mg.lower() for mg in m_genres):
                    suggested_movies.append(m)
        except Exception as query_err:
            print(f"[ERROR] Chatbot failed querying genre movies: {query_err}")

        # Sort top-rated first
        suggested_movies.sort(key=lambda m: m.get("rating") or 0.0, reverse=True)

        if suggested_movies:
            selected = suggested_movies[:3]
            rec_details = []
            for sm in selected:
                rating = f" (Rating: {sm['rating']}/10)" if sm.get('rating') else ""
                rec_details.append(f"• *{sm['title']}*{rating} — {sm.get('overview') or 'A great film to watch.'}")
            rec_str = "\n".join(rec_details)
            
            pref_msg = ""
            if user_id:
                prefs = _get_user_preferences(user_id)
                if detected_genre in prefs.get("favorite_genres", []):
                    pref_msg = f"Since you frequently watch {detected_genre.lower()} movies, I "
                else:
                    pref_msg = "I "
            else:
                pref_msg = "I "
                
            return f"Great taste! 🎬 {pref_msg}found some top-rated *{detected_genre}* movies in your region:\n\n{rec_str}"
        else:
            # Fallback
            fallback_replies = {
                "action": "Try 'Baahubali' or 'Sholay' for epic action in your region!",
                "comedy": "'3 Idiots' and 'PK' are comedy gold — perfect for a laugh! 😂",
                "romance": "'DDLJ' is the ultimate romance — still unbeatable! ❤️",
                "thriller": "'Andhadhun' and 'Drishyam' will keep you on the edge! 😱",
                "horror": "For chills, 'Tumbbad' delivers atmosphere and scares! 👻",
                "sci-fi": "'Inception' bends minds beautifully — a must-watch! 🚀",
                "drama": "'Pather Panchali' is a masterpiece of Indian cinema — deeply moving.",
                "animation": "'Spirited Away' is magical — perfect for any mood!",
            }
            reply = fallback_replies.get(detected_genre.lower(), "Enjoy the show!")
            if user_id:
                prefs = _get_user_preferences(user_id)
                if detected_genre in prefs.get("favorite_genres", []):
                    return f"Great taste! 🎬 Since you love {detected_genre.lower()} films, {reply}"
            return f"Great taste! 🎬 {reply}"
    # Generic recommendation requests
    if any(w in text for w in ("suggest", "recommend", "what to watch", "pick a movie")):
        if user_id:
            prefs = _get_user_preferences(user_id)
            if prefs.get("favorite_genres"):
                genre = prefs["favorite_genres"][0]
                return f"I'd love to suggest something! 😊 Since you enjoy {genre} films, tell me your current mood and I'll find the perfect match!"
        return random.choice(RECOMMEND_PROMPTS)

    # Thank you
    if "thank" in text:
        return "Anytime! 🍿 Enjoy the show — I'm here whenever you need another pick!"

    # Region-aware response
    if region:
        return (
            f"I'm here for you in {region}! 🌍 Tell me if you're feeling happy, sad, bored, "
            "stressed, lonely, demotivated, or heartbroken — or ask for a genre like action, comedy, or romance!"
        )
    return (
        "I'm here to help! 🎬 Tell me your mood (happy, sad, excited, lonely, demotivated…) or ask for a genre — "
        "I'll find something perfect for you!"
    )


@app.route("/submit-review", methods=["POST"])
@csrf.exempt
@login_required
def submit_review():
    try:
        data = request.get_json() or {}

        # Handle helpful count increments separately
        if data.get("helpful_review_id"):
            try:
                review_id = int(data.get("helpful_review_id"))
                if review_id <= 0:
                    return jsonify({"success": False, "error": "Invalid review_id"}), 400
            except (TypeError, ValueError):
                return jsonify({"success": False, "error": "Invalid review_id"}), 400
            
            conn = None
            try:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute(
                    "UPDATE reviews SET helpful_count = helpful_count + 1 WHERE id = ?",
                    (review_id,),
                )
                conn.commit()
                return jsonify({"success": True})
            except sqlite3.Error as db_error:
                print(f"[ERROR] Database error in submit_review (helpful): {db_error}")
                return jsonify({"success": False, "error": "Database error occurred"}), 500
            finally:
                if conn:
                    conn.close()

        # Validate inputs for review submission
        movie_title = validate_string_input(data.get("movie_title", ""), "movie_title", 255)
        if not movie_title:
            return jsonify({"success": False, "error": "Missing or invalid movie_title"}), 400
        
        stars = data.get("stars")
        if stars is None:
            return jsonify({"success": False, "error": "Missing stars"}), 400

        try:
            stars = int(stars)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Invalid star rating"}), 400

        if stars < 1 or stars > 10:
            return jsonify({"success": False, "error": "Stars must be between 1 and 10"}), 400

        review_text = data.get("review_text", "").strip()
        if review_text:
            review_text = validate_string_input(review_text, "review_text", 2000)
        
        region = data.get("region") or session.get("region") or current_user.region
        if region and not validate_region(region):
            region = None
        
        movie_id = data.get("movie_id")
        if movie_id:
            movie_id = validate_string_input(str(movie_id), "movie_id", 100)
        
        review_id = data.get("review_id")
        if review_id:
            try:
                review_id = int(review_id)
            except (TypeError, ValueError):
                return jsonify({"success": False, "error": "Invalid review_id"}), 400

        conn = None
        try:
            conn = get_db_connection()
            c = conn.cursor()
            
            # If movie_id not provided, try to find it from the title
            if not movie_id:
                c.execute("SELECT id FROM movies WHERE LOWER(title) = LOWER(?)", (movie_title,))
                row = c.fetchone()
                if row:
                    movie_id = row["id"]

            if review_id:
                # Edit mode: verify ownership
                c.execute("SELECT user_id FROM reviews WHERE id = ?", (review_id,))
                row = c.fetchone()
                if not row:
                    return jsonify({"success": False, "error": "Review not found"}), 404
                if row["user_id"] != current_user.id:
                    return jsonify({"success": False, "error": "Unauthorized"}), 403

                c.execute(
                    """UPDATE reviews 
                       SET rating = ?, review = ?, region = ?, movie_id = ?
                       WHERE id = ?""",
                    (stars, review_text, region, movie_id, review_id)
                )
            else:
                # Add new review
                c.execute(
                    """INSERT INTO reviews (user_id, movie_title, movie_id, rating, review, region)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (current_user.id, movie_title, movie_id, stars, review_text, region),
                )
            
            conn.commit()
            
            # Clear recommendation caches
            keys_to_remove = [k for k in list(session.keys()) if k.startswith("recs_")]
            for k in keys_to_remove:
                session.pop(k, None)
            
            print("[DEBUG] Review Saved Successfully")
            return jsonify({"success": True})
        except sqlite3.Error as db_error:
            print(f"[ERROR] Database error in submit_review: {db_error}")
            return jsonify({"success": False, "error": "Database error occurred"}), 500
        finally:
            if conn:
                conn.close()
    except ValueError as ve:
        print(f"[WARNING] Invalid input in submit_review: {ve}")
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        print(f"[ERROR] submit_review failed: {e}")
        return jsonify({"success": False, "error": "An unexpected error occurred"}), 500


@app.route("/get-reviews", methods=["GET"])
@login_required
def get_reviews():
    try:
        title = validate_string_input(request.args.get("title", ""), "title", 255)
        if not title:
            return jsonify({"success": False, "error": "Missing or invalid title parameter"}), 400

        region = (request.args.get("region") or session.get("region") or current_user.region or "").strip()
        
        # Pagination parameters
        try:
            page = int(request.args.get("page", 1))
            per_page = min(int(request.args.get("per_page", 20)), 100)  # Max 100 per page
            if page < 1 or per_page < 1:
                page, per_page = 1, 20
        except (TypeError, ValueError):
            page, per_page = 1, 20
        
        offset = (page - 1) * per_page

        conn = None
        try:
            conn = get_db_connection()
            c = conn.cursor()
            
            # Get total count
            c.execute(
                "SELECT COUNT(*) as count FROM reviews WHERE LOWER(movie_title) = LOWER(?) OR movie_id = ?",
                (title, title),
            )
            total_count = c.fetchone()["count"]
            
            # Get paginated results
            c.execute(
                """
                SELECT r.*, u.name AS user_name
                FROM reviews r
                LEFT JOIN users u ON r.user_id = u.id
                WHERE LOWER(r.movie_title) = LOWER(?) OR r.movie_id = ?
                ORDER BY
                    CASE WHEN r.region = ? THEN 0 ELSE 1 END,
                    r.created_at DESC
                LIMIT ? OFFSET ?
                """,
                (title, title, region, per_page, offset),
            )
            rows = c.fetchall()
        except sqlite3.Error as db_error:
            print(f"[ERROR] Database error in get_reviews: {db_error}")
            return jsonify({"success": False, "error": "Database error occurred"}), 500
        finally:
            if conn:
                conn.close()

        reviews = []
        total_stars = 0
        for row in rows:
            try:
                reviews.append({
                    "id": row["id"],
                    "user_id": row["user_id"],
                    "user_name": row["user_name"] if row["user_id"] else (row["reviewer_name"] or "Anonymous"),
                    "movie_title": row["movie_title"],
                    "stars": row["rating"],
                    "review_text": row["review"] or "",
                    "region": row["region"] or "International",
                    "created_at": row["created_at"],
                    "helpful_count": row["helpful_count"] or 0,
                })
                total_stars += row["rating"]
            except Exception as row_error:
                print(f"[WARNING] Error processing review row: {row_error}")
                continue

        avg = round(total_stars / len(reviews), 1) if reviews else 0
        total_pages = (total_count + per_page - 1) // per_page
        
        return jsonify({
            "success": True,
            "reviews": reviews,
            "average_rating": avg,
            "review_count": len(reviews),
            "total_count": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        })
    except ValueError as ve:
        print(f"[WARNING] Invalid input in get_reviews: {ve}")
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        print(f"[ERROR] get_reviews failed: {e}")
        return jsonify({"success": False, "error": "An unexpected error occurred"}), 500


@app.route("/delete-review", methods=["POST"])
@csrf.exempt
@login_required
def delete_review():
    try:
        data = request.get_json() or {}
        review_id = data.get("review_id")
        if not review_id:
            return jsonify({"success": False, "error": "Missing review_id"}), 400

        conn = get_db_connection()
        c = conn.cursor()
        try:
            # Check ownership
            c.execute("SELECT user_id FROM reviews WHERE id = ?", (review_id,))
            row = c.fetchone()
            if not row:
                conn.close()
                return jsonify({"success": False, "error": "Review not found"}), 404
            if row["user_id"] != current_user.id:
                conn.close()
                return jsonify({"success": False, "error": "Unauthorized"}), 403

            c.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
            conn.commit()
            
            # Clear recommendation caches
            keys_to_remove = [k for k in list(session.keys()) if k.startswith("recs_")]
            for k in keys_to_remove:
                session.pop(k, None)
            
            conn.close()
            return jsonify({"success": True})
        except sqlite3.Error as db_error:
            conn.close()
            print(f"[ERROR] Database error in delete_review: {db_error}")
            return jsonify({"success": False, "error": "Database error occurred"}), 500
    except Exception as e:
        print(f"[ERROR] delete_review failed: {e}")
        return jsonify({"success": False, "error": "An unexpected error occurred"}), 500


@app.route("/chatbot", methods=["POST"])
@csrf.exempt
@login_required
@rate_limit_chatbot
def chatbot():
    try:
        data = request.get_json() or {}
        message = validate_string_input(data.get("message", ""), "message", 500)
        if not message:
            return jsonify({"success": False, "error": "Message cannot be empty"}), 400
        
        mood = data.get("mood", "")
        if mood:
            mood = validate_string_input(mood, "mood", 50)
        
        region = data.get("region") or session.get("region") or current_user.region
        if region and not validate_region(region):
            region = None
        
        user_id = current_user.id
        user_name = getattr(current_user, 'name', None)
        if user_name:
            user_name = validate_string_input(user_name, "name", 100)
        
        client_time = data.get("client_time")
        client_hour = data.get("client_hour")
        if client_hour is not None:
            try:
                client_hour = int(client_hour)
            except (TypeError, ValueError):
                client_hour = None
        timezone = data.get("timezone")
        if timezone:
            timezone = validate_string_input(timezone, "timezone", 100)
        
        reply = _chatbot_reply(
            message, 
            mood, 
            region, 
            user_id=user_id, 
            user_name=user_name,
            client_time=client_time,
            client_hour=client_hour,
            timezone=timezone
        )
        return jsonify({"reply": reply})
    except ValueError as ve:
        print(f"[WARNING] Invalid input in chatbot: {ve}")
        return jsonify({"reply": "Sorry, I couldn't understand that. Could you rephrase? 🤔"}), 400
    except Exception as e:
        print(f"[ERROR] chatbot failed: {e}")
        return jsonify({"reply": "I'm having a little trouble right now. Please try again! 🍿"}), 500


@app.route("/api/debug/otp")
def debug_otp():
    dev_mode_env = os.getenv("DEV_MODE", "false").lower() == "true"
    if not app.debug and not dev_mode_env:
        return jsonify({
            "success": False, 
            "error": "Access denied: Debug endpoint disabled in production",
            "dev_mode": False
        }), 403
        
    email = session.get("pending_verification_email")
    if not email:
        return jsonify({"success": False, "error": "No pending email verification"}), 404
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT otp_code, expires_at FROM otp_verification WHERE email = ? ORDER BY id DESC LIMIT 1",
        (email,)
    )
    row = c.fetchone()
    conn.close()
    
    if row:
        expires_at_str = row["expires_at"]
        try:
            expires_at_dt = datetime.strptime(expires_at_str, "%Y-%m-%d %H:%M:%S")
            created_at_dt = expires_at_dt - timedelta(minutes=5)
            created_at_str = created_at_dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            created_at_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            expires_at_dt = datetime.now() + timedelta(minutes=5)
            expires_at_str = expires_at_dt.strftime("%Y-%m-%d %H:%M:%S")
            
        now = datetime.now()
        if now > expires_at_dt:
            status = "Expired"
        else:
            status = "Pending Verification"
            
        dev_mode_env = os.getenv("DEV_MODE", "false").lower() == "true"
        
        return jsonify({
            "success": True, 
            "otp": row["otp_code"],
            "created_at": created_at_str,
            "expires_at": expires_at_str,
            "status": status,
            "dev_mode": dev_mode_env
        })
    return jsonify({"success": False, "error": "No OTP found"}), 404


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1") or \
                 os.getenv("FLASK_ENV", "").lower() == "development" or \
                 os.getenv("DEBUG", "false").lower() in ("true", "1")
    app.run(debug=debug_mode)