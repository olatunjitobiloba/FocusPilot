# app/routes/ml_data.py
"""
ML Data endpoints — expose data pipeline status and dataset info.
These are used by the frontend to show data readiness.
"""

from fastapi import APIRouter, Depends, BackgroundTasks
from app.auth import get_current_user_id
from app.ml.dataset_builder import DatasetBuilder
import os

router = APIRouter(prefix="/ml", tags=["ML Data"])


@router.get("/data-status")
def get_data_status(user_id: str = Depends(get_current_user_id)):
    """
    Check if user has enough data for ML training.
    Frontend uses this to show "collecting data" vs "model ready" state.
    """
    from app.ml.data_extractor import DataExtractor

    extractor = DataExtractor(user_id)
    summary   = extractor.get_data_summary()

    # Progress toward ML readiness
    sessions_needed = 20   # Recommended for good accuracy
    sessions_have   = summary['completed_sessions']
    progress_pct    = min(100, int((sessions_have / sessions_needed) * 100))

    return {
        'data_summary':       summary,
        'progress_pct':       progress_pct,
        'sessions_needed':    sessions_needed,
        'sessions_have':      sessions_have,
        'sessions_remaining': max(0, sessions_needed - sessions_have),
        'status': (
            'ready'       if summary['recommended_data'] else
            'minimum'     if summary['has_enough_data']  else
            'collecting'
        ),
        'message': (
            '🟢 Model ready for high-accuracy predictions'
            if summary['recommended_data'] else
            '🟡 Model can train but more data = better accuracy'
            if summary['has_enough_data'] else
            f'🔴 Need {max(0, 5 - sessions_have)} more sessions to enable ML'
        )
    }


@router.get("/feature-preview")
def get_feature_preview(user_id: str = Depends(get_current_user_id)):
    """
    Preview the feature engineering output.
    Shows what the ML model will see.
    Useful for debugging and transparency.
    """
    builder = DatasetBuilder(user_id=user_id, days_back=30)
    dataset = builder.build()

    if 'error' in dataset:
        return dataset

    # Return latest feature row as a concise preview sample.
    feature_rows = dataset['feature_rows'][-1:]

    # Remove internal metadata fields
    clean_rows = []
    for row in feature_rows:
        clean_row = {
            k: v for k, v in row.items()
            if not k.startswith('_')
        }
        clean_rows.append(clean_row)

    return {
        'feature_names':  dataset['feature_names'],
        'sample_rows':    clean_rows,
        'total_rows':     len(dataset['feature_rows']),
        'label_balance':  dataset['label_balance']
    }


@router.post("/build-dataset")
def build_dataset(
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id)
):
    """
    Trigger dataset build in the background.
    Returns immediately, builds in background.
    Frontend polls /ml/data-status to check progress.
    """
    def _build():
        builder = DatasetBuilder(user_id=user_id)
        result  = builder.build()

        if 'error' not in result:
            print(f"✅ Dataset built for user {user_id[:8]}: "
                  f"{len(result['feature_rows'])} rows")
        else:
            print(f"⚠️  Dataset build failed: {result.get('message')}")

    background_tasks.add_task(_build)

    return {
        'message': 'Dataset build started in background',
        'status':  'building'
    }
