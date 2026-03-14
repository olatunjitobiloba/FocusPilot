# tests/test_ml.py
"""
Tests for ML pipeline.
Run with: pytest tests/test_ml.py -v
"""

import pytest
import numpy as np
from app.ml.feature_engineer import FeatureEngineer
from app.ml.preprocessor     import Preprocessor
from app.ml.model_trainer    import ModelTrainer


class TestFeatureEngineer:

    def setup_method(self):
        """Create sample sessions for testing."""
        self.engineer = FeatureEngineer()

        self.sample_sessions = [
            {
                'id':               f'session-{i}',
                'user_id':          'user-123',
                'start_time':       f'2024-01-{10+i:02d}T14:30:00',
                'end_time':         f'2024-01-{10+i:02d}T15:15:00',
                'duration_minutes': 45,
                'focus_score':      7 if i % 2 == 0 else 4,
                'distraction_count': 2,
                'activities': [
                    {
                        'domain':           'youtube.com',
                        'duration_seconds': 300,
                        'session_id':       f'session-{i}',
                        'timestamp':        f'2024-01-{10+i:02d}T14:45:00'
                    }
                ]
            }
            for i in range(10)
        ]

    def test_builds_correct_number_of_rows(self):
        """Should build one row per completed session."""
        rows = self.engineer.build_feature_matrix(self.sample_sessions)
        assert len(rows) == len(self.sample_sessions)

    def test_all_features_present(self):
        """Each row should have all 15 features."""
        rows = self.engineer.build_feature_matrix(self.sample_sessions)
        feature_names = self.engineer.get_feature_names()

        for row in rows:
            for feature in feature_names:
                assert feature in row, f"Missing feature: {feature}"

    def test_temporal_features_valid_range(self):
        """Hour should be 0-23, day_of_week 0-6."""
        rows = self.engineer.build_feature_matrix(self.sample_sessions)

        for row in rows:
            assert 0 <= row['hour_of_day'] <= 23
            assert 0 <= row['day_of_week'] <= 6
            assert row['is_night']   in [0, 1]
            assert row['is_weekend'] in [0, 1]

    def test_distraction_ratio_bounded(self):
        """Distraction ratio must be between 0 and 1."""
        rows = self.engineer.build_feature_matrix(self.sample_sessions)

        for row in rows:
            assert 0.0 <= row['distraction_ratio'] <= 1.0

    def test_label_is_binary(self):
        """Label must be 0 or 1."""
        rows = self.engineer.build_feature_matrix(self.sample_sessions)

        for row in rows:
            assert row['did_procrastinate'] in [0, 1]

    def test_low_focus_score_labeled_procrastinating(self):
        """Sessions with focus_score <= 4 should be labeled 1."""
        low_focus_session = {
            **self.sample_sessions[0],
            'focus_score': 3
        }
        rows = self.engineer.build_feature_matrix([low_focus_session])
        assert rows[0]['did_procrastinate'] == 1

    def test_high_focus_score_labeled_focused(self):
        """Sessions with focus_score >= 8 and low distraction = 0."""
        high_focus_session = {
            **self.sample_sessions[0],
            'focus_score': 9,
            'activities':  []   # No distractions
        }
        rows = self.engineer.build_feature_matrix([high_focus_session])
        assert rows[0]['did_procrastinate'] == 0


class TestPreprocessor:

    def setup_method(self):
        self.preprocessor = Preprocessor()
        self.sample_rows  = [
            {
                'hour_of_day':            14,
                'is_night':               0,
                'day_of_week':            1,
                'is_weekend':             0,
                'session_duration_mins':  45,
                'distraction_ratio':      0.3,
                'distraction_count':      3,
                'abandoned_early':        0,
                'peak_distraction_mins':  8.5,
                'avg_focus_score_last3':  6.5,
                'days_since_last_session': 1,
                'sessions_today':         1,
                'avg_duration_last7':     40.0,
                'same_hour_avg_score':    7.0,
                'streak_days':            3,
                'did_procrastinate':      0
            }
            for _ in range(10)
        ]

    def test_fit_transform_returns_numpy_array(self):
        """fit_transform should return numpy array."""
        X = self.preprocessor.fit_transform(self.sample_rows)
        assert isinstance(X, np.ndarray)

    def test_output_shape_correct(self):
        """Output shape should be (n_samples, n_features)."""
        X = self.preprocessor.fit_transform(self.sample_rows)
        assert X.shape[0] == len(self.sample_rows)
        assert X.shape[1] == len(
            self.preprocessor.NUMERIC_FEATURES +
            self.preprocessor.BINARY_FEATURES
        )

    def test_values_normalized_0_to_1(self):
        """All values should be between 0 and 1 after normalization."""
        X = self.preprocessor.fit_transform(self.sample_rows)
        assert X.min() >= 0.0
        assert X.max() <= 1.0

    def test_labels_extracted_correctly(self):
        """Labels should match did_procrastinate field."""
        y = self.preprocessor.extract_labels(self.sample_rows)
        assert isinstance(y, np.ndarray)
        assert len(y) == len(self.sample_rows)
        assert all(label in [0, 1] for label in y)


class TestModelTrainer:

    def setup_method(self):
        """Create synthetic training data."""
        np.random.seed(42)
        self.trainer   = ModelTrainer()
        self.n_samples = 50
        self.n_features = 15

        self.X_train = np.random.rand(self.n_samples, self.n_features)
        self.X_test  = np.random.rand(10, self.n_features)
        self.y_train = np.random.randint(0, 2, self.n_samples)
        self.y_test  = np.random.randint(0, 2, 10)

        self.feature_names = [f'feature_{i}' for i in range(self.n_features)]

    def test_train_sets_is_trained(self):
        """After training, is_trained should be True."""
        self.trainer.train(self.X_train, self.y_train, self.feature_names)
        assert self.trainer.is_trained == True

    def test_evaluate_returns_metrics(self):
        """Evaluate should return accuracy, precision, recall, f1."""
        self.trainer.train(self.X_train, self.y_train, self.feature_names)
        metrics = self.trainer.evaluate(self.X_test, self.y_test)

        assert 'accuracy'  in metrics
        assert 'precision' in metrics
        assert 'recall'    in metrics
        assert 'f1_score'  in metrics

        # All metrics should be between 0 and 1
        assert 0 <= metrics['accuracy']  <= 1
        assert 0 <= metrics['precision'] <= 1
        assert 0 <= metrics['recall']    <= 1
        assert 0 <= metrics['f1_score']  <= 1

    def test_predict_returns_risk_score(self):
        """Predict should return risk_score between 0 and 1."""
        self.trainer.train(self.X_train, self.y_train, self.feature_names)
        result = self.trainer.predict(self.X_test[:1])

        assert 'risk_score'   in result
        assert 'risk_level'   in result
        assert 'confidence'   in result
        assert 0 <= result['risk_score'] <= 1

    def test_feature_importance_sums_to_one(self):
        """Feature importances should sum to approximately 1.0."""
        self.trainer.train(self.X_train, self.y_train, self.feature_names)
        importance = self.trainer.get_feature_importance()

        total = sum(item['importance'] for item in importance)
        assert abs(total - 1.0) < 0.01  # Allow small floating point error

    def test_risk_levels_correct(self):
        """Risk levels should match score ranges."""
        self.trainer.train(self.X_train, self.y_train, self.feature_names)

        assert self.trainer._get_risk_level(0.80) == 'critical'
        assert self.trainer._get_risk_level(0.65) == 'high'
        assert self.trainer._get_risk_level(0.50) == 'medium'
        assert self.trainer._get_risk_level(0.20) == 'low'
