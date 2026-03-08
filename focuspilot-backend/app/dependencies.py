# app/dependencies.py
from fastapi import Depends, HTTPException, Header
from app.auth import verify_token
from app.database import get_supabase as _get_supabase

def get_current_user_id(authorization: str = Header(None)) -> str:
    """
    Extract and verify the current user ID from JWT token in Authorization header.
    Used as a FastAPI dependency.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return payload.get("user_id")

def get_supabase():
    """
    Get Supabase client instance.
    """
    return _get_supabase()
