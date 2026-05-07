import joblib
import pandas as pd
import re

# Use the same cleaning function as used during training
def clean_tweet(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'#', '', text)
    text = re.sub(r'[^a-z\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def test_model():
    # Load artifacts
    try:
        model = joblib.load("models/sentiment_model.joblib")
        vectorizer = joblib.load("models/sentiment_vectorizer.joblib")
    except FileNotFoundError:
        print("Error: Model or vectorizer not found. Please run train_sentiment.py first.")
        return

    # Sample texts for testing
    test_cases = [
        {"text": "I love this new car! It's absolutely amazing.", "expected": "Positive"},
        {"text": "I am so sad today, everything is going wrong.", "expected": "Negative"},
        {"text": "Just finished my coffee. It was okay.", "expected": "Neutral/Ambiguous"},
        {"text": "@lpm962 Righto, I will be there in 5 minutes!", "expected": "Positive/Neutral"},
        {"text": "The service was terrible and the food was cold. Never coming back.", "expected": "Negative"},
        {"text": "What a beautiful day for a walk in the park! #blessed", "expected": "Positive"}
    ]

    print(f"{'Original Tweet':<60} | {'Cleaned Tweet':<40} | {'Prediction':<10} | {'Confidence'}")
    print("-" * 135)

    for case in test_cases:
        original = case["text"]
        cleaned = clean_tweet(original)
        
        # Transform and Predict
        vec = vectorizer.transform([cleaned])
        pred = model.predict(vec)[0]
        prob = model.predict_proba(vec)[0]
        
        label = "Positive" if pred == 1 else "Negative"
        confidence = prob[pred]
        
        print(f"{original[:58]:<60} | {cleaned[:38]:<40} | {label:<10} | {confidence:.2%}")

if __name__ == "__main__":
    test_model()
