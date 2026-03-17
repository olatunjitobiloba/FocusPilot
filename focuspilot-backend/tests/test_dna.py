# tests/test_dna.py
"""Tests for Productivity DNA clustering."""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock


class TestProductivityClusterer:

    def test_fit_returns_labels_and_k(self):
        from app.ml.clustering.clusterer import ProductivityClusterer

        X = np.random.rand(20, 15).astype(np.float32)
        X[:, 3] = np.random.uniform(1, 10, 20)   # focus_score

        clusterer = ProductivityClusterer()
        labels, k = clusterer.fit(X)

        assert len(labels) == 20
        assert 2 <= k <= 5
        assert set(labels).issubset(set(range(k)))

    def test_labels_cover_all_sessions(self):
        from app.ml.clustering.clusterer import ProductivityClusterer

        X      = np.random.rand(15, 15).astype(np.float32)
        clust  = ProductivityClusterer()
        labels, k = clust.fit(X)

        assert len(labels) == len(X)

    def test_profile_clusters_returns_correct_count(self):
        from app.ml.clustering.clusterer import ProductivityClusterer

        X = np.random.rand(20, 15).astype(np.float32)
        X[:, 3] = np.random.uniform(1, 10, 20)

        clust          = ProductivityClusterer()
        labels, k      = clust.fit(X)
        profiles       = clust.profile_clusters(X, labels)

        assert len(profiles) == k

    def test_profile_has_required_fields(self):
        from app.ml.clustering.clusterer import ProductivityClusterer

        X = np.random.rand(20, 15).astype(np.float32)
        X[:, 3] = np.random.uniform(1, 10, 20)

        clust     = ProductivityClusterer()
        labels, k = clust.fit(X)
        profiles  = clust.profile_clusters(X, labels)

        required = [
            'cluster_id', 'name', 'n_sessions',
            'quality_score', 'color', 'characteristics'
        ]
        for field in required:
            assert field in profiles[0], f"Missing: {field}"

    def test_quality_score_bounded(self):
        from app.ml.clustering.clusterer import ProductivityClusterer

        X = np.random.rand(20, 15).astype(np.float32)
        X[:, 3] = np.random.uniform(1, 10, 20)

        clust     = ProductivityClusterer()
        labels, k = clust.fit(X)
        profiles  = clust.profile_clusters(X, labels)

        for p in profiles:
            assert 0 <= p['quality_score'] <= 100

    def test_profiles_sorted_by_quality_desc(self):
        from app.ml.clustering.clusterer import ProductivityClusterer

        X = np.random.rand(30, 15).astype(np.float32)
        X[:, 3] = np.random.uniform(1, 10, 30)

        clust     = ProductivityClusterer()
        labels, k = clust.fit(X)
        profiles  = clust.profile_clusters(X, labels)

        scores = [p['quality_score'] for p in profiles]
        assert scores == sorted(scores, reverse=True)


class TestInsightGenerator:

    def _make_data(self, n=20):
        from app.ml.clustering.clusterer import ProductivityClusterer

        X = np.random.rand(n, 15).astype(np.float32)
        X[:, 3] = np.random.uniform(1, 10, n)
        X[:, 0] = np.random.randint(0, 24, n)
        X[:, 1] = np.random.randint(0, 7, n)
        X[:, 2] = np.random.uniform(10, 90, n)
        X[:, 7] = np.random.randint(0, 2, n)

        clust     = ProductivityClusterer()
        labels, k = clust.fit(X)
        profiles  = clust.profile_clusters(X, labels)
        return X, labels, profiles

    def test_generate_all_returns_required_keys(self):
        from app.ml.clustering.insight_generator import InsightGenerator

        X, labels, profiles = self._make_data()
        gen    = InsightGenerator()
        result = gen.generate_all(X, labels, profiles, [])

        required = [
            'peak_hours', 'best_session_length',
            'worst_patterns', 'insights', 'heatmap_data'
        ]
        for key in required:
            assert key in result, f"Missing: {key}"

    def test_insights_not_empty(self):
        from app.ml.clustering.insight_generator import InsightGenerator

        X, labels, profiles = self._make_data()
        gen    = InsightGenerator()
        result = gen.generate_all(X, labels, profiles, [])

        assert len(result['insights']) > 0

    def test_heatmap_has_hour_and_day(self):
        from app.ml.clustering.insight_generator import InsightGenerator

        X, labels, profiles = self._make_data()
        gen    = InsightGenerator()
        result = gen.generate_all(X, labels, profiles, [])

        if result['heatmap_data']:
            cell = result['heatmap_data'][0]
            assert 'hour'    in cell
            assert 'day'     in cell
            assert 'quality' in cell

    def test_best_session_length_has_avg(self):
        from app.ml.clustering.insight_generator import InsightGenerator

        X, labels, profiles = self._make_data()
        gen    = InsightGenerator()
        result = gen.generate_all(X, labels, profiles, [])

        bsl = result['best_session_length']
        assert 'avg_minutes' in bsl


# Run tests
# pytest tests/test_dna.py -v
