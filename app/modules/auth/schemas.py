from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=40, max_length=200)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    full_name: str | None
    phone: str | None
    created_at: datetime


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    phone: str | None = Field(default=None, min_length=7, max_length=32)


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    organization_type: str = Field(default="business", pattern="^(business|enterprise|individual)$")


class OrganizationUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=200)


class OrganizationResponse(BaseModel):
    id: str
    name: str
    organization_type: str
    role: str
    created_at: datetime


class OrganizationMemberAdd(BaseModel):
    email: EmailStr
    role: str = Field(default="member", pattern="^(admin|member|merchant_staff|enterprise_user)$")


class OrganizationMemberUpdate(BaseModel):
    role: str = Field(pattern="^(admin|member|merchant_staff|enterprise_user)$")


class OrganizationMemberResponse(BaseModel):
    user_id: str
    email: EmailStr
    role: str
    created_at: datetime
