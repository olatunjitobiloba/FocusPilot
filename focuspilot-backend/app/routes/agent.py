# app/routes/agent.py
from fastapi import APIRouter, Depends
from app.auth import get_current_user_id
from app.database import get_supabase
from datetime import datetime

router = APIRouter(prefix="/agent", tags=["Agent"])

@router.get("/state")
def get_agent_state(user_id: str = Depends(get_current_user_id)):
    supabase = get_supabase()
    
    # Get or create agent state
    result = supabase.table('agent_state').select("*").eq('user_id', user_id).execute()
    
    if not result.data:
        # Initialize agent state
        initial_state = {
            'user_id': user_id,
            'state': {
                'monitoring': True,
                'idle_minutes': 0,
                'last_activity': None,
                'current_risk': 0.0
            },
            'risk_score': 0.0,
            'last_intervention': None
        }
        supabase.table('agent_state').insert(initial_state).execute()
        return initial_state
    
    return result.data[0]

@router.post("/update-state")
def update_agent_state(
    state_data: dict,
    user_id: str = Depends(get_current_user_id)
):
    supabase = get_supabase()
    
    # Update agent state
    result = supabase.table('agent_state').update({
        'state': state_data,
        'updated_at': datetime.utcnow().isoformat()
    }).eq('user_id', user_id).execute()
    
    return {"message": "State updated", "data": result.data}
