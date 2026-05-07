import pandas as pd
import numpy as np
import re
from datetime import datetime
from textblob import TextBlob
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
import nltk
from nltk.corpus import stopwords

# Download stopwords if not already present
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

def clean_text(text):
    """
    Clean text: lowercase, remove URLs, mentions, special characters
    """
    if not isinstance(text, str):
        return ""
    
    # Lowercase
    text = text.lower()
    # Remove URLs
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    # Remove mentions (@user)
    text = re.sub(r'@\w+', '', text)
    # Remove hashtags (#hashtag) - keeping the word but removing the #
    text = re.sub(r'#', '', text)
    # Remove special characters and numbers
    text = re.sub(r'[^a-z\s]', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def get_sentiment(text):
    """
    Compute sentiment score using TextBlob
    """
    return TextBlob(text).sentiment.polarity

def preprocess_data(df, is_training=True, tfidf_vectorizer=None, scaler=None):
    """
    Apply preprocessing and feature engineering
    """
    df = df.copy()
    
    # 1. Drop unnecessary columns
    drop_cols = ['User ID', 'Username', 'Location', 'Hashtags', 'Bot Label']
    df = df.drop(columns=[col for col in drop_cols if col in df.columns])
    
    # 2. Handle missing values
    # For numeric columns -> fill with median
    numeric_cols = ['Retweet Count', 'Mention Count', 'Follower Count']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].fillna(df[col].median() if is_training else 0)
            
    # For text (Tweet) -> fill with empty string
    if 'Tweet' in df.columns:
        df['Tweet'] = df['Tweet'].fillna("")
        
    # 3. Convert Created At into useful features
    if 'Created At' in df.columns:
        df['Created At'] = pd.to_datetime(df['Created At'])
        current_date = datetime.now()
        df['account_age_days'] = (current_date - df['Created At']).dt.days
        # Ensure age is not negative (in case of future dates in data)
        df['account_age_days'] = df['account_age_days'].clip(lower=0)
        df = df.drop(columns=['Created At'])
    
    # 4. Convert Verified Boolean to integer
    if 'Verified' in df.columns:
        df['Verified'] = df['Verified'].astype(int)
        
    # 5. Text Features (Tweet column)
    if 'Tweet' in df.columns:
        df['clean_tweet'] = df['Tweet'].apply(clean_text)
        df['sentiment_score'] = df['clean_tweet'].apply(get_sentiment)
        
        # TF-IDF Vectorization
        if is_training:
            tfidf_vectorizer = TfidfVectorizer(max_features=5000, stop_words='english')
            tfidf_matrix = tfidf_vectorizer.fit_transform(df['clean_tweet'])
        else:
            if tfidf_vectorizer is None:
                raise ValueError("tfidf_vectorizer must be provided for non-training data")
            tfidf_matrix = tfidf_vectorizer.transform(df['clean_tweet'])
            
        tfidf_df = pd.DataFrame(tfidf_matrix.toarray(), 
                                columns=tfidf_vectorizer.get_feature_names_out(),
                                index=df.index)
        
        # Combine with other features
        df = pd.concat([df, tfidf_df], axis=1)
        df = df.drop(columns=['Tweet', 'clean_tweet'])

    # 6. Normalize numeric features
    features_to_scale = ['Retweet Count', 'Mention Count', 'Follower Count', 'account_age_days', 'sentiment_score', 'Verified']
    features_to_scale = [f for f in features_to_scale if f in df.columns]
    
    if is_training:
        scaler = StandardScaler()
        df[features_to_scale] = scaler.fit_transform(df[features_to_scale])
    else:
        if scaler is None:
            raise ValueError("scaler must be provided for non-training data")
        df[features_to_scale] = scaler.transform(df[features_to_scale])
        
    return df, tfidf_vectorizer, scaler
