# app/ml/model_trainer.py
"""
Model Trainer — trains the Random Forest procrastination predictor.

Responsibility:
- Train Random Forest on feature matrix
- Evaluate model performance
- Save trained model to disk
- Generate feature importance report

This layer knows about scikit-learn.
It does NOT know about Supabase or HTTP.
"""

import numpy as np
import json
import os
import pickle
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics  import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)


class ModelTrainer:

    def __init__(self):
        self.model          = None
        self.feature_names  = []
        self.training_meta  = {}
        self.is_trained     = False

    # ── Training ───────────────────────────────────────────────────────

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        feature_names: List[str]
    ) -> 'ModelTrainer':
        """
        Train the Random Forest classifier.

        Args:
            X_train:       Feature matrix (n_samples, n_features)
            y_train:       Labels (n_samples,) — 0=focused, 1=procrastinating
            feature_names: Names of each feature column

        Returns:
            self (for chaining)
        """
        self.feature_names = feature_names

        print(f"🌲 Training Random Forest...")
        print(f"   Training samples: {len(X_train)}")
        print(f"   Features:         {len(feature_names)}")
        print(f"   Label balance:    {int(y_train.sum())} procrastinated, "
              f"{int((y_train == 0).sum())} focused")

        # ── Handle class imbalance ─────────────────────────────────────
        # If dataset is imbalanced (e.g. 80% focused, 20% procrastinated),
        # class_weight='balanced' tells the model to pay more attention
        # to the minority class (procrastinated sessions)
        self.model = RandomForestClassifier(
            n_estimators=100,        # 100 trees in the forest
            max_depth=10,            # Max depth per tree (prevents overfitting)
            min_samples_split=2,     # Min samples to split a node
            min_samples_leaf=1,      # Min samples at leaf node
            max_features='sqrt',     # Features per tree = sqrt(total features)
            class_weight='balanced', # Handle imbalanced classes
            random_state=42,         # Reproducible results
            n_jobs=-1                # Use all CPU cores
        )

        self.model.fit(X_train, y_train)
        self.is_trained = True

        # Store training metadata
        self.training_meta = {
            'trained_at':      datetime.utcnow().isoformat(),
            'n_samples':       len(X_train),
            'n_features':      len(feature_names),
            'n_estimators':    100,
            'label_balance': {
                'procrastinated': int(y_train.sum()),
                'focused':        int((y_train == 0).sum())
            }
        }

        print("Model trained!")
        return self

    # ── Evaluation ─────────────────────────────────────────────────────

    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict[str, Any]:
        """
        Evaluate model performance on test set.

        Returns dict with accuracy, precision, recall, F1, confusion matrix.
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")

        y_pred      = self.model.predict(X_test)
        y_pred_prob = self.model.predict_proba(X_test)[:, 1]

        # Core metrics
        accuracy  = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall    = recall_score(y_test, y_pred, zero_division=0)
        f1        = f1_score(y_test, y_pred, zero_division=0)
        cm        = confusion_matrix(y_test, y_pred)

        # Confusion matrix breakdown
        if cm.shape == (2, 2):
            tn, fp, fn, tp = cm.ravel()
        else:
            tn, fp, fn, tp = 0, 0, 0, int(cm[0][0])

        metrics = {
            'accuracy':  round(float(accuracy),  4),
            'precision': round(float(precision), 4),
            'recall':    round(float(recall),    4),
            'f1_score':  round(float(f1),        4),
            'confusion_matrix': {
                'true_negatives':  int(tn),   # Correctly predicted focused
                'false_positives': int(fp),   # Said procrastinating, was focused
                'false_negatives': int(fn),   # Said focused, was procrastinating
                'true_positives':  int(tp)    # Correctly predicted procrastinating
            },
            'test_samples': len(X_test),
            'interpretation': self._interpret_metrics(accuracy, precision, recall)
        }

        # Print report
        print("\nModel Evaluation:")
        print(f"   Accuracy:  {accuracy:.1%}")
        print(f"   Precision: {precision:.1%}")
        print(f"   Recall:    {recall:.1%}")
        print(f"   F1 Score:  {f1:.1%}")
        print(f"\n   Confusion Matrix:")
        print(f"   TP={tp} FP={fp}")
        print(f"   FN={fn} TN={tn}")
        print(f"\n   {metrics['interpretation']}")

        return metrics

    def _interpret_metrics(
        self,
        accuracy: float,
        precision: float,
        recall: float
    ) -> str:
        """Generate human-readable interpretation of metrics."""

        if accuracy >= 0.85:
            acc_msg = "Excellent accuracy"
        elif accuracy >= 0.70:
            acc_msg = "Good accuracy"
        elif accuracy >= 0.60:
            acc_msg = "Moderate accuracy — more data will help"
        else:
            acc_msg = "Low accuracy — need more training data"

        if recall >= 0.70:
            rec_msg = "catches most procrastination episodes"
        else:
            rec_msg = "misses some procrastination episodes"

        return f"{acc_msg}. Model {rec_msg}."

    # ── Feature Importance ─────────────────────────────────────────────

    def get_feature_importance(self) -> List[Dict]:
        """
        Return features ranked by importance.
        Higher importance = feature contributes more to predictions.
        """
        if not self.is_trained:
            raise ValueError("Model not trained.")

        importances = self.model.feature_importances_

        # Pair feature names with importance scores
        feature_importance = [
            {
                'feature':    name,
                'importance': round(float(imp), 4),
                'percentage': round(float(imp) * 100, 2)
            }
            for name, imp in zip(self.feature_names, importances)
        ]

        # Sort by importance descending
        feature_importance.sort(
            key=lambda x: x['importance'],
            reverse=True
        )

        return feature_importance

    # ── Prediction ─────────────────────────────────────────────────────

    def predict(self, X: np.ndarray) -> Dict[str, Any]:
        """
        Predict procrastination risk for one or more samples.

        Args:
            X: Feature matrix (n_samples, n_features)

        Returns:
            Dict with prediction and confidence
        """
        if not self.is_trained:
            raise ValueError("Model not trained.")

        # Get class probabilities
        # predict_proba returns [[prob_focused, prob_procrastinating], ...]
        probabilities = self.model.predict_proba(X)
        predictions   = self.model.predict(X)

        results = []
        for i, (pred, probs) in enumerate(zip(predictions, probabilities)):
            risk_score = float(probs[1])  # Probability of procrastinating

            results.append({
                'prediction':         int(pred),
                'will_procrastinate': bool(pred == 1),
                'risk_score':         round(risk_score, 4),
                'risk_percentage':    round(risk_score * 100, 1),
                'confidence':         self._get_confidence(risk_score, pred),
                'risk_level':         self._get_risk_level(risk_score)
            })

        return results[0] if len(results) == 1 else results

    def _get_confidence(self, risk_score: float, prediction: int) -> str:
        """How confident is the model in its prediction?"""
        # Distance from 0.5 = confidence
        distance = abs(risk_score - 0.5)

        if distance >= 0.35:
            return 'high'
        elif distance >= 0.15:
            return 'medium'
        else:
            return 'low'

    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to human-readable level."""
        if risk_score >= 0.75:
            return 'critical'
        elif risk_score >= 0.60:
            return 'high'
        elif risk_score >= 0.40:
            return 'medium'
        else:
            return 'low'

    # ── Save / Load ────────────────────────────────────────────────────

    def save(self, model_dir: str = "app/ml/models") -> str:
        """
        Save trained model and metadata to disk.

        Saves two files:
        - model.pkl:  The trained RandomForest object
        - model_meta.json: Training metadata and feature names
        """
        if not self.is_trained:
            raise ValueError("Cannot save untrained model.")

        os.makedirs(model_dir, exist_ok=True)

        # Save model binary
        model_path = os.path.join(model_dir, "procrastination_model.pkl")
        with open(model_path, 'wb') as f:
            pickle.dump(self.model, f)

        # Save metadata
        meta_path = os.path.join(model_dir, "model_meta.json")
        meta = {
            **self.training_meta,
            'feature_names':      self.feature_names,
            'feature_importance': self.get_feature_importance()
        }
        with open(meta_path, 'w') as f:
            json.dump(meta, f, indent=2)

        print(f"Model saved to {model_path}")
        print(f"Metadata saved to {meta_path}")

        return model_path

    def load(self, model_dir: str = "app/ml/models") -> 'ModelTrainer':
        """Load trained model and metadata from disk."""
        model_path = os.path.join(model_dir, "procrastination_model.pkl")
        meta_path  = os.path.join(model_dir, "model_meta.json")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")

        # Load model
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)

        # Load metadata
        if os.path.exists(meta_path):
            with open(meta_path, 'r') as f:
                meta = json.load(f)

            self.feature_names = meta.get('feature_names', [])
            self.training_meta = meta

        self.is_trained = True
        print(f"Model loaded from {model_path}")

        return self
