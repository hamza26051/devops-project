import pandas as pd
import numpy as np
import re
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
import mlflow
import mlflow.sklearn

def clean_tweet(text):
    """
    Clean tweet text: remove mentions, URLs, special characters, and numbers.
    """
    if not isinstance(text, str):
        return ""
    # Lowercase
    text = text.lower()
    # Remove mentions (@user)
    text = re.sub(r'@\w+', '', text)
    # Remove URLs
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    # Remove hashtags (keep the word)
    text = re.sub(r'#', '', text)
    # Remove special characters and numbers
    text = re.sub(r'[^a-z\s]', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def train_sentiment_model():
    file_path = "training.1600000.processed.noemoticon.csv"
    
    print("Loading Sentiment140 dataset...")
    df = pd.read_csv(file_path, encoding='latin-1', header=None)
    df = df[[0, 5]]
    df.columns = ['label', 'text']
    df['label'] = df['label'].replace(4, 1)
    
    # Increase sample size significantly for better coverage
    print("Sampling dataset (300k tweets)...")
    df_pos = df[df['label'] == 1].sample(150000, random_state=42)
    df_neg = df[df['label'] == 0].sample(150000, random_state=42)
    df = pd.concat([df_pos, df_neg])
    
    print("Cleaning tweets...")
    df['clean_text'] = df['text'].apply(clean_tweet)
    df = df[df['clean_text'].str.len() > 3] # Filter out very short/useless tweets
    
    print(f"Final training set size: {len(df)}")
    
    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        df['clean_text'], df['label'], test_size=0.1, random_state=42, stratify=df['label']
    )
    
    print("Vectorizing text (Enhanced TF-IDF)...")
    # Increase max_features and include up to trigrams
    vectorizer = TfidfVectorizer(
        max_features=50000, 
        stop_words=None, # Keep stop words like 'not', 'no' for sentiment
        ngram_range=(1, 3),
        min_df=2
    )
    X_train = vectorizer.fit_transform(X_train_raw)
    X_test = vectorizer.transform(X_test_raw)
    
    print("Training Enhanced Logistic Regression...")
    # Use balanced class weights and a stronger regularization
    model = LogisticRegression(max_iter=2000, C=0.5, solver='saga', n_jobs=-1)
    
    mlflow.set_experiment("Traditional_Sentiment_Analysis")
    with mlflow.start_run():
        mlflow.log_params({
            "model_type": "LogisticRegression",
            "max_features": 50000,
            "ngram_range": "(1, 3)",
            "C": 0.5
        })
        
        model.fit(X_train, y_train)
        
        # Evaluation
        print("\nEvaluating model...")
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        print(f"Accuracy: {acc:.4f}")
        mlflow.log_metric("accuracy", acc)
        
        print("\nClassification Report:")
        report = classification_report(y_test, y_pred, target_names=['Negative', 'Positive'])
        print(report)
        
        # Save artifacts
        print("\nSaving model and vectorizer...")
        os.makedirs("models", exist_ok=True)
        joblib.dump(model, "models/sentiment_model.joblib")
        joblib.dump(vectorizer, "models/sentiment_vectorizer.joblib")
        
        # Log to MLflow
        mlflow.sklearn.log_model(model, "sentiment_lr_model")
        mlflow.log_artifact("models/sentiment_vectorizer.joblib")
        
    print("Done!")

    # Interactive Loop
    print("\n" + "="*50)
    print("INTERACTIVE SENTIMENT PREDICTION")
    print("="*50)
    print("Type your tweet below to see the sentiment.")
    print("Type 'quit' or 'exit' to stop.")
    
    while True:
        user_input = input("\nEnter tweet: ")
        if user_input.lower() in ['quit', 'exit']:
            break
            
        cleaned = clean_tweet(user_input)
        if not cleaned:
            print("Please enter some text.")
            continue
            
        vec = vectorizer.transform([cleaned])
        pred = model.predict(vec)[0]
        prob = model.predict_proba(vec)[0]
        
        label = "POSITIVE" if pred == 1 else "NEGATIVE"
        confidence = prob[pred]
        
        print(f"Cleaned Text: {cleaned}")
        print(f"Sentiment: {label} ({confidence:.2%} confidence)")

if __name__ == "__main__":
    train_sentiment_model()
