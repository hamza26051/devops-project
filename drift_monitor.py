import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.spatial.distance import cosine
import sys
from firebase_admin import credentials, firestore
import firebase_admin

# ══════════════════════════════════════════════════════════════════════
# DATA DRIFT MONITORING
# ══════════════════════════════════════════════════════════════════════
# MLOps requires monitoring if the incoming data distribution has drifted
# away from the data the model was originally trained on.

TRAIN_DATA_PATH = "labeled_data.csv"

def init_firebase():
    cred_path = "devops-82448-firebase-adminsdk-fbsvc-750566db39.json"
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    return firestore.client()

# Fetch REAL incoming production data from Firebase
def get_production_data_real():
    try:
        db = init_firebase()
        docs = db.collection("analysis_records").stream()
        
        prod_texts = []
        for doc in docs:
            data = doc.to_dict()
            posts = data.get("posts", [])
            for p in posts:
                text = p if isinstance(p, str) else p.get("text", "")
                if text and len(text.split()) > 2:
                    prod_texts.append(text)
        return prod_texts
    except Exception as e:
        print(f"Error connecting to Firebase: {e}")
        return []

def check_data_drift():
    print("Loading Training Baseline...")
    try:
        train_df = pd.read_csv(TRAIN_DATA_PATH)
        baseline_texts = train_df["tweet"].sample(5000, random_state=42).tolist()
    except Exception as e:
        print(f"Could not load {TRAIN_DATA_PATH}. Ensure it exists. {e}")
        return
        
    print("Fetching Production Data from Firebase...")
    prod_texts = get_production_data_real()
    
    if len(prod_texts) < 10:
        print(f"Only found {len(prod_texts)} valid posts in production database.")
        print("Not enough data to compute statistically significant drift. Submit more analyses in the UI first!")
        return
    
    print(f"Baseline size: {len(baseline_texts)} | Production sample size: {len(prod_texts)}")
    
    # We will use TF-IDF to extract the top vocabulary of both sets
    # and calculate the Cosine Similarity between their vocabulary frequency vectors.
    # If the similarity drops below a threshold, Concept/Data Drift is detected!
    
    vec = TfidfVectorizer(max_features=5000, stop_words="english")
    
    # Fit on baseline
    vec.fit(baseline_texts)
    
    # Get mean tf-idf vector for baseline
    baseline_matrix = vec.transform(baseline_texts)
    baseline_centroid = np.asarray(baseline_matrix.mean(axis=0)).flatten()
    
    # Get mean tf-idf vector for production
    prod_matrix = vec.transform(prod_texts)
    prod_centroid = np.asarray(prod_matrix.mean(axis=0)).flatten()
    
    # Calculate similarity
    similarity = 1 - cosine(baseline_centroid, prod_centroid)
    
    print("\n" + "="*50)
    print("DATA DRIFT REPORT")
    print("="*50)
    print(f"Cosine Similarity (Baseline vs Production): {similarity:.4f}")
    
    if similarity < 0.20:
        print("🚨 SEVERE DATA DRIFT DETECTED!")
        print("Incoming language has shifted significantly. Vocabulary mismatch.")
        print("Recommendation: Trigger Data Labeling Pipeline and Retrain.")
    elif similarity < 0.50:
        print("⚠️ MODERATE DRIFT DETECTED.")
        print("Monitor model confidence scores closely.")
    else:
        print("✅ NO SIGNIFICANT DRIFT. Data is stable.")

if __name__ == "__main__":
    check_data_drift()
