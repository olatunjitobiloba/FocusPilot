# app/models.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# Authentication models
class UserSignup(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

# Session models
class SessionStart(BaseModel):
    planned_duration: int = 25  # minutes

class SessionEnd(BaseModel):
    session_id: str
    focus_score: int  # 1-10
    distraction_count: int = 0
    notes: Optional[str] = None

class Session(BaseModel):
    id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_minutes: Optional[int]
    focus_score: Optional[int]
    distraction_count: int

# Activity models
class ActivityLog(BaseModel):
    url: str
    domain: str
    duration_seconds: int

class BlocklistItem(BaseModel):
    domain: str
    reason: Optional[str] = None
