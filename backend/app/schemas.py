from pydantic import BaseModel, EmailStr, Field, field_validator

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=10, max_length=128)

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    username: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class AnalysisRequest(BaseModel):
    module_id: str
    task: str = Field(default="default", max_length=100)
    input_name: str | None = Field(default=None, max_length=255)
