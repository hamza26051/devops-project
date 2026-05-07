import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

load_dotenv()

_db = None

def init_firebase():
    global _db
    if _db is not None:
        return _db

    # Try loading from JSON string (convenient for cloud ENV vars)
    json_str = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if json_str:
        try:
            import json
            cred_dict = json.loads(json_str)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            _db = firestore.client()
            print("Firebase initialized successfully from JSON string")
            return _db
        except Exception as e:
            print(f"ERROR initializing Firebase from JSON string: {e}")
            # Fall back to file path if JSON string failed

    cred_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "devops-82448-firebase-adminsdk-fbsvc-750566db39.json")

    if not os.path.exists(cred_path):
        print(f"WARNING: Firebase service account key not found at {cred_path}")
        print("Firebase features will be unavailable. Create a Firebase project,")
        print("go to Project Settings > Service Accounts > Generate new private key,")
        print("and save the JSON as devops-82448-firebase-adminsdk-fbsvc-750566db39.json in the project root.")
        return None

    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        _db = firestore.client()
        print("Firebase initialized successfully from file")
        return _db
    except Exception as e:
        print(f"ERROR initializing Firebase from file: {e}")
        return None

def get_db():
    global _db
    if _db is None:
        _db = init_firebase()
    return _db


# ── Analysis Records ───────────────────────────────────────────────

def create_analysis_record(data: Dict[str, Any]) -> Optional[str]:
    db = get_db()
    if db is None:
        return None
    try:
        doc_ref = db.collection("analysis_records").document()
        record_id = doc_ref.id
        data["id"] = record_id
        data["created_at"] = firestore.SERVER_TIMESTAMP
        data["updated_at"] = firestore.SERVER_TIMESTAMP
        doc_ref.set(data)
        return record_id
    except Exception as e:
        print(f"Error creating analysis record: {e}")
        return None

def get_all_records() -> List[Dict[str, Any]]:
    db = get_db()
    if db is None:
        return []
    try:
        docs = (
            db.collection("analysis_records")
            .stream()
        )
        records = [doc.to_dict() for doc in docs]
        records.sort(key=lambda x: x.get("created_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return records
    except Exception as e:
        print(f"Error fetching records: {e}")
        return []

def get_record(record_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    if db is None:
        return None
    try:
        doc = db.collection("analysis_records").document(record_id).get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"Error fetching record: {e}")
        return None

def get_record_by_result_id(result_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    if db is None:
        return None
    try:
        docs = (
            db.collection("analysis_records")
            .where("frontend_result_id", "==", result_id)
            .limit(1)
            .stream()
        )
        for doc in docs:
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"Error fetching record by result_id: {e}")
        return None

def update_record(record_id: str, updates: Dict[str, Any]) -> bool:
    db = get_db()
    if db is None:
        return False
    try:
        updates["updated_at"] = firestore.SERVER_TIMESTAMP
        db.collection("analysis_records").document(record_id).update(updates)
        return True
    except Exception as e:
        print(f"Error updating record: {e}")
        return False

def get_user_records(user_id: str) -> List[Dict[str, Any]]:
    db = get_db()
    if db is None:
        return []
    try:
        docs = (
            db.collection("analysis_records")
            .where("user_id", "==", user_id)
            .stream()
        )
        records = [doc.to_dict() for doc in docs]
        records.sort(key=lambda x: x.get("created_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return records
    except Exception as e:
        print(f"Error fetching user records: {e}")
        return []


# ── Notifications ──────────────────────────────────────────────────

def create_notification(data: Dict[str, Any]) -> Optional[str]:
    db = get_db()
    if db is None:
        return None
    try:
        doc_ref = db.collection("notifications").document()
        notif_id = doc_ref.id
        data["id"] = notif_id
        data["created_at"] = firestore.SERVER_TIMESTAMP
        data["read"] = False
        doc_ref.set(data)
        return notif_id
    except Exception as e:
        print(f"Error creating notification: {e}")
        return None

def get_user_notifications(user_id: str) -> List[Dict[str, Any]]:
    db = get_db()
    if db is None:
        return []
    try:
        docs = (
            db.collection("notifications")
            .where("user_id", "==", user_id)
            .stream()
        )
        notifs = [doc.to_dict() for doc in docs]
        notifs.sort(key=lambda x: x.get("created_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return notifs
    except Exception as e:
        print(f"Error fetching notifications: {e}")
        return []

def mark_notification_read(notification_id: str) -> bool:
    db = get_db()
    if db is None:
        return False
    try:
        db.collection("notifications").document(notification_id).update({"read": True})
        return True
    except Exception as e:
        print(f"Error marking notification read: {e}")
        return False

def get_unread_count(user_id: str) -> int:
    db = get_db()
    if db is None:
        return 0
    try:
        docs = (
            db.collection("notifications")
            .where("user_id", "==", user_id)
            .where("read", "==", False)
            .stream()
        )
        return len(list(docs))
    except Exception as e:
        print(f"Error counting notifications: {e}")
        return 0
# ── Human Overrides & Feedback Loop ──────────────────────────────────

def submit_human_override(data: Dict[str, Any]) -> Optional[str]:
    """
    Submits a human override to Firestore. 
    Expected data: {tweet: str, class: int, source: str}
    """
    db = get_db()
    if db is None: return None
    try:
        doc_ref = db.collection("human_overrides").document()
        data["id"] = doc_ref.id
        data["created_at"] = firestore.SERVER_TIMESTAMP
        doc_ref.set(data)
        return doc_ref.id
    except Exception as e:
        print(f"Error submitting override: {e}")
        return None

def get_recent_overrides(limit: int = 100) -> List[Dict[str, Any]]:
    """Fetches recent overrides for retraining or reference."""
    db = get_db()
    if db is None: return []
    try:
        docs = (
            db.collection("human_overrides")
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print(f"Error fetching overrides: {e}")
        return []

def check_for_override(text: str) -> Optional[int]:
    """
    Checks if a specific text has a human override.
    This is useful for 'fixing' known misclassifications instantly.
    """
    db = get_db()
    if db is None: return None
    try:
        # Note: In production, you'd use a hash or normalized text for lookup
        docs = (
            db.collection("human_overrides")
            .where("tweet", "==", text)
            .limit(1)
            .stream()
        )
        for doc in docs:
            return doc.to_dict().get("class")
        return None
    except Exception as e:
        print(f"Error checking override: {e}")
        return None
