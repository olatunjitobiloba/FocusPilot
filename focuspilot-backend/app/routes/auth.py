# app/routes/auth.py
from fastapi import APIRouter, HTTPException, Depends
from app.models import UserSignup, UserLogin, Token
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user_id,
)
from app.database import get_supabase

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=Token)
def signup(user: UserSignup):
    """Register a new user"""
    supabase = get_supabase()
    
    # Check if user exists
    existing = supabase.table('users').select("*").eq('email', user.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password and create user
    hashed_pw = hash_password(user.password)
    new_user = {
        'email': user.email,
        'password_hash': hashed_pw,
        'full_name': user.full_name
    }
    
    result = supabase.table('users').insert(new_user).execute()
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create user")
    
    user_data = result.data[0]
    token = create_access_token({'user_id': user_data['id'], 'email': user_data['email']})
    
    return {
        "access_token": token,
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
    supabase = get_supabase()
    
    # Find user
    result = supabase.table('users').select("*").eq('email', user.email).execute()
    
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user_data = result.data[0]
    
    # Verify password
    if not verify_password(user.password, user_data['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    token = create_access_token({'user_id': user_data['id'], 'email': user_data['email']})
    
    return {
        "access_token": token,
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
    supabase = get_supabase()
    result = supabase.table('users').select(
        "id, email, full_name, created_at"
    ).eq('id', user_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return result.data[0]
