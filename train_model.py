"""
TruthLens — ML Training Pipeline
Trains an ensemble classifier (Passive Aggressive + Logistic Regression + Random Forest)
on a curated fake/real news dataset and exports model.pkl + vectorizer.pkl
"""

import os
import json
import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import random
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.metrics import (
    accuracy_score, f1_score, classification_report, confusion_matrix
)

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

MODEL_PATH      = os.path.join(MODELS_DIR, "model.pkl")
VECTORIZER_PATH = os.path.join(MODELS_DIR, "vectorizer.pkl")
DATASET_PATH    = os.path.join(DATA_DIR, "sample_news.csv")

# ── Banner ─────────────────────────────────────────────────────────────────────
def banner():
    print("\n" + "=" * 55)
    print("  🛡️  TruthLens — Model Training Pipeline")
    print("=" * 55)

# ── Text Cleaning ──────────────────────────────────────────────────────────────
import re

def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"http\S+|www\S+", " ", text)          # remove URLs
    text = re.sub(r"[^a-z\s]", " ", text)                # keep only letters
    text = re.sub(r"\s+", " ", text).strip()              # collapse whitespace
    return text

# ── Load Dataset ───────────────────────────────────────────────────────────────
def load_dataset():
    if not os.path.exists(DATASET_PATH):
        print(f"\n❌  Dataset not found at: {DATASET_PATH}")
        print("    Run generate_dataset.py first, or place your Fake.csv / True.csv")
        print("    in the data/ folder and update this script.\n")
        raise FileNotFoundError(DATASET_PATH)

    print(f"\n📂  Loading dataset from {DATASET_PATH} ...")
    df = pd.read_csv(DATASET_PATH)

    # Expect columns: text, label  (0=fake, 1=real)
    df = df.dropna(subset=["text", "label"])
    df["text"] = df["text"].apply(clean_text)
    df = df[df["text"].str.len() > 20]          # drop near-empty rows

    fake_count = int((df["label"] == 0).sum())
    real_count = int((df["label"] == 1).sum())
    print(f"✅  Loaded {len(df):,} articles  |  Fake: {fake_count:,}  Real: {real_count:,}")
    return df

# ── Train ──────────────────────────────────────────────────────────────────────
def train(df):
    X = df["text"]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42
    )
    print(f"\n✂️   Split  —  Train: {len(X_train):,}  |  Test: {len(X_test):,}")

    # ── TF-IDF ────────────────────────────────────────────────────────────────
    print("\n📊  Fitting TF-IDF vectorizer  (unigrams + bigrams, max 50k features)…")
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=50_000,
        ngram_range=(1, 2),
        max_df=0.70,
        sublinear_tf=True,
    )
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec  = vectorizer.transform(X_test)

    # ── Individual Models ─────────────────────────────────────────────────────
    print("\n🏋️  Training individual classifiers…")

    mnb = MultinomialNB(alpha=0.1)
    lr  = LogisticRegression(max_iter=1000, C=1.0, solver="lbfgs", random_state=42, n_jobs=-1)
    rf  = RandomForestClassifier(n_estimators=100, max_depth=30, random_state=42, n_jobs=-1)

    for name, clf in [("Multinomial Naive Bayes", mnb), ("Logistic Regression", lr), ("Random Forest", rf)]:
        clf.fit(X_train_vec, y_train)
        acc = accuracy_score(y_test, clf.predict(X_test_vec)) * 100
        print(f"   {name:<25}  accuracy = {acc:.2f}%")

    # ── Ensemble ──────────────────────────────────────────────────────────────
    print("\n🗳️  Building soft-voting ensemble…")
    ensemble = VotingClassifier(
        estimators=[("mnb", mnb), ("lr", lr), ("rf", rf)],
        voting="soft",
        weights=[1, 2, 1],   # LR gets slightly higher weight (best calibrated)
    )
    ensemble.fit(X_train_vec, y_train)

    y_pred = ensemble.predict(X_test_vec)
    acc = accuracy_score(y_test, y_pred) * 100
    f1  = f1_score(y_test, y_pred, average="weighted") * 100
    cm  = confusion_matrix(y_test, y_pred)

    print(f"\n{'=' * 55}")
    print(f"  ✅  Ensemble Accuracy : {acc:.2f}%")
    print(f"  ✅  F1 Score          : {f1:.2f}%")
    print(f"  Confusion Matrix:")
    print(f"    TN={cm[0,0]}  FP={cm[0,1]}")
    print(f"    FN={cm[1,0]}  TP={cm[1,1]}")
    print(f"\n{classification_report(y_test, y_pred, target_names=['Fake','Real'])}")
    print("=" * 55)

    # ── Save ──────────────────────────────────────────────────────────────────
    joblib.dump(ensemble,   MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    print(f"\n💾  Saved model     → {MODEL_PATH}")
    print(f"💾  Saved vectorizer→ {VECTORIZER_PATH}")

    # Save meta
    meta = {
        "accuracy": round(acc, 2),
        "f1_score": round(f1, 2),
        "total_samples": len(df),
        "fake_samples": int((df["label"] == 0).sum()),
        "real_samples": int((df["label"] == 1).sum()),
        "features": 50_000,
        "models": ["MultinomialNB", "LogisticRegression", "RandomForest"],
        "voting": "soft",
    }
    with open(os.path.join(MODELS_DIR, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    return ensemble, vectorizer

# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    banner()
    df = load_dataset()
    train(df)
    print("\n🎉  Training complete!  Run  python app.py  to start the server.\n")
