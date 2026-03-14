# app/routes/auth.py
from fastapi import APIRouter, HTTPException, Depends
from app.models import UserSignup, UserLogin, Token, RefreshTokenRequest
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_current_user_id,
)
from app.database import execute_with_retries

router = APIRouter(prefix="/auth", tags=["Authentication"])


def run_db(operation, failure_message: str):
    try:
        return execute_with_retries(operation)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail=failure_message)

@router.post("/signup", response_model=Token)
def signup(user: UserSignup):
    """Register a new user"""
    # Check if user exists
    existing = run_db(
        lambda supabase: supabase.table('users').select("*").eq('email', user.email).execute(),
        "Database unavailable during signup"
    )
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password and create user
    hashed_pw = hash_password(user.password)
    new_user = {
        'email': user.email,
        'password_hash': hashed_pw,
        'full_name': user.full_name
    }
    
    result = run_db(
        lambda supabase: supabase.table('users').insert(new_user).execute(),
        "Database unavailable during signup"
    )
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create user")
    
    user_data = result.data[0]
    token = create_access_token({'user_id': user_data['id'], 'email': user_data['email']})
    refresh_token = create_refresh_token({'user_id': user_data['id'], 'email': user_data['email']})
    
    return {
        "access_token": token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user_data['id'],
            "email": user_data['email'],
            "full_name": user_data['full_name']
        }
    }

@router.post("/login", response_model=Token)
def login(user: UserLogin):
    """Login and get access token"""
    # Find user
    result = run_db(
        lambda supabase: supabase.table('users').select("*").eq('email', user.email).execute(),
        "Database unavailable during login"
    )
    
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user_data = result.data[0]
    
    # Verify password
    if not verify_password(user.password, user_data['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    token = create_access_token({'user_id': user_data['id'], 'email': user_data['email']})
    refresh_token = create_refresh_token({'user_id': user_data['id'], 'email': user_data['email']})
    
    return {
        "access_token": token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user_data['id'],
            "email": user_data['email'],
            "full_name": user_data['full_name']
        }
    }

@router.get("/me")
def get_current_user(user_id: str = Depends(get_current_user_id)):
    """
    Get current authenticated user's profile.
    """
    result = run_db(
        lambda supabase: supabase.table('users').select(
            "id, email, full_name, created_at"
        ).eq('id', user_id).execute(),
        "Database unavailable while loading user profile"
    )
    
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return result.data[0]


@router.post("/refresh", response_model=Token)
def refresh_access_token(payload: RefreshTokenRequest):
    """Exchange a valid refresh token for a new access token pair."""
    token_payload = verify_token(payload.refresh_token, expected_type="refresh")

    if not token_payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id = token_payload.get("user_id")
    email = token_payload.get("email")
    if not user_id or not email:
        raise HTTPException(status_code=401, detail="Invalid refresh token payload")

    result = run_db(
        lambda supabase: supabase.table('users').select("id, email, full_name").eq('id', user_id).execute(),
        "Database unavailable during token refresh"
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    user_data = result.data[0]
    new_access_token = create_access_token({'user_id': user_data['id'], 'email': user_data['email']})
    new_refresh_token = create_refresh_token({'user_id': user_data['id'], 'email': user_data['email']})

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user_data['id'],
            "email": user_data['email'],
            "full_name": user_data['full_name']
        }
    }
