import mlflow
from mlflow.tracking import MlflowClient
from config import settings
import argparse

def promote_model(model_name: str, version: int, target_alias: str):
    """
    Promotes a specific model version to a given alias (e.g., 'Production').
    """
    if not settings.MLFLOW_TRACKING_URI:
        print("Error: MLFLOW_TRACKING_URI not set in config.")
        return

    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    client = MlflowClient()

    print(f"Promoting {model_name} v{version} to {target_alias}...")
    
    # Assign the alias to the specified version
    client.set_registered_model_alias(model_name, target_alias, str(version))
    
    print(f"✅ Successfully promoted {model_name} version {version} to @{target_alias}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Promote MLflow Model versions.")
    parser.add_argument("--model", type=str, default="SentimentModel", help="Model name in registry")
    parser.add_argument("--version", type=int, required=True, help="Model version number")
    parser.add_argument("--alias", type=str, default="Production", help="Alias to assign (Staging, Production)")

    args = parser.parse_args()
    promote_model(args.model, args.version, args.alias)
