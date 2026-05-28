from flask import Flask, render_template, request
from dotenv import load_dotenv
import pandas as pd
import requests
import os
import sqlite3
import json
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static"
)

# =========================================
# OMDB API & CONFIG
# =========================================

OMDB_API_KEY = os.getenv("OMDB_API_KEY")

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

CSV_PATH = os.path.join(
    BASE_DIR,
    "database",
    "movies.csv"
)

DB_PATH = os.path.join(
    BASE_DIR,
    "database",
    "mouverse.db"
)

# =========================================
# LOAD DATASET
# =========================================

movies_df = pd.read_csv(CSV_PATH)
movies_df = movies_df.fillna("")

# =========================================
# DATABASE CACHE INITIALIZATION
# =========================================

def init_db():
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS movie_cache (
                title TEXT PRIMARY KEY,
                data TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        print("Database cache initialized successfully.")
    except Exception as e:
        print("Database initialization error:", e)

init_db()

# =========================================
# SECURE POSTER URL HANDLER
# =========================================

def secure_poster_url(poster_url):
    """Convert HTTP poster URLs to HTTPS-safe versions"""
    if not poster_url or poster_url == "N/A" or poster_url is None:
        return None
    
    poster_str = str(poster_url).strip()
    
    # Check if it's a valid URL
    if poster_str.startswith("https://"):
        return poster_str
    elif poster_str.startswith("http://"):
        # Convert HTTP to HTTPS for OMDb images
        return poster_str.replace("http://", "https://")
    
    return None

def get_fallback_poster(title, year=""):
    """Generate fallback poster using public APIs and better placeholders"""
    import urllib.parse
    try:
        # Clean title
        safe_title = str(title).strip()
        
        # Word wrap the title into multiple lines of at most 18 characters
        words = safe_title.split()
        lines = []
        current_line = []
        for word in words:
            if len(" ".join(current_line + [word])) <= 18:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
        
        # Limit to maximum 3 lines
        lines = lines[:3]
        
        # Build SVG tspan lines
        tspan_html = ""
        for i, line in enumerate(lines):
            dy = "0" if i == 0 else "18"
            y_attr = "y='360'" if i == 0 else ""
            tspan_html += f"<tspan x='150' {y_attr} dy='{dy}'>{line}</tspan>"
            
        svg_content = f"""<svg xmlns='http://www.w3.org/2000/svg' width='300' height='450'>
<defs>
<linearGradient id='grad' x1='0%' y1='0%' x2='100%' y2='100%'>
<stop offset='0%' style='stop-color:#001a4d;stop-opacity:1' />
<stop offset='100%' style='stop-color:#0f1423;stop-opacity:1' />
</linearGradient>
</defs>
<rect fill='url(#grad)' width='300' height='450'/>
<rect x='20' y='30' width='260' height='260' fill='none' stroke='#00d9ff' stroke-width='2' opacity='0.5'/>
<text x='150' y='160' font-size='32' fill='#00d9ff' text-anchor='middle' font-family='Arial' font-weight='bold'>🎬</text>
<text fill='#00d9ff' text-anchor='middle' font-family='Poppins' font-size='12' font-weight='bold'>
{tspan_html}
</text>
</svg>"""

        # URL-encode the SVG content
        encoded_svg = urllib.parse.quote(svg_content)
        return f"data:image/svg+xml,{encoded_svg}"
    except Exception as e:
        print(f"Fallback poster generation error: {e}")
        return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='450'%3E%3Crect fill='%230f1423' width='300' height='450'/%3E%3Ctext x='150' y='225' font-size='18' fill='%2300d9ff' text-anchor='middle' dominant-baseline='middle' font-family='Arial'%3EMovie Poster%3C/text%3E%3C/svg%3E"

# =========================================
# PARSE GENRE FROM CSV JSON
# =========================================

def parse_genres(genre_string):
    """Parse genre JSON from CSV and extract genre names"""
    if not genre_string or genre_string == "":
        return "Unknown"
    try:
        # If it's a JSON string from CSV, parse it
        if isinstance(genre_string, str) and genre_string.startswith("["):
            genres_data = json.loads(genre_string)
            if isinstance(genres_data, list):
                names = [g.get("name", "") for g in genres_data if isinstance(g, dict)]
                return ", ".join(names) if names else "Unknown"
        return str(genre_string)
    except:
        return str(genre_string) if genre_string else "Unknown"

# =========================================
# FETCH & CACHE MOVIE DETAILS
# =========================================

def get_movie_details(title):
    try:
        url = (
            f"http://www.omdbapi.com/"
            f"?apikey={OMDB_API_KEY}"
            f"&t={title}"
        )
        response = requests.get(
            url,
            timeout=5
        )
        data = response.json()
        return data
    except Exception as e:
        print(f"OMDB Error for '{title}':", e)
        return {}

def get_cached_movie_details(title):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT data FROM movie_cache WHERE title = ?", (title.strip().lower(),))
        row = c.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
    except Exception as e:
        print(f"Database cache read error for '{title}':", e)
    return None

def cache_movie_details(title, data):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO movie_cache (title, data) VALUES (?, ?)", (title.strip().lower(), json.dumps(data)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database cache write error for '{title}':", e)

