# app/ml/dataset_builder.py
"""
Dataset Builder — orchestrates the full data pipeline.

Usage:
    builder = DatasetBuilder(user_id="abc-123")
    dataset = builder.build()

    X_train, X_test, y_train, y_test = dataset['splits']
    feature_names = dataset['feature_names']
    stats = dataset['stats']
"""

from app.ml.data_extractor   import DataExtractor
from app.ml.feature_engineer import FeatureEngineer
from app.ml.preprocessor     import Preprocessor
from typing import Dict, Any
import numpy as np


class DatasetBuilder:

    def __init__(self, user_id: str, days_back: int = 30):
        self.user_id      = user_id
        self.days_back    = days_back
        self.extractor    = DataExtractor(user_id)
        self.engineer     = FeatureEngineer()
        self.preprocessor = Preprocessor()

    def build(self) -> Dict[str, Any]:
        """
        Full pipeline:
        1. Extract raw data from Supabase
        2. Engineer features
        3. Preprocess (normalize)
        4. Split into train/test
        5. Return everything

        Returns dict with:
        - splits:        (X_train, X_test, y_train, y_test)
        - feature_rows:  Raw feature dicts (for debugging)
        - feature_names: List of feature names
        - stats:         Descriptive statistics
        - data_summary:  How much data we have
        - preprocessor:  Fitted preprocessor (save for inference)
        """

        print(f"Building dataset for user {self.user_id[:8]}...")

        # ── Step 1: Check data availability ───────────────────────────
        data_summary = self.extractor.get_data_summary()
        print(f"   Data: {data_summary['completed_sessions']} sessions, "
              f"{data_summary['total_activities']} activities")

        if not data_summary['has_enough_data']:
            print("   Not enough data for ML (need >= 5 sessions)")
            return {
                'error':        'insufficient_data',
                'data_summary': data_summary,
                'message':      (
                    f"Need at least 5 completed sessions. "
                    f"Currently have {data_summary['completed_sessions']}."
                )
            }

        # ── Step 2: Extract raw data ───────────────────────────────────
        sessions = self.extractor.get_sessions_with_activities(
            days_back=self.days_back
        )
        print(f"   Extracted {len(sessions)} sessions with activities")

        # ── Step 3: Engineer features ──────────────────────────────────
        feature_rows = self.engineer.build_feature_matrix(sessions)
        print(f"   Engineered {len(feature_rows)} feature rows")

        if len(feature_rows) < 5:
            return {
                'error':   'insufficient_features',
                'message': 'Not enough completed sessions to build features'
            }

        # ── Step 4: Get statistics ─────────────────────────────────────
        stats = self.preprocessor.get_feature_stats(feature_rows)

        # ── Step 5: Preprocess ─────────────────────────────────────────
        X = self.preprocessor.fit_transform(feature_rows)
        y = self.preprocessor.extract_labels(feature_rows)

        print(f"   Feature matrix shape: {X.shape}")
        print(f"   Label distribution: "
              f"{int(y.sum())} procrastinated, "
              f"{int((y == 0).sum())} focused")

        # ── Step 6: Train/test split ───────────────────────────────────
        X_train, X_test, y_train, y_test = (
            self.preprocessor.train_test_split(X, y, test_size=0.2)
        )

        print(f"   Train: {len(X_train)} rows | Test: {len(X_test)} rows")

        # ── Step 7: Save preprocessor ─────────────────────────────────
        self.preprocessor.save(f"app/ml/scalers/{self.user_id[:8]}_scaler.json")

        print("Dataset built successfully!")

        return {
            'splits':        (X_train, X_test, y_train, y_test),
            'feature_rows':  feature_rows,
            'feature_names': self.engineer.get_feature_names(),
            'stats':         stats,
            'data_summary':  data_summary,
            'preprocessor':  self.preprocessor,
            'label_balance': {
                'procrastinated': int(y.sum()),
                'focused':        int((y == 0).sum()),
                'ratio':          round(float(y.mean()), 3)
            }
        }

    def build_inference_row(
        self,
        current_session: Dict,
        preprocessor_path: str = None
    ) -> np.ndarray:
        """
        Build a single feature row for REAL-TIME prediction.
        Used when the agent needs to predict RIGHT NOW.

        Args:
            current_session: The session currently happening
            preprocessor_path: Path to saved scaler

        Returns:
            1D numpy array ready for model.predict()
        """
        # Get past sessions for historical features
        past_sessions = self.extractor.get_sessions(
            days_back=30,
            completed_only=True
        )

        # Attach activities to current session
        if 'activities' not in current_session:
            activities = self.extractor.get_activities(
                session_id=current_session['id']
            )
            current_session['activities'] = activities

        # Engineer features for this single session
        feature_rows = self.engineer.build_feature_matrix(
            past_sessions + [current_session]
        )

        if not feature_rows:
            # Return neutral features if no data
            return np.zeros((1, 15), dtype=np.float32)

        # Use last row (current session)
        current_row = feature_rows[-1:]

        # Load preprocessor
        preprocessor = Preprocessor()
        path = preprocessor_path or f"app/ml/scalers/{self.user_id[:8]}_scaler.json"

        try:
            preprocessor.load(path)
        except FileNotFoundError:
            # Fit on available data if no saved scaler
            preprocessor.fit(feature_rows)

        return preprocessor.transform(current_row)
