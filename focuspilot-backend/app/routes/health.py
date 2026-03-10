# app/routes/health.py
"""
Health check endpoint.
Used by Hugging Face Spaces to verify the app is running.
Also useful for debugging deployment issues.
"""

from fastapi import APIRouter
from app.database import get_supabase, execute_with_retries
from datetime import datetime
import os

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
def health_check():
    """Basic health check — is the server running?"""
    return {
        "status":    "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version":   "1.0.0"
    }


@router.get("/detailed")
def detailed_health_check():
    """
    Detailed health check — checks all dependencies.
    Use this to debug deployment issues.
    """
    checks = {}
    overall_status = "healthy"

    # ── Check 1: Database connection ──────────────────────────────────
    try:
        supabase = get_supabase()
        # Simple query to verify connection
        execute_with_retries(
            lambda db: db.table('users').select("id").limit(1).execute()
        )
        checks["database"] = {
            "status":  "healthy",
            "message": "Connected to Supabase"
        }
    except Exception as e:
        checks["database"] = {
            "status":  "unhealthy",
            "message": f"Database error: {str(e)}"
        }
        overall_status = "degraded"

    # ── Check 2: Environment variables ────────────────────────────────
    required_env_vars = ["SUPABASE_URL", "SUPABASE_KEY", "JWT_SECRET"]
    missing_vars = [v for v in required_env_vars if not os.getenv(v)]

    if missing_vars:
        checks["environment"] = {
            "status":  "unhealthy",
            "message": f"Missing env vars: {', '.join(missing_vars)}"
        }
        overall_status = "degraded"
    else:
        checks["environment"] = {
            "status":  "healthy",
            "message": "All environment variables set"
        }

    # ── Check 3: ML module ────────────────────────────────────────────
    try:
        from app.ml.distraction_scorer import DistractionScorer
        scorer = DistractionScorer()
        checks["ml_module"] = {
            "status":  "healthy",
            "message": "DistractionScorer loaded"
        }
    except Exception as e:
        checks["ml_module"] = {
            "status":  "unhealthy",
            "message": f"ML module error: {str(e)}"
        }
        overall_status = "degraded"

    return {
        "status":    overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks":    checks
    }
