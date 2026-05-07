import pandas as pd
import torch
from torch.utils.data import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments,
    pipeline,
    TrainerCallback
)
import mlflow
import mlflow.transformers
import re
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

# ---------------- CONFIG ----------------
DATA_PATH = "training.1600000.processed.noemoticon.csv"
MODEL_SAVE_PATH = "./sentiment_model"
SAMPLE_SIZE = 5000
MODEL_NAME = "google/bert_uncased_L-2_H-128_A-2"

# ---------------- CLEAN TEXT ----------------
def clean_tweet(text):
    if not isinstance(text, str):
        return ""
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'http\S+|www\S+|https\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ---------------- DATASET ----------------
class SentimentDataset(Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {k: v[idx] for k, v in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.labels)

# ---------------- METRICS ----------------
def compute_metrics(pred):
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)

    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average="binary"
    )
    acc = accuracy_score(labels, preds)

    return {
        "accuracy": acc,
        "f1": f1,
        "precision": precision,
        "recall": recall
    }

# ---------------- TRAIN MODEL ----------------
def train_model():
    print(f"Loading data from {DATA_PATH}...")

    columns = ["target", "ids", "date", "flag", "user", "text"]
    df = pd.read_csv(DATA_PATH, encoding="latin-1", names=columns)

    # convert labels (4 → 1)
    df["target"] = df["target"].replace(4, 1)

    # Load staging data if exists (Continuous Training)
    staging_path = "human_overrides_staging.csv"
    if os.path.exists(staging_path):
        print(f"Loading staging data from {staging_path}...")
        staging_df = pd.read_csv(staging_path)
        # Map staging 'class' (0=Hate, 1=Offensive, 2=Neither) to 'target' (0=Neg, 1=Pos)
        # This is a simplification; in reality, we'd have a more robust mapping.
        # For BERT sentiment, we mostly care about Pos/Neg.
        staging_df["target"] = staging_df["class"].map({0: 0, 1: 0, 2: 1})
        staging_df = staging_df.rename(columns={"tweet": "text"})
        df = pd.concat([df, staging_df[["text", "target"]]], ignore_index=True)
        print(f"Added {len(staging_df)} samples from overrides.")

    # balance dataset
    df_pos = df[df["target"] == 1].sample(min(len(df[df["target"] == 1]), SAMPLE_SIZE // 2), random_state=42)
    df_neg = df[df["target"] == 0].sample(min(len(df[df["target"] == 0]), SAMPLE_SIZE // 2), random_state=42)
    df = pd.concat([df_pos, df_neg]).sample(frac=1, random_state=42)

    print(f"Preprocessing {len(df)} samples...")
    df["text"] = df["text"].apply(clean_tweet)

    train_texts, val_texts, train_labels, val_labels = train_test_split(
        df["text"].tolist(),
        df["target"].tolist(),
        test_size=0.2,
        random_state=42
    )

    print(f"Tokenizing with {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    train_encodings = tokenizer(
        train_texts,
        truncation=True,
        padding=True,
        max_length=128
    )

    val_encodings = tokenizer(
        val_texts,
        truncation=True,
        padding=True,
        max_length=128
    )

    train_dataset = SentimentDataset(train_encodings, train_labels)
    val_dataset = SentimentDataset(val_encodings, val_labels)

    print("Loading model...")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=2
    )

    # ---------------- TRAINING ARGS (FIXED FOR ALL VERSIONS) ----------------
    training_args = TrainingArguments(
        output_dir="./results",
        num_train_epochs=3,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        warmup_steps=100,
        weight_decay=0.01,
        logging_dir="./logs",
        logging_steps=50,

        # compatibility fix (new transformers)
        eval_strategy="epoch",
        save_strategy="epoch",

        load_best_model_at_end=True,

        # automatic CPU/GPU detection (SAFE FIX)
        no_cuda=not torch.cuda.is_available()
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics
    )

    print("Training started...")
    
    mlflow.set_experiment("BERT_Sentiment_Analysis")
    with mlflow.start_run():
        mlflow.log_params({
            "model_name": MODEL_NAME,
            "sample_size": SAMPLE_SIZE,
            "epochs": training_args.num_train_epochs,
            "batch_size": training_args.per_device_train_batch_size,
        })
        
        trainer.train()
        
        # Log final metrics
        eval_metrics = trainer.evaluate()
        mlflow.log_metrics(eval_metrics)
        
        print(f"Saving model to {MODEL_SAVE_PATH}...")
        model.save_pretrained(MODEL_SAVE_PATH)
        tokenizer.save_pretrained(MODEL_SAVE_PATH)
        
        # Log model to MLflow
        mlflow.transformers.log_model(
            transformers_model={"model": model, "tokenizer": tokenizer},
            artifact_path="sentiment_bert_model"
        )

    print("Training complete!")

# ---------------- INTERACTIVE MODE ----------------
def interactive_mode():
    if not os.path.exists(MODEL_SAVE_PATH):
        print("Model not found. Train first.")
        return

    classifier = pipeline(
        "sentiment-analysis",
        model=MODEL_SAVE_PATH,
        tokenizer=MODEL_SAVE_PATH
    )

    print("\n=== SENTIMENT ANALYZER ===")
    print("Type 'exit' to quit")

    while True:
        text = input("\nTweet: ")
        if text.lower() == "exit":
            break

        text = clean_tweet(text)
        result = classifier(text)[0]

        label = "POSITIVE" if result["label"] == "LABEL_1" else "NEGATIVE"
        print(f"{label} ({result['score']:.2%})")

# ---------------- MAIN ----------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--train":
        train_model()
    elif os.path.exists(MODEL_SAVE_PATH):
        interactive_mode()
    else:
        print("No model found. Training first...")
        train_model()
        interactive_mode()