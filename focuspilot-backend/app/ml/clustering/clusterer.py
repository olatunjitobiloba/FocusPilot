# app/ml/clustering/clusterer.py
"""
K-Means Clusterer — finds behavioral patterns in sessions.

Uses scikit-learn KMeans with:
- Automatic K selection (elbow method)
- Feature scaling (StandardScaler)
- Cluster profiling (what makes each cluster unique)
- Cluster naming (Deep Focus, Struggling, etc.)
"""

import numpy as np
from sklearn.cluster     import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics     import silhouette_score
from typing import Dict, List, Tuple, Any
import warnings
warnings.filterwarnings('ignore')

from app.ml.clustering.feature_extractor import FEATURE_NAMES


# Cluster name templates based on characteristics
CLUSTER_NAMES = {
    'deep_focus':    'Deep Focus',
    'moderate':      'Moderate Focus',
    'struggling':    'Struggling',
    'distracted':    'Highly Distracted',
    'short_burst':   'Short Burst',
    'marathon':      'Marathon Session'
}


class ProductivityClusterer:

    MIN_CLUSTERS = 2
    MAX_CLUSTERS = 5

    def __init__(self):
        self.scaler  = StandardScaler()
        self.model   = None
        self.k       = None
        self.labels_ = None

    # ── Main fit method ────────────────────────────────────────────────

    def fit(
        self,
        X: np.ndarray
    ) -> Tuple[np.ndarray, int]:
        """
        Fit K-Means to session features.

        Automatically selects best K using silhouette score.

        Args:
            X: Feature matrix (n_sessions × n_features)

        Returns:
            labels: Cluster assignment per session
            k:      Number of clusters chosen
        """
        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Select best K
        self.k = self._select_k(X_scaled)

        print(f"   🔢 Selected K={self.k} clusters")

        # Final fit
        self.model = KMeans(
            n_clusters=self.k,
            init='k-means++',
            n_init=20,
            max_iter=500,
            random_state=42
        )

        self.labels_ = self.model.fit_predict(X_scaled)

        # Compute silhouette score
        if self.k > 1:
            score = silhouette_score(X_scaled, self.labels_)
            print(f"   📊 Silhouette score: {score:.3f}")

        return self.labels_, self.k

    def _select_k(self, X_scaled: np.ndarray) -> int:
        """
        Select optimal K using silhouette score.
        Tries K = 2, 3, 4, 5 and picks the best.
        """
        n_samples = X_scaled.shape[0]

        # Can't have more clusters than samples
        max_k = min(self.MAX_CLUSTERS, n_samples - 1)
        min_k = min(self.MIN_CLUSTERS, max_k)

        if min_k == max_k:
            return min_k

        best_k     = min_k
        best_score = -1

        for k in range(min_k, max_k + 1):
            km = KMeans(
                n_clusters=k,
                init='k-means++',
                n_init=10,
                random_state=42
            )
            labels = km.fit_predict(X_scaled)

            if len(set(labels)) < 2:
                continue

            score = silhouette_score(X_scaled, labels)

            if score > best_score:
                best_score = score
                best_k     = k

        return best_k

    def profile_clusters(
        self,
        X: np.ndarray,
        labels: np.ndarray
    ) -> List[Dict[str, Any]]:
        """
        Build a profile for each cluster.

        For each cluster, compute:
        - Mean of each feature
        - Size (number of sessions)
        - Name (based on characteristics)
        - Color (for UI display)
        - Key characteristics
        """
        profiles = []
        colors   = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

        for cluster_id in range(self.k):
            mask       = labels == cluster_id
            cluster_X  = X[mask]
            n_sessions = int(mask.sum())

            if n_sessions == 0:
                continue

            # Compute mean feature values
            means = cluster_X.mean(axis=0)
            feature_means = {
                name: round(float(means[i]), 3)
                for i, name in enumerate(FEATURE_NAMES)
            }

            # Name and describe the cluster
            name, characteristics = self._name_cluster(
                feature_means,
                n_sessions
            )

            # Compute quality score (0-100)
            quality = self._compute_quality_score(feature_means)

            profiles.append({
                'cluster_id':      cluster_id,
                'name':            name,
                'n_sessions':      n_sessions,
                'pct_of_total':    round(n_sessions / len(labels) * 100, 1),
                'quality_score':   quality,
                'color':           colors[cluster_id % len(colors)],
                'feature_means':   feature_means,
                'characteristics': characteristics,
                'avg_focus_score': round(feature_means['focus_score'], 1),
                'avg_duration':    round(feature_means['duration_minutes'], 1),
                'avg_distraction': round(
                    feature_means['distraction_ratio'] * 100, 1
                ),
                'peak_hour':       self._get_peak_hour(cluster_X)
            })

        # Sort by quality score descending
        profiles.sort(key=lambda p: p['quality_score'], reverse=True)

        return profiles

    def _name_cluster(
        self,
        means: Dict[str, float],
        n_sessions: int
    ) -> Tuple[str, List[str]]:
        """
        Name a cluster based on its feature means.
        Returns (name, list_of_characteristics).
        """
        focus_score       = means['focus_score']
        distraction_ratio = means['distraction_ratio']
        duration          = means['duration_minutes']
        completed         = means['session_completed']
        productive_ratio  = means['productive_ratio']

        characteristics = []

        # ── Determine name ─────────────────────────────────────────────
        if focus_score >= 7.5 and distraction_ratio < 0.20:
            name = 'Deep Focus'
            characteristics.append('High focus score (≥7.5)')
            characteristics.append('Very low distraction (<20%)')

        elif focus_score >= 6.0 and distraction_ratio < 0.40:
            name = 'Moderate Focus'
            characteristics.append('Good focus score (≥6.0)')
            characteristics.append('Moderate distraction (<40%)')

        elif distraction_ratio >= 0.60:
            name = 'Highly Distracted'
            characteristics.append('Very high distraction (≥60%)')
            characteristics.append('Low productive time')

        elif focus_score < 5.0:
            name = 'Struggling'
            characteristics.append('Low focus score (<5.0)')
            characteristics.append('Difficulty maintaining attention')

        elif duration < 20:
            name = 'Short Burst'
            characteristics.append('Short sessions (<20 min)')
            characteristics.append('Quick focused sprints')

        elif duration > 60:
            name = 'Marathon Session'
            characteristics.append('Long sessions (>60 min)')
            characteristics.append('Extended work periods')

        else:
            name = 'Mixed Focus'
            characteristics.append('Variable focus patterns')

        # ── Add more characteristics ───────────────────────────────────
        if means['is_morning'] > 0.6:
            characteristics.append('Mostly morning sessions')
        elif means['is_evening'] > 0.6:
            characteristics.append('Mostly evening sessions')

        if means['is_weekend'] > 0.6:
            characteristics.append('Mostly weekend sessions')
        elif means['is_weekend'] < 0.2:
            characteristics.append('Mostly weekday sessions')

        if completed > 0.8:
            characteristics.append('High completion rate (>80%)')
        elif completed < 0.4:
            characteristics.append('Low completion rate (<40%)')

        if productive_ratio > 0.5:
            characteristics.append('High productive site usage')

        return name, characteristics[:4]   # Max 4 characteristics

    def _compute_quality_score(
        self,
        means: Dict[str, float]
    ) -> int:
        """
        Compute a 0-100 quality score for a cluster.
        Higher = better focus pattern.
        """
        score = 0

        # Focus score (max 40 points)
        score += min(40, means['focus_score'] * 4)

        # Low distraction (max 30 points)
        score += max(0, 30 - means['distraction_ratio'] * 50)

        # Completion rate (max 20 points)
        score += means['session_completed'] * 20

        # Productive ratio (max 10 points)
        score += means['productive_ratio'] * 10

        return round(min(100, max(0, score)))

    def _get_peak_hour(self, cluster_X: np.ndarray) -> int:
        """Get the most common hour for sessions in this cluster."""
        hours = cluster_X[:, 0].astype(int)   # hour_of_day is index 0
        if len(hours) == 0:
            return 9
        counts = np.bincount(hours, minlength=24)
        return int(counts.argmax())
