from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from ..tables.database import get_db
from ..tables.student_preferences import StudentPreferences

router = APIRouter(prefix="/api/preferences", tags=["preferences"])


class PreferencesIn(BaseModel):
    user_id: Optional[int] = None
    max_credits_per_term: Optional[int] = None
    unavailable_days: Optional[str] = None
    avoid_mornings: Optional[bool] = False
    avoid_evenings: Optional[bool] = False
    preferred_instructors: Optional[list] = None
    notes: Optional[str] = None


@router.get("/{user_id}")
def get_preferences(user_id: int, db: Session = Depends(get_db)):
    prefs = db.query(StudentPreferences).filter(StudentPreferences.user_id == user_id).first()
    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not found")
    return prefs.to_dict()


@router.post("/{user_id}")
def set_preferences(user_id: int, prefs_in: PreferencesIn, db: Session = Depends(get_db)):
    prefs = db.query(StudentPreferences).filter(StudentPreferences.user_id == user_id).first()
    if not prefs:
        prefs = StudentPreferences(user_id=user_id)
        db.add(prefs)

    # update fields
    if prefs_in.max_credits_per_term is not None:
        prefs.max_credits_per_term = prefs_in.max_credits_per_term
    if prefs_in.unavailable_days is not None:
        prefs.unavailable_days = prefs_in.unavailable_days
    prefs.avoid_mornings = prefs_in.avoid_mornings
    prefs.avoid_evenings = prefs_in.avoid_evenings
    if prefs_in.preferred_instructors is not None:
        prefs.preferred_instructors = ','.join(prefs_in.preferred_instructors)
    if prefs_in.notes is not None:
        prefs.notes = prefs_in.notes

    try:
        db.commit()
        db.refresh(prefs)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return prefs.to_dict()
