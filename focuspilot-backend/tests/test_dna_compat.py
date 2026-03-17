import pytest

from app.ml.clustering.feature_extractor import SessionFeatureExtractor
from app.ml.clustering.dna_trainer import DNATrainer


class _ChainResult:
    def __init__(self, data=None):
        self.data = data if data is not None else []


class _Table:
    def __init__(self, supabase, name):
        self.supabase = supabase
        self.name = name

    def upsert(self, payload, on_conflict=None):
        self.supabase.calls.append((self.name, "upsert", on_conflict))
        if self.name == "session_clusters" and on_conflict == "user_id,session_id":
            raise Exception(
                "{'message': 'there is no unique or exclusion constraint matching the ON CONFLICT specification', 'code': '42P10'}"
            )
        if self.name == "productivity_clusters" and on_conflict == "user_id":
            raise Exception(
                "{'message': 'there is no unique or exclusion constraint matching the ON CONFLICT specification', 'code': '42P10'}"
            )
        return self

    def select(self, *_args):
        self.supabase.calls.append((self.name, "select", None))
        return self

    def eq(self, *_args):
        self.supabase.calls.append((self.name, "eq", None))
        return self

    def limit(self, *_args):
        self.supabase.calls.append((self.name, "limit", None))
        return self

    def update(self, _payload):
        self.supabase.calls.append((self.name, "update", None))
        return self

    def insert(self, _payload):
        self.supabase.calls.append((self.name, "insert", None))
        return self

    def delete(self):
        self.supabase.calls.append((self.name, "delete", None))
        return self

    def in_(self, *_args):
        self.supabase.calls.append((self.name, "in_", None))
        return self

    def execute(self):
        if self.name == "productivity_clusters" and any(
            c[0] == "productivity_clusters" and c[1] == "select"
            for c in self.supabase.calls
        ):
            return _ChainResult(data=[])
        return _ChainResult(data=[])


class _FakeSupabase:
    def __init__(self):
        self.calls = []

    def table(self, name):
        return _Table(self, name)


def test_feature_extractor_parses_high_precision_iso_timestamps(monkeypatch):
    monkeypatch.setattr(
        "app.ml.clustering.feature_extractor.get_supabase",
        lambda: _FakeSupabase(),
    )

    extractor = SessionFeatureExtractor("user-1")
    dt = extractor._parse_datetime("2026-03-05T15:01:25.358967891Z")

    assert dt.year == 2026
    assert dt.month == 3
    assert dt.day == 5
    assert dt.hour == 15
    assert dt.minute == 1
    assert dt.second == 25
    assert dt.microsecond == 358967


def test_dna_trainer_falls_back_when_on_conflict_constraint_missing(monkeypatch):
    fake = _FakeSupabase()

    monkeypatch.setattr(
        "app.ml.clustering.dna_trainer.get_supabase",
        lambda: fake,
    )

    trainer = DNATrainer("7337938a-7320-4bee-8b3f-fe556adf9c77")

    trainer._save_results(
        profiles=[{"cluster_id": 0, "name": "Test"}],
        assignments={"session-1": 0},
        insight_data={
            "peak_hours": [10],
            "best_session_length": {"minutes": 45},
            "worst_patterns": [],
            "insights": ["test"],
        },
        k=1,
        n_sessions=1,
    )

    trainer._save_session_assignments(
        session_ids=["session-1"],
        labels=[0],
        profiles=[{"cluster_id": 0, "name": "Test"}],
    )

    assert ("productivity_clusters", "insert", None) in fake.calls
    assert ("session_clusters", "delete", None) in fake.calls
    assert ("session_clusters", "insert", None) in fake.calls
