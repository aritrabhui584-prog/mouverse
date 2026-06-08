import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import joblib
import os

class MovieRecommender:
    def __init__(self):
        self.vectorizer = None
        self.feature_matrix = None
        self.df = None
        self.load_model()
    
    def load_model(self):
        try:
            model_dir = os.path.dirname(os.path.abspath(__file__))
            self.vectorizer = joblib.load(os.path.join(model_dir, 'vectorizer.pkl'))
            self.feature_matrix = joblib.load(os.path.join(model_dir, 'feature_matrix.pkl'))
            self.df = pd.read_csv(os.path.join(model_dir, 'processed_movies.csv'))
            print("ML Model loaded!")
        except:
            print("Model not found. Run train.py first.")
    
    def recommend(self, mood, genre, language, region, min_rating=0, max_runtime=240, n=10):
        if self.vectorizer is None:
            return []
        
        query = f"{mood} {genre} {language}"
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.feature_matrix)[0]
        
        self.df['ml_score'] = scores
        
        REGION_LANGS = {
          'India': ['Hindi','Bengali','Tamil','Telugu','Marathi','Malayalam','Kannada','English','Urdu'],
          'USA': ['English','Spanish'],
          'UK': ['English'],
          'Korea': ['Korean'],
          'Japan': ['Japanese'],
          'Bangladesh': ['Bengali','Urdu'],
          'Pakistan': ['Urdu','Punjabi']
        }
        
        langs = REGION_LANGS.get(region, ['English'])
        
        # Filter by language strictly if specified, otherwise filter only by rating and runtime
        if language:
            filtered = self.df[
              (self.df['language'].str.lower() == language.lower()) &
              (self.df['rating'] >= min_rating) &
              (self.df['runtime'] <= max_runtime)
            ].copy()
        else:
            filtered = self.df[
              (self.df['rating'] >= min_rating) &
              (self.df['runtime'] <= max_runtime)
            ].copy()

        
        # Language boost: same language gets preference but not required
        filtered['lang_boost'] = filtered['language'].isin(langs).astype(int) * 0.2
        
        filtered['final_score'] = (
          filtered['ml_score'] * 0.6 +
          filtered['rating']/10 * 0.2 +
          filtered['lang_boost'] * 0.2
        )
        
        # Always return results even if language doesn't match perfectly
        results = filtered.nlargest(n, 'final_score')
        return results.to_dict('records')
