import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import joblib, os

def train_model():
    df = pd.read_csv('database/movies.csv')
    
    df['genre'] = df['genre'].fillna('')
    df['mood_tags'] = df['mood_tags'].fillna('')
    df['language'] = df['language'].fillna('')
    
    # Add overview if it exists, otherwise use empty string
    if 'overview' in df.columns:
        df['overview'] = df['overview'].fillna('')
    else:
        df['overview'] = ''
    
    # Add id column
    df['id'] = range(1, len(df) + 1)
    
    MOOD_MAP = {
      'Action': 'excited thrilling action',
      'Comedy': 'happy funny cheerful',
      'Drama': 'emotional deep moving',
      'Romance': 'romantic love emotional',
      'Thriller': 'thrilled dark suspense',
      'Horror': 'dark scary thrilling',
      'Animation': 'happy funny family',
      'Sci-Fi': 'excited futuristic dark'
    }
    df['mood_tags'] = df['genre'].map(MOOD_MAP).fillna('general')
    
    df['ml_features'] = (
        df['genre'] + ' ' +
        df['mood_tags'] + ' ' +
        df['language'] + ' ' +
        df['overview']
    )
    
    vectorizer = TfidfVectorizer(
        max_features=5000,
        stop_words='english',
        ngram_range=(1,2)
    )
    feature_matrix = vectorizer.fit_transform(df['ml_features'])
    
    os.makedirs('ml_model', exist_ok=True)
    joblib.dump(vectorizer, 'ml_model/vectorizer.pkl')
    joblib.dump(feature_matrix, 'ml_model/feature_matrix.pkl')
    df.to_csv('ml_model/processed_movies.csv', index=False)
    
    print(f"Model trained! Movies: {len(df)}")
    return vectorizer, feature_matrix, df

if __name__ == '__main__':
    train_model()
