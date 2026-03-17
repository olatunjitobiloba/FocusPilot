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
from datetime import datetime

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
                    cls._instance._load_errors = {}
                    cls._instance._retrain_in_progress = set()
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
            self._load_errors.pop(user_key, None)
            return self._models[user_key]

        # Load from disk
        if not os.path.exists(model_path):
            self._load_errors.pop(user_key, None)
            return None

        try:
            trainer = ModelTrainer()
            trainer.load(model_dir=f"app/ml/models/{user_key}")
            self._models[user_key] = trainer
            self._load_errors.pop(user_key, None)
            print(f"Model loaded for user {user_key}")
            return trainer
        except Exception as e:
            self._load_errors[user_key] = str(e)
            self._quarantine_incompatible_model(user_key)
            print(f"WARNING Failed to load model for {user_key}: {e}")
            return None

    def _quarantine_incompatible_model(self, user_key: str):
        """
        Rename incompatible model artifacts so they are not retried forever.
        """
        model_dir = f"app/ml/models/{user_key}"
        model_path = os.path.join(model_dir, "procrastination_model.pkl")

        if not os.path.exists(model_path):
            return

        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        quarantined = os.path.join(
            model_dir,
            f"procrastination_model.incompatible.{ts}.pkl"
        )

        try:
            os.rename(model_path, quarantined)
            print(
                f"WARNING Quarantined incompatible model artifact for {user_key}: "
                f"{quarantined}"
            )
        except Exception as rename_error:
            print(
                f"WARNING Could not quarantine incompatible model for {user_key}: "
                f"{rename_error}"
            )

    def get_last_model_error(self, user_id: str) -> Optional[str]:
        """Return the most recent model load error for a user, if any."""
        return self._load_errors.get(user_id[:8])

    def mark_retraining_started(self, user_id: str):
        self._retrain_in_progress.add(user_id[:8])

    def mark_retraining_finished(self, user_id: str):
        self._retrain_in_progress.discard(user_id[:8])

    def is_retraining(self, user_id: str) -> bool:
        return user_id[:8] in self._retrain_in_progress

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
            print(f"WARNING Failed to load scaler for {user_key}: {e}")
            return None

    def invalidate(self, user_id: str):
        """
        Remove cached model (call after retraining).
        Forces reload from disk on next prediction.
        """
        user_key = user_id[:8]
        self._models.pop(user_key, None)
        self._scalers.pop(user_key, None)
        self._load_errors.pop(user_key, None)
        self._retrain_in_progress.discard(user_key)
        print(f"Cache invalidated for user {user_key}")

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
        has_artifact = self.has_model(user_id)

        if trainer is None:
            last_error = self.get_last_model_error(user_id)
            if has_artifact and last_error:
                return {
                    'prediction':         0,
                    'will_procrastinate': False,
                    'risk_score':         0.3,
                    'risk_percentage':    30.0,
                    'confidence':         'low',
                    'risk_level':         'low',
                    'model_available':    False,
                    'retrain_required':   True,
                    'retraining':         self.is_retraining(user_id),
                    'error_code':         'model_load_failed',
                    'model_error':        last_error,
                    'message':            'Model artifact is incompatible with current runtime. Retrain required.'
                }

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
