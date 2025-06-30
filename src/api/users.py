from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import secrets

from .. import models
from ..utils.database import get_db
from . import security

router = APIRouter(
    prefix="/api/v1/users",
    tags=["Users"],
    dependencies=[Depends(security.get_current_user)]
)

@router.get("/me", response_model=models.schemas.User)
async def read_users_me(current_user: models.database.User = Depends(security.get_current_user)):
    """
    Get the current logged-in user's profile.
    """
    return current_user

@router.post("/me/api-key", status_code=status.HTTP_201_CREATED)
async def create_api_key_for_user(
    current_user: models.database.User = Depends(security.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a new API key for the current user.
    """
    new_key = secrets.token_urlsafe(32)
    api_key = models.database.APIKey(
        key=new_key,
        owner=current_user,
        description="User generated key"
    )
    db.add(api_key)
    await db.commit()
    return {"api_key": new_key}