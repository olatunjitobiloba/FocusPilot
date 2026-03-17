# app/ml/clustering/dna_trainer.py
"""
DNA Trainer — orchestrates the full Productivity DNA pipeline.

Steps:
1. Extract features from all sessions
2. Run K-Means clustering
3. Profile each cluster
4. Generate insights
5. Save results to Supabase
"""

from datetime import datetime
from typing import Dict, Any
from app.ml.clustering.feature_extractor import SessionFeatureExtractor
from app.ml.clustering.clusterer         import ProductivityClusterer
from app.ml.clustering.insight_generator import InsightGenerator
from app.database import get_supabase


class DNATrainer:

    MIN_SESSIONS = 5

    def __init__(self, user_id: str):
        self.user_id   = user_id
        self.extractor = SessionFeatureExtractor(user_id)
        self.clusterer = ProductivityClusterer()
        self.insights  = InsightGenerator()
        self.supabase  = get_supabase()

    def train(self) -> Dict[str, Any]:
        """
        Run the full Productivity DNA pipeline.

        Returns complete DNA result dict.
        """
        print(f"\n🧬 Training Productivity DNA for {self.user_id[:8]}")
        start = datetime.utcnow()

        # ── Step 1: Extract features ───────────────────────────────────
        print("   📊 Extracting session features...")
        X, sessions, session_ids = self.extractor.extract_all_sessions(
            min_sessions=self.MIN_SESSIONS
        )

        # ── Step 2: Cluster ────────────────────────────────────────────
        print("   🔢 Running K-Means clustering...")
        labels, k = self.clusterer.fit(X)

        # ── Step 3: Profile clusters ───────────────────────────────────
        print("   🏷️  Profiling clusters...")
        profiles = self.clusterer.profile_clusters(X, labels)

        # ── Step 4: Generate insights ──────────────────────────────────
        print("   💡 Generating insights...")
        insight_data = self.insights.generate_all(
            X=X,
            labels=labels,
            profiles=profiles,
            sessions=sessions
        )

        # ── Step 5: Build session assignments ─────────────────────────
        assignments = {
            session_ids[i]: int(labels[i])
            for i in range(len(session_ids))
        }

        # ── Step 6: Save to DB ─────────────────────────────────────────
        print("   💾 Saving to database...")
        self._save_results(
            profiles=profiles,
            assignments=assignments,
            insight_data=insight_data,
            k=k,
            n_sessions=len(sessions)
        )

        self._save_session_assignments(
            session_ids=session_ids,
            labels=labels,
            profiles=profiles
        )

        duration_ms = round(
            (datetime.utcnow() - start).total_seconds() * 1000
        )

        result = {
            'status':           'success',
            'n_clusters':       k,
            'n_sessions':       len(sessions),
            'cluster_profiles': profiles,
            'peak_hours':       insight_data['peak_hours'],
            'best_session_length': insight_data['best_session_length'],
            'worst_patterns':   insight_data['worst_patterns'],
            'insights':         insight_data['insights'],
            'heatmap_data':     insight_data['heatmap_data'],
            'trained_at':       datetime.utcnow().isoformat(),
            'duration_ms':      duration_ms
        }

        print(
            f"   ✅ DNA trained in {duration_ms}ms | "
            f"{k} clusters | {len(sessions)} sessions"
        )

        return result

    def _save_results(
        self,
        profiles: list,
        assignments: dict,
        insight_data: dict,
        k: int,
        n_sessions: int
    ):
        """Save DNA results to productivity_clusters table."""
        self.supabase.table('productivity_clusters').upsert({
            'user_id':            self.user_id,
            'n_clusters':         k,
            'cluster_profiles':   profiles,
            'session_assignments': assignments,
            'peak_hours':         insight_data['peak_hours'],
            'best_session_length': insight_data['best_session_length'],
            'worst_patterns':     insight_data['worst_patterns'],
            'insights':           insight_data['insights'],
            'trained_at':         datetime.utcnow().isoformat(),
            'sessions_analyzed':  n_sessions
        }).execute()

    def _save_session_assignments(
        self,
        session_ids: list,
        labels,
        profiles: list
    ):
        """Save per-session cluster assignments."""
        # Build name map
        name_map = {p['cluster_id']: p['name'] for p in profiles}

        rows = [
            {
                'user_id':       self.user_id,
                'session_id':    session_ids[i],
                'cluster_label': int(labels[i]),
                'cluster_name':  name_map.get(int(labels[i]), 'Unknown')
            }
            for i in range(len(session_ids))
        ]

        # Upsert in batches of 50
        for i in range(0, len(rows), 50):
            batch = rows[i:i+50]
            self.supabase.table('session_clusters').upsert(
                batch,
                on_conflict='user_id,session_id'
            ).execute()

    def get_existing_dna(self) -> Dict | None:
        """Get previously trained DNA (no retraining)."""
        result = (
            self.supabase
            .table('productivity_clusters')
            .select("*")
            .eq('user_id', self.user_id)
            .execute()
        )
        return result.data[0] if result.data else None