def fetch_movie_with_cache(title):
    # Check database cache first
    cached = get_cached_movie_details(title)
    if cached is not None:
        return cached
    
    # Otherwise, fetch from OMDB
    data = get_movie_details(title)
    if data and data.get("Response") == "True":
        cache_movie_details(title, data)
    return data

# =========================================
# HOME PAGE
# =========================================

@app.route("/")
def home():
    return render_template(
        "index.html",
        movies=[],
        selected_genre="",
        runtime=150,
        rating=0
    )

# =========================================
# RECOMMENDATION ROUTE
# =========================================

@app.route("/recommend")
def recommend():
    try:
        # =====================================
        # GET FILTER VALUES
        # =====================================
        genre = request.args.get(
            "genre",
            "action"
        ).lower()

        max_runtime = int(
            request.args.get(
                "runtime",
                150
            )
        )

        min_rating = float(
            request.args.get(
                "rating",
                0
            )
        )

        print("Genre:", genre)
        print("Runtime:", max_runtime)
        print("Rating:", min_rating)

        # =====================================
        # MAP GENRE & FILTER
        # =====================================
        # Map "sci-fi" to "science fiction" to match CSV values
        search_genre = "science fiction" if genre == "sci-fi" else genre

        filtered = movies_df[
            movies_df["genres"]
            .astype(str)
            .str.lower()
            .str.contains(search_genre)
        ]

        # =====================================
        # FILTER RUNTIME
        # =====================================
        if "runtime" in filtered.columns:
            filtered["runtime"] = pd.to_numeric(
                filtered["runtime"],
                errors="coerce"
            )
            filtered = filtered[
                filtered["runtime"] <= max_runtime
            ]

        # =====================================
        # FILTER RATING
        # =====================================
        if "vote_average" in filtered.columns:
            filtered["vote_average"] = pd.to_numeric(
                filtered["vote_average"],
                errors="coerce"
            )
            filtered = filtered[
                filtered["vote_average"] >= min_rating
            ]

        # =====================================
        # REMOVE EMPTY TITLES & RANDOMIZE
        # =====================================
        filtered = filtered[
            filtered["title"] != ""
        ]

        filtered = filtered.sample(
            min(len(filtered), 12)
        )

        print("Movies Found:", len(filtered))

        # =====================================
        # PARALLEL FETCH DETAILS
        # =====================================
        titles = [str(movie.get("title", "Unknown")) for _, movie in filtered.iterrows()]
        
        details_list = []
        if titles:
            with ThreadPoolExecutor(max_workers=min(len(titles), 12)) as executor:
                details_list = list(executor.map(fetch_movie_with_cache, titles))

        movies_list = []

        for idx, (_, movie) in enumerate(filtered.iterrows()):
            try:
                title = titles[idx]
                details = details_list[idx]

                poster = details.get("Poster")
                
                # Try to secure the poster URL
                if poster and poster != "N/A":
                    secure_url = secure_poster_url(poster)
                    if secure_url:
                        poster = secure_url
                    else:
                        # If URL format is invalid, use fallback
                        poster = get_fallback_poster(title, details.get("Year", ""))
                else:
                    # OMDB didn't return a poster, use fallback
                    poster = get_fallback_poster(title, details.get("Year", ""))
                
                # Final safety check - ensure we have a valid poster
                if not poster:
                    poster = get_fallback_poster(title, details.get("Year", ""))

                # Parse genre from OMDB or CSV
                omdb_genre = details.get("Genre", "")
                csv_genre = movie.get("genres", "")
                if omdb_genre and omdb_genre != "N/A":
                    genre_display = omdb_genre
                else:
                    genre_display = parse_genres(csv_genre)

                # Clean cast and director
                cast = details.get("Actors", "")
                if not cast or cast == "N/A":
                    cast = "Unknown"
                director = details.get("Director", "")
                if not director or director == "N/A":
                    director = "Unknown"

                movies_list.append({
                    "title": details.get("Title", title),
                    "poster": poster,
                    "year": details.get("Year", movie.get("release_date", "Unknown")),
                    "rating": details.get("imdbRating", movie.get("vote_average", "N/A")),
                    "summary": details.get("Plot", movie.get("overview", "No description available.")),
                    "cast": cast,
                    "director": director,
                    "runtime": details.get("Runtime", f"{movie.get('runtime', 120)} min"),
                    "genre": genre_display,
                    "trailer": f"https://www.youtube.com/results?search_query={title}+official+trailer"
                })
            except Exception as movie_error:
                print("Movie processing error:", movie_error)
                continue

        print("FINAL MOVIES:", len(movies_list))

        return render_template(
            "index.html",
            movies=movies_list,
            selected_genre=genre,
            runtime=max_runtime,
            rating=min_rating
        )

    except Exception as e:
        print("ERROR:", e)
        return render_template(
            "index.html",
            movies=[],
            selected_genre="",
            runtime=150,
            rating=0
        )
if __name__ == "__main__":
    app.run(
        debug=True
    )