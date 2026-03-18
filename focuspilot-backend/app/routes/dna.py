# app/routes/dna.py
"""
Productivity DNA endpoints.
"""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from app.auth import get_current_user_id
from app.ml.clustering.dna_trainer import DNATrainer
from app.ml.data_extractor import DataExtractor

router = APIRouter(prefix="/dna", tags=["DNA"])


@router.post("/train")
def train_dna(
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id)
):
    """
    Train Productivity DNA in the background.
    Returns immediately with a job ID.
    """
    def _train():
        trainer = DNATrainer(user_id)
        trainer.train()

    background_tasks.add_task(_train)

    return {
        'message': 'DNA training started in background',
        'status':  'training'
    }


@router.post("/train/sync")
def train_dna_sync(user_id: str = Depends(get_current_user_id)):
    """
    Train Productivity DNA synchronously.
    Waits for training to complete and returns result.
    """
    trainer = DNATrainer(user_id)

    try:
        result = trainer.train()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Training failed: {str(e)}"
        )


@router.get("/results")
def get_dna_results(user_id: str = Depends(get_current_user_id)):
    """
    Get existing Productivity DNA results.
    Returns None if not yet trained.
    """
    trainer = DNATrainer(user_id)
    dna     = trainer.get_existing_dna()

    if not dna:
        return {
            'trained':  False,
            'message':  (
                'No DNA trained yet. '
                'Complete at least 5 sessions then call POST /dna/train'
            )
        }

    heatmap_data = trainer.get_heatmap_data(dna)

    return {
        'trained':             True,
        'n_clusters':          dna.get('n_clusters'),
        'n_sessions':          dna.get('sessions_analyzed'),
        'cluster_profiles':    dna.get('cluster_profiles', []),
        'peak_hours':          dna.get('peak_hours', []),
        'best_session_length': dna.get('best_session_length', {}),
        'worst_patterns':      dna.get('worst_patterns', []),
        'insights':            dna.get('insights', []),
        'heatmap_data':        heatmap_data,
        'trained_at':          dna.get('trained_at')
    }


@router.get("/clusters")
def get_cluster_profiles(user_id: str = Depends(get_current_user_id)):
    """Get just the cluster profiles."""
    trainer = DNATrainer(user_id)
    dna     = trainer.get_existing_dna()

    if not dna:
        raise HTTPException(
            status_code=404,
            detail='DNA not trained yet'
        )

    return {
        'clusters': dna.get('cluster_profiles', []),
        'total':    dna.get('n_clusters', 0)
    }


@router.get("/insights")
def get_insights(user_id: str = Depends(get_current_user_id)):
    """Get just the insights."""
    trainer = DNATrainer(user_id)
    dna     = trainer.get_existing_dna()

    if not dna:
        raise HTTPException(
            status_code=404,
            detail='DNA not trained yet'
        )

    return {
        'insights':            dna.get('insights', []),
        'peak_hours':          dna.get('peak_hours', []),
        'best_session_length': dna.get('best_session_length', {}),
        'worst_patterns':      dna.get('worst_patterns', [])
    }


@router.get("/eligibility")
def get_dna_eligibility(user_id: str = Depends(get_current_user_id)):
    """Return a quick summary of whether user can train DNA now."""
    summary = DataExtractor(user_id).get_data_summary()
    required = DNATrainer.MIN_SESSIONS
    completed = summary.get('completed_sessions', 0)

    return {
        'can_train': completed >= required,
        'required_sessions': required,
        'completed_sessions': completed,
        'remaining_sessions': max(0, required - completed),
        'total_sessions': summary.get('total_sessions', 0),
        'days_of_data': summary.get('days_of_data', 0)
    }
