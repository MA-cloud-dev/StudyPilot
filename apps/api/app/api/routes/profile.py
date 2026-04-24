from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import get_db
from app.models import UserProfileEntity
from app.schemas.common import ErrorResponse
from app.schemas.profile import UserProfile, UserProfileCreate

router = APIRouter()


@router.get("", response_model=UserProfile, responses={404: {"model": ErrorResponse}})
def get_profile(db: Session = Depends(get_db)) -> UserProfile:
    profile = db.scalar(select(UserProfileEntity).limit(1))
    if profile is None:
        raise AppError(status_code=404, code="PROFILE_NOT_FOUND", message="Learner profile has not been created yet.")
    return UserProfile.model_validate(profile)


@router.post("", response_model=UserProfile)
def upsert_profile(payload: UserProfileCreate, db: Session = Depends(get_db)) -> UserProfile:
    profile = db.scalar(select(UserProfileEntity).limit(1))
    now = datetime.now(timezone.utc)
    if profile is None:
        profile = UserProfileEntity(created_at=now, updated_at=now, **payload.model_dump())
        db.add(profile)
    else:
        for key, value in payload.model_dump().items():
            setattr(profile, key, value)
        profile.updated_at = now
    db.commit()
    db.refresh(profile)
    return UserProfile.model_validate(profile)
