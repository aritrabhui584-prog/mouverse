import pandas as pd
import sqlite3
import os
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "mouverse.db")
CSV_PATH = os.path.join(BASE_DIR, "database", "MOUVERSE_2.csv")
OUTPUT_CSV = os.path.join(BASE_DIR, "database", "movies_extended.csv")

def process_mouverse2():
    """
    Process the large MOUVERSE_2.csv dataset to extract unique movies
    and create an extended movie database that can supplement the main dataset.
    """
    print("Loading MOUVERSE_2.csv (this may take a while due to size)...")
    
    # Read the CSV in chunks to handle large file
    chunk_size = 10000
    movies_data = {}
    
    # Read first chunk to get structure
    df_sample = pd.read_csv(CSV_PATH, nrows=100)
    print(f"Columns found: {df_sample.columns.tolist()}")
    print(f"Sample data:\n{df_sample.head()}")
    
    # Process the full file to extract unique movies
    print("Extracting unique movies from dataset...")
    chunk_count = 0
    total_rows = 0
    
    for chunk in pd.read_csv(CSV_PATH, chunksize=chunk_size):
        chunk_count += 1
        total_rows += len(chunk)
        
        # Extract unique movies from this chunk
        for _, row in chunk.iterrows():
            movie_id = str(row.get('movieId', ''))
            title = row.get('title', '')
            genres = row.get('genres', '')
            
            if movie_id and title and movie_id not in movies_data:
                movies_data[movie_id] = {
                    'movieId': movie_id,
                    'title': title,
                    'genres': genres,
                    'imdbId': row.get('imdbId', ''),
                    'tmdbId': row.get('tmdbId', ''),
                    'avg_rating': 0,
                    'rating_count': 0,
                    'tags': []
                }
        
        # Update ratings and tags
        for _, row in chunk.iterrows():
            movie_id = str(row.get('movieId', ''))
            rating = row.get('rating', 0)
            tag = row.get('tag', '')
            
            if movie_id in movies_data:
                if pd.notna(rating) and rating > 0:
                    movies_data[movie_id]['rating_count'] += 1
                    # Simple average (not weighted, for simplicity)
                    movies_data[movie_id]['avg_rating'] = (
                        (movies_data[movie_id]['avg_rating'] * (movies_data[movie_id]['rating_count'] - 1) + rating) 
                        / movies_data[movie_id]['rating_count']
                    )
                
                if pd.notna(tag) and tag and tag not in movies_data[movie_id]['tags']:
                    movies_data[movie_id]['tags'].append(tag)
        
        if chunk_count % 10 == 0:
            print(f"Processed {chunk_count * chunk_size} rows, found {len(movies_data)} unique movies...")
    
    print(f"Completed! Total rows processed: {total_rows}")
    print(f"Total unique movies found: {len(movies_data)}")
    
    # Convert to DataFrame and save
    movies_list = list(movies_data.values())
    df_movies = pd.DataFrame(movies_list)
    
    # Convert tags list to string for SQLite compatibility
    df_movies['tags'] = df_movies['tags'].apply(lambda x: ','.join(x) if isinstance(x, list) else str(x))
    
    # Save to CSV
    df_movies.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved extended movies to {OUTPUT_CSV}")
    
    # Also create a SQLite database for faster querying
    print("Creating SQLite database for extended movies...")
    conn = sqlite3.connect(DB_PATH)
    
    # Create extended movies table
    df_movies.to_sql('movies_extended', conn, if_exists='replace', index=False)
    
    conn.close()
    print(f"Created movies_extended table in {DB_PATH}")
    
    return df_movies

if __name__ == "__main__":
    process_mouverse2()
