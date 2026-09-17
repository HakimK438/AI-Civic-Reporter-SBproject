from datetime import datetime

from pydantic import BaseModel, EmailStr

# -------------------------
# Authentication Schemas
# -------------------------

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str

# -------------------------
# Issue Schemas
# -------------------------
class IssueResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str
    category: str
    image_url: str | None
    latitude: float | None
    longitude: float | None
    severity: str | None
    severity_score: int | None
    status: str
    assigned_to: int | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True