# app/ml/model_manager.py
"""
Model Manager — loads and caches trained models for inference.

This is a SINGLETON that keeps models in memory.
Loading from disk on every prediction would be too slow.

Usage:
    manager    = ModelManager()
    prediction = manager.predict(user_id, feature_row)
"""

import os
import threading
from typing import Dict, Optional
import numpy as np

from app.ml.model_trainer  import ModelTrainer
from app.ml.preprocessor   import Preprocessor


class ModelManager:
    """Thread-safe singleton model cache."""

    _instance = None
    _lock     = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._models      = {}
                    cls._instance._scalers     = {}
                    cls._instance._initialized = True
        return cls._instance

    # ── Load ───────────────────────────────────────────────────────────

    def load_model(self, user_id: str) -> Optional[ModelTrainer]:
        """
        Load model for user (from cache or disk).
        Returns None if no model exists yet.
        """
        user_key   = user_id[:8]
        model_path = f"app/ml/models/{user_key}/procrastination_model.pkl"

        # Return cached model if available
        if user_key in self._models:
            return self._models[user_key]

        # Load from disk
        if not os.path.exists(model_path):
            return None

        try:
            trainer = ModelTrainer()
            trainer.load(model_dir=f"app/ml/models/{user_key}")
            self._models[user_key] = trainer
            print(f"✅ Model loaded for user {user_key}")
            return trainer
        except Exception as e:
            print(f"⚠️  Failed to load model for {user_key}: {e}")
            return None

    def load_scaler(self, user_id: str) -> Optional[Preprocessor]:
        """Load preprocessor/scaler for user."""
        user_key     = user_id[:8]
        scaler_path  = f"app/ml/scalers/{user_key}_scaler.json"

        if user_key in self._scalers:
            return self._scalers[user_key]

        if not os.path.exists(scaler_path):
            return None

        try:
            preprocessor = Preprocessor()
            preprocessor.load(scaler_path)
            self._scalers[user_key] = preprocessor
            return preprocessor
        except Exception as e:
            print(f"⚠️  Failed to load scaler for {user_key}: {e}")
            return None

    def invalidate(self, user_id: str):
        """
        Remove cached model (call after retraining).
        Forces reload from disk on next prediction.
        """
        user_key = user_id[:8]
        self._models.pop(user_key, None)
        self._scalers.pop(user_key, None)
        print(f"🔄 Cache invalidated for user {user_key}")

    def has_model(self, user_id: str) -> bool:
        """Check if a trained model exists for this user."""
        user_key   = user_id[:8]
        model_path = f"app/ml/models/{user_key}/procrastination_model.pkl"
        return (
            user_key in self._models or
            os.path.exists(model_path)
        )

    # ── Predict ────────────────────────────────────────────────────────

    def predict(
        self,
        user_id: str,
        X: np.ndarray
    ) -> Dict:
        """
        Make a prediction for a user.

        Args:
            user_id: User's ID
            X:       Preprocessed feature array (1, n_features)

        Returns:
            Prediction dict with risk_score, risk_level, etc.
            Returns default 'low risk' if no model exists.
        """
        trainer = self.load_model(user_id)

        if trainer is None:
            # No model yet — return neutral prediction
            return {
                'prediction':         0,
                'will_procrastinate': False,
                'risk_score':         0.3,
                'risk_percentage':    30.0,
                'confidence':         'low',
                'risk_level':         'low',
                'model_available':    False,
                'message':            'Model not trained yet. Complete more sessions.'
            }

        result = trainer.predict(X)
        result['model_available'] = True
        return result


# Global singleton instance
model_manager = ModelManager()
