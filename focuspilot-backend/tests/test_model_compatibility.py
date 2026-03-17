from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.ml.model_manager import ModelManager
from app.routes import predictions
from app.auth import get_current_user_id


def test_model_manager_marks_retrain_required_when_load_fails(monkeypatch):
    manager = ModelManager()
    user_id = "7337938a-7320-4bee-8b3f-fe556adf9c77"
    user_key = user_id[:8]

    manager.invalidate(user_id)

    monkeypatch.setattr("os.path.exists", lambda path: "procrastination_model.pkl" in str(path))

    def _boom(self, model_dir="app/ml/models"):
        raise ModuleNotFoundError("No module named 'numpy._core.numeric'")

    monkeypatch.setattr("app.ml.model_trainer.ModelTrainer.load", _boom)

    result = manager.predict(user_id, X=None)

    assert result["model_available"] is False
    assert result["retrain_required"] is True
    assert result["error_code"] == "model_load_failed"
    assert "numpy._core.numeric" in result["model_error"]

    manager._models.pop(user_key, None)
    manager._load_errors.pop(user_key, None)


def test_risk_endpoint_self_heals_when_model_retrain_required(monkeypatch):
    app = FastAPI()
    app.include_router(predictions.router)
    app.dependency_overrides[get_current_user_id] = (
        lambda: "7337938a-7320-4bee-8b3f-fe556adf9c77"
    )

    class _SupabaseStub:
        def table(self, *_args, **_kwargs):
            return self

        def select(self, *_args, **_kwargs):
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def is_(self, *_args, **_kwargs):
            return self

        def execute(self):
            class _R:
                data = []
            return _R()

    class _Builder:
        def __init__(self, *args, **kwargs):
            pass

        def build_inference_row(self, *_args, **_kwargs):
            return [[0.0] * 15]

    monkeypatch.setattr("app.routes.predictions.get_supabase", lambda: _SupabaseStub())
    monkeypatch.setattr("app.routes.predictions.DatasetBuilder", _Builder)
    monkeypatch.setattr("app.routes.predictions.model_manager.has_model", lambda _user_id: True)
    monkeypatch.setattr(
        "app.routes.predictions.model_manager.predict",
        lambda _user_id, _x: {
            "model_available": False,
            "retrain_required": True,
            "model_error": "No module named 'numpy._core.numeric'",
            "risk_score": 0.3,
        },
    )

    client = TestClient(app)
    response = client.get(
        "/predictions/risk",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["model_refreshing"] is True
    assert data["model_available"] is False
    assert data["fallback_source"] in ["agent_state", "static_default"]

    app.dependency_overrides.clear()
