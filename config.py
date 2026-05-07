import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App General
    APP_NAME: str = "VeriDrive-Inference"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = False
    FRONTEND_URL: str = "http://localhost:8081" # Default for many TanStack Start templates
    
    # Auth
    JWT_SECRET: str = "veridrive-secret-key-change-me"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "fast1234"
    
    # Mastodon
    MASTODON_INSTANCE: str = "https://mastodon.social"
    MASTODON_CLIENT_ID: str = ""
    MASTODON_CLIENT_SECRET: str = ""
    MASTODON_REDIRECT_URI: str = "http://localhost:8000/auth/mastodon/callback"
    
    # ML Models
    MODEL_MODE: str = "TRANSFORMERS"  # Default to Transformers as requested
    TOX_MODEL_PATH: str = "toxicity_model_v3.pkl"
    SENT_MODEL_PATH: str = "models/sentiment_model.joblib"
    SENT_VEC_PATH: str = "models/sentiment_vectorizer.joblib"
    TRANSFORMER_MODEL_PATH: str = "./sentiment_model"
    
    # MLflow
    MLFLOW_TRACKING_URI: Optional[str] = None
    MLFLOW_MODEL_ALIAS: str = "Production"
    
    # Firebase
    FIREBASE_SERVICE_ACCOUNT: str = "devops-82448-firebase-adminsdk-fbsvc-750566db39.json"

    # Use .env files based on APP_ENV
    model_config = SettingsConfigDict(
        env_file=(".env", f".env.{os.getenv('APP_ENV', 'development')}"),
        env_file_encoding='utf-8',
        extra='ignore'
    )

settings = Settings()
