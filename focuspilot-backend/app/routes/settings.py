# app/routes/settings.py
from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user_id
from app.database import get_supabase

router = APIRouter(prefix="/settings", tags=["Settings"])

DEFAULT_SETTINGS = {
    "notifications_enabled": True,
    "agent_sensitivity":     "medium",
    "auto_start_sessions":   False,
    "session_duration_mins": 25,
    "break_duration_mins":   5,
    "daily_goal_hours":      4,
    "quiet_hours_start":     22,
    "quiet_hours_end":       8,
    "theme":                 "system"
}

@router.get("/")
def get_settings(user_id: str = Depends(get_current_user_id)):
    supabase = get_supabase()
    result   = supabase.table('user_settings').select("*").eq('user_id', user_id).execute()

    if not result.data:
        # Return defaults for new user
        return DEFAULT_SETTINGS

    # Merge with defaults (in case new settings were added)
    saved = result.data[0].get('settings') or {}
    return {**DEFAULT_SETTINGS, **saved}

@router.put("/")
def update_settings(
    new_settings: dict,
    user_id: str = Depends(get_current_user_id)
):
    supabase = get_supabase()

    try:
        # Get existing settings
        result = supabase.table('user_settings').select("*").eq('user_id', user_id).execute()

        if result.data:
            # Merge defaults + current + incoming so missing keys remain stable.
            current = result.data[0].get('settings') or {}
            merged  = {**DEFAULT_SETTINGS, **current, **new_settings}
            supabase.table('user_settings').update({
                'settings': merged
            }).eq('user_id', user_id).execute()
        else:
            # Create new settings row
            merged = {**DEFAULT_SETTINGS, **new_settings}
            supabase.table('user_settings').insert({
                'user_id':  user_id,
                'settings': merged
            }).execute()

        return {"message": "Settings saved", "settings": merged}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to save settings: {str(exc)}")
