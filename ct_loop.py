import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
from datetime import datetime, timezone, timedelta
from firebase_admin import credentials, firestore
import firebase_admin

# ══════════════════════════════════════════════════════════════════════
# CONTINUOUS TRAINING LOOP (CT)
# ══════════════════════════════════════════════════════════════════════
# This script represents the "Continuous Training" component of MLOps.
# It queries Firebase for profiles where the human Admin OVERRODE the AI.
# It extracts the posts, applies heuristic labels based on the Admin's
# final decision, and appends them to a new training file.

def init_firebase():
    cred_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "devops-82448-firebase-adminsdk-fbsvc-750566db39.json")
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    return firestore.client()

def fetch_admin_overrides():
    db = init_firebase()
    
    # In MLOps, you typically run this as a daily/weekly cron job.
    # We fetch records from the last 7 days.
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    docs = db.collection("analysis_records").stream()
    
    ct_data = []
    
    for doc in docs:
        data = doc.to_dict()
        
        ai_decision = data.get("ai_decision", "").upper()
        admin_decision = data.get("status", "").upper()
        
        # Check if an override happened
        if admin_decision in ["ADMIN_APPROVED", "ADMIN_DECLINED"]:
            # If AI said "REVIEW" but Admin said "APPROVE", it means the posts are "Neither" (Safe)
            if admin_decision == "ADMIN_APPROVED":
                implied_label = 2 # Neither
            else:
                # If Admin declined it, we conservatively mark it as "Offensive" (1)
                # In a real environment, the admin dashboard would explicitly tag which post was bad.
                implied_label = 1
                
            posts = data.get("posts", [])
            for p in posts:
                text = p if isinstance(p, str) else p.get("text", "")
                if len(text.split()) > 3:
                    ct_data.append({
                        "count": 0, "hate_speech": 0, "offensive_language": 0, "neither": 0,
                        "class": implied_label,
                        "tweet": text,
                        "source": "admin_override"
                    })

    if not ct_data:
        print("No new overrides found. No retraining needed.")
        return False
        
    new_df = pd.DataFrame(ct_data)
    
    # Save to a staging file before merging with labeled_data.csv
    staging_file = "human_overrides_staging.csv"
    new_df.to_csv(staging_file, index=False)
    
    print(f"Extracted {len(new_df)} posts from Admin overrides.")
    print(f"Saved to {staging_file}.")
    print("In a fully automated CT pipeline, this would now append to labeled_data.csv and trigger model1.py")
    return True

if __name__ == "__main__":
    print("Running Continuous Training (CT) Data Extraction Loop...")
    fetch_admin_overrides()
