import os
import re
import json
import requests
import pandas as pd
from dotenv import load_dotenv
from PIL import Image
import io

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Check ml_model directory for processed_movies.csv
CSV_PATH = os.path.join(BASE_DIR, "ml_model", "processed_movies.csv")
if not os.path.exists(CSV_PATH):
    CSV_PATH = os.path.join(BASE_DIR, "database", "processed_movies.csv")

POSTERS_DIR = os.path.join(BASE_DIR, "public", "posters")
CACHE_FILE = os.path.join(POSTERS_DIR, "poster_cache.json")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
if TMDB_API_KEY == "your_tmdb_api_key_here" or not TMDB_API_KEY:
    TMDB_API_KEY = None

OMDB_API_KEY = os.getenv("OMDB_API_KEY")
if OMDB_API_KEY == "your_omdb_api_key_here" or not OMDB_API_KEY:
    OMDB_API_KEY = None
    print("[WARNING] OMDB_API_KEY not configured. Poster downloads will be skipped.")

def normalize_title(title):
    if not title:
        return ""
    normalized = title.lower().strip()
    normalized = re.sub(r'[^a-z0-9]+', '-', normalized)
    normalized = normalized.strip('-')
    return normalized

def compress_and_save(image_bytes, dest_path):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        # Resize to max 500x750 keeping aspect ratio
        img.thumbnail((500, 750), Image.Resampling.LANCZOS)
        img.save(dest_path, format="JPEG", quality=85, optimize=True)
        return True
    except Exception as e:
        print(f"Error compressing image: {e}")
        try:
            with open(dest_path, "wb") as f:
                f.write(image_bytes)
            return True
        except Exception as e2:
            print(f"Error saving raw bytes: {e2}")
            return False

def download_image(url, dest_path):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return compress_and_save(r.content, dest_path)
    except Exception as e:
        print(f"Error downloading image from {url}: {e}")
    return False

def get_poster_url_from_tmdb(title):
    if not TMDB_API_KEY:
        return get_poster_url_from_omdb(title)
        
    url = "https://api.tmdb.org/3/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": title
    }
    try:
        r = requests.get(url, params=params, timeout=5)
        if r.status_code == 200:
            data = r.json()
            results = data.get("results", [])
            if results:
                poster_path = results[0].get("poster_path")
                if poster_path:
                    return f"https://image.tmdb.org/t/p/w500{poster_path}"
    except Exception as e:
        print(f"TMDB search failed for {title}: {e}")
    return get_poster_url_from_omdb(title)

def get_poster_url_from_omdb(title):
    if not OMDB_API_KEY:
        return None
    url = f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&t={title}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get("Response") == "True":
                poster = data.get("Poster")
                if poster and poster != "N/A":
                    return poster
    except Exception as e:
        print(f"OMDb lookup failed for {title}: {e}")
    return None

def main():
    os.makedirs(POSTERS_DIR, exist_ok=True)
    
    # Load existing cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}")
            
    # Load processed movies
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV not found at {CSV_PATH}")
        return
        
    df = pd.read_csv(CSV_PATH)
    titles = df["title"].dropna().unique()
    
    print(f"Starting poster download for {len(titles)} movies...")
    
    for title in titles:
        normalized = normalize_title(title)
        if not normalized:
            continue
            
        filename = f"{normalized}.jpg"
        dest_path = os.path.join(POSTERS_DIR, filename)
        local_path = f"/posters/{filename}"
        
        # Check if already downloaded
        if os.path.exists(dest_path):
            print(f"[CACHE] {title} poster already exists at {local_path}")
            cache[title] = local_path
            continue
            
        # Get poster url
        print(f"[SEARCH] Searching poster for: {title}")
        poster_url = get_poster_url_from_tmdb(title)
        
        if poster_url:
            print(f"[DOWNLOAD] Downloading {poster_url} to {local_path}")
            if download_image(poster_url, dest_path):
                print(f"[SUCCESS] Saved poster for {title}")
                cache[title] = local_path
            else:
                print(f"[FAILED] Download failed for {title}")
        else:
            print(f"[MISSING] No poster found on TMDB/OMDB for {title}")
            
    # Save cache file
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
        print("Poster cache mapping updated successfully.")
    except Exception as e:
        print(f"Error saving cache: {e}")

if __name__ == "__main__":
    main()
