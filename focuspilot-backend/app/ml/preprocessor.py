# app/ml/preprocessor.py
"""
Preprocessor — cleans and normalizes feature data.

Responsibility:
- Handle missing values
- Normalize numeric features (0 to 1 scale)
- Encode categorical features
- Split into train/test sets
- Save/load scaler for inference

This layer knows about ML math.
It does NOT know about Supabase or sessions.
"""

import numpy as np
from typing import List, Dict, Tuple
import json
import os


class Preprocessor:

    # Features that need normalization (min-max scaling)
    NUMERIC_FEATURES = [
        'hour_of_day',
        'day_of_week',
        'session_duration_mins',
        'distraction_ratio',
        'distraction_count',
        'peak_distraction_mins',
        'avg_focus_score_last3',
        'days_since_last_session',
        'sessions_today',
        'avg_duration_last7',
        'same_hour_avg_score',
        'streak_days'
    ]

    # Features that are already binary (0 or 1)
    BINARY_FEATURES = [
        'is_night',
        'is_weekend',
        'abandoned_early'
    ]

    # All features in order
    ALL_FEATURES = NUMERIC_FEATURES + BINARY_FEATURES

    def __init__(self):
        self.feature_mins  = {}
        self.feature_maxes = {}
        self.is_fitted     = False

    # ── Fit + Transform ────────────────────────────────────────────────

    def fit(self, feature_rows: List[Dict]) -> 'Preprocessor':
        """
        Learn min/max values from training data.
        Call this ONCE on training data only.
        """
        for feature in self.NUMERIC_FEATURES:
            values = [
                row[feature]
                for row in feature_rows
                if feature in row and row[feature] is not None
            ]

            if values:
                self.feature_mins[feature]  = min(values)
                self.feature_maxes[feature] = max(values)
            else:
                self.feature_mins[feature]  = 0
                self.feature_maxes[feature] = 1

        self.is_fitted = True
        return self

    def transform(self, feature_rows: List[Dict]) -> np.ndarray:
        """
        Normalize features using fitted min/max values.
        Returns numpy array ready for model training/inference.
        """
        if not self.is_fitted:
            raise ValueError(
                "Preprocessor not fitted. Call fit() first."
            )

        matrix = []

        for row in feature_rows:
            processed_row = []

            # Normalize numeric features
            for feature in self.NUMERIC_FEATURES:
                value    = row.get(feature) or 0
                min_val  = self.feature_mins.get(feature, 0)
                max_val  = self.feature_maxes.get(feature, 1)

                # Min-max normalization: (x - min) / (max - min)
                if max_val > min_val:
                    normalized = (value - min_val) / (max_val - min_val)
                else:
                    normalized = 0.0

                # Clip to [0, 1] to handle out-of-range values
                normalized = max(0.0, min(1.0, normalized))
                processed_row.append(normalized)

            # Binary features (already 0 or 1)
            for feature in self.BINARY_FEATURES:
                processed_row.append(float(row.get(feature) or 0))

            matrix.append(processed_row)

        return np.array(matrix, dtype=np.float32)

    def fit_transform(self, feature_rows: List[Dict]) -> np.ndarray:
        """Fit and transform in one step."""
        return self.fit(feature_rows).transform(feature_rows)

    def extract_labels(self, feature_rows: List[Dict]) -> np.ndarray:
        """Extract target labels from feature rows."""
        labels = [
            int(row.get('did_procrastinate') or 0)
            for row in feature_rows
        ]
        return np.array(labels, dtype=np.int32)

    # ── Train/Test Split ───────────────────────────────────────────────

    def train_test_split(
        self,
        X: np.ndarray,
        y: np.ndarray,
        test_size: float = 0.2
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Split data into training and test sets.
        Uses time-based split (not random) to prevent data leakage.
        Earlier sessions = train, later sessions = test.
        """
        n_total = len(X)
        n_test  = max(1, int(n_total * test_size))
        n_train = n_total - n_test

        X_train = X[:n_train]
        X_test  = X[n_train:]
        y_train = y[:n_train]
        y_test  = y[n_train:]

        return X_train, X_test, y_train, y_test

    # ── Save/Load ──────────────────────────────────────────────────────

    def save(self, path: str = "app/ml/scaler.json"):
        """Save fitted scaler parameters to disk."""
        os.makedirs(os.path.dirname(path), exist_ok=True)

        params = {
            'feature_mins':  self.feature_mins,
            'feature_maxes': self.feature_maxes,
            'is_fitted':     self.is_fitted
        }

        with open(path, 'w') as f:
            json.dump(params, f, indent=2)

        print(f"Scaler saved to {path}")

    def load(self, path: str = "app/ml/scaler.json") -> 'Preprocessor':
        """Load fitted scaler parameters from disk."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Scaler file not found: {path}")

        with open(path, 'r') as f:
            params = json.load(f)

        self.feature_mins  = params['feature_mins']
        self.feature_maxes = params['feature_maxes']
        self.is_fitted     = params['is_fitted']

        return self

    def get_feature_stats(
        self,
        feature_rows: List[Dict]
    ) -> Dict:
        """
        Return descriptive statistics for each feature.
        Useful for understanding your data before training.
        """
        stats = {}

        for feature in self.ALL_FEATURES:
            values = [
                row[feature]
                for row in feature_rows
                if feature in row and row[feature] is not None
            ]

            if not values:
                continue

            arr = np.array(values)

            stats[feature] = {
                'mean':   round(float(np.mean(arr)), 3),
                'std':    round(float(np.std(arr)), 3),
                'min':    round(float(np.min(arr)), 3),
                'max':    round(float(np.max(arr)), 3),
                'median': round(float(np.median(arr)), 3)
            }

        return stats
