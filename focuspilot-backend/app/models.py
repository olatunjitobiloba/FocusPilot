# app/models.py
from pydantic import BaseModel, EmailStr, Field
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
    refresh_token: str
    token_type: str
    user: dict


class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Session models
class SessionStart(BaseModel):
    planned_duration: int = Field(25, ge=1, le=240)  # minutes

class SessionEnd(BaseModel):
    session_id: str
    focus_score: int = Field(..., ge=0, le=10)  # 0-10
    distraction_count: int = Field(0, ge=0, le=10000)
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
