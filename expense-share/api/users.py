import uuid
from fastapi import APIRouter, HTTPException
from schema.user import UserCreate, UserResponse, UserUpdate
from database import supabase
from typing import List

router = APIRouter()

@router.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate):
    try:
        response = supabase.table('users').insert({
            "email": user.email,
            "name": user.name,
            "mobile": user.mobile
        }).execute()
        
        return response.data[0]
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error creating user: {str(e)}"
        )

@router.get("/u/{user_id}", response_model=UserResponse)
async def get_user_data(user_id: str):
    try:
        response = supabase.table('users').select("*").eq('id', user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="User not found")
            
        return response.data[0]
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error fetching user: {str(e)}"
        )

@router.get("/users", response_model=List[UserResponse])
async def list_users():
    try:
        response = supabase.table('users').select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error listing users: {str(e)}"
        )

@router.patch("/u/{user_id}", response_model=UserResponse)
async def update_user_data(user_id: str, user: UserUpdate):
    try:
        
        # Validate UUID format for user_id
        try:
            uuid_obj = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid user ID format. Must be a valid UUID."
            )

        # First check if user exists
        check_user = supabase.table('users').select("*").eq('id', str(uuid_obj)).execute()
        
        if not check_user.data:
            raise HTTPException(status_code=404, detail="User not found")

        # If user exists, proceed with update
        update_data = user.model_dump(exclude_unset=True)
        response = supabase.table('users').update(
            update_data
        ).eq('id', str(uuid_obj)).execute()
        
        return response.data[0]
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error updating user: {str(e)}"
        )