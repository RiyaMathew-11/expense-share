from pydantic import BaseModel, EmailStr, StringConstraints
from typing import Optional, Annotated

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    mobile: Annotated[str, StringConstraints(pattern=r'^\+?91?\d{10}$')]

class UserResponse(BaseModel):
    # Todo: remove email and mobile from response
    email: EmailStr
    name: str
    mobile: Annotated[str, StringConstraints(pattern=r'^\+?91?\d{10}$')]

class UserUpdate(BaseModel):
    name: Optional[str] = None
    mobile: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Name",
                "mobile": "+1234567890"
            }
        }
