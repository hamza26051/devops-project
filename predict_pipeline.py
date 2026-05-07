import joblib
import pandas as pd
from pipeline_utils import preprocess_data

class BotDetectionPipeline:
    def __init__(self, model_dir='models'):
        """
        Load the trained model and artifacts
        """
        self.model = joblib.load(f'{model_dir}/best_model.joblib')
        self.tfidf_vec = joblib.load(f'{model_dir}/tfidf_vectorizer.joblib')
        self.scaler = joblib.load(f'{model_dir}/scaler.joblib')
        
    def predict(self, raw_data):
        """
        Predict bot/human for raw input
        raw_data: DataFrame with columns: Tweet, Retweet Count, Mention Count, Follower Count, Verified, Created At
        """
        # Preprocess using the loaded artifacts
        processed_data, _, _ = preprocess_data(
            raw_data, 
            is_training=False, 
            tfidf_vectorizer=self.tfidf_vec, 
            scaler=self.scaler
        )
        
        # Predict
        predictions = self.model.predict(processed_data)
        probabilities = self.model.predict_proba(processed_data)[:, 1]
        
        results = []
        for pred, prob in zip(predictions, probabilities):
            results.append({
                'label': 'Bot' if pred == 1 else 'Human',
                'bot_probability': float(prob),
                'is_risky': bool(pred == 1) # Bot is considered risky for car rental
            })
            
        return results

if __name__ == "__main__":
    # Example usage
    pipeline = BotDetectionPipeline()
    
    sample_input = pd.DataFrame([{
        'Tweet': "I love renting cars for my summer road trips!",
        'Retweet Count': 2,
        'Mention Count': 1,
        'Follower Count': 500,
        'Verified': False,
        'Created At': '2022-01-01 10:00:00',
        'User ID': '123', # Will be dropped
        'Username': 'user1', # Will be dropped
        'Location': 'NYC' # Will be dropped
    }])
    
    prediction = pipeline.predict(sample_input)
    print(f"Prediction for sample input: {prediction}")
