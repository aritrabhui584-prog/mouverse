import pandas as pd
import csv

# Try to read the CSV with different approaches to understand its structure
file_path = r"c:\Users\aritr\OneDrive\Desktop\mouverse-AI\database\MOUVERSE_2.csv"

# First, let's read just the raw lines to understand the format
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()[:20]

print("Raw first 20 lines:")
for i, line in enumerate(lines[:20]):
    print(f"Line {i}: {line[:200]}")  # Print first 200 chars of each line

print("\n" + "="*80 + "\n")

# Try to detect the actual delimiter and structure
print("Attempting to parse with different delimiters...")

# Try comma delimiter
try:
    df = pd.read_csv(file_path, nrows=5, on_bad_lines='skip')
    print("Comma delimiter - Columns:", df.columns.tolist())
    print("First row:", df.iloc[0].tolist() if len(df) > 0 else "No data")
except Exception as e:
    print(f"Comma delimiter failed: {e}")

print("\n" + "="*80 + "\n")

# The file seems to have a complex structure. Let's analyze it manually.
# It appears to be a combination of movie info, ratings, and tags.
# Let's extract unique movies first.

print("Extracting unique movie information...")
unique_movies = {}
with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        # Look for lines that start with a number (movieId)
        if line.strip() and line[0].isdigit():
            parts = line.split(',')
            if len(parts) >= 3:
                movie_id = parts[0].strip()
                title = parts[1].strip()
                genres = parts[2].strip() if len(parts) > 2 else ""
                if movie_id and title and movie_id not in unique_movies:
                    unique_movies[movie_id] = {
                        'movieId': movie_id,
                        'title': title,
                        'genres': genres
                    }
                if len(unique_movies) >= 10:
                    break

print(f"Found {len(unique_movies)} sample movies:")
for movie_id, movie in list(unique_movies.items())[:5]:
    print(f"  {movie_id}: {movie['title']} - {movie['genres']}")
