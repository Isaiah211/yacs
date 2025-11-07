from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
from sqlalchemy.orm import Session

from ..tables.database import get_db
from ..services.pathway_optimizer import optimize_pathway

router = APIRouter(prefix="/api/optimizer", tags=["optimizer"])


class OptimizeRequest(BaseModel):
    pathway_id: Optional[int] = None
    pathway_code: Optional[str] = None
    completed_course_codes: Optional[List[str]] = []
    max_credits_per_semester: Optional[int] = 15
    start_semester: Optional[str] = None
    max_terms: Optional[int] = 12


class SemesterPlan(BaseModel):
    semester: str
    courses: List[Dict]
    total_credits: int


@router.post("/", response_model=List[SemesterPlan])
def optimize(request: OptimizeRequest, db: Session = Depends(get_db)):
    if not request.pathway_id and not request.pathway_code:
        raise HTTPException(status_code=400, detail="pathway_id or pathway_code required")

    plan = optimize_pathway(
        db=db,
        pathway_id=request.pathway_id,
        pathway_code=request.pathway_code,
        completed_course_codes=request.completed_course_codes,
        max_credits_per_semester=request.max_credits_per_semester or 15,
        start_semester=request.start_semester,
        max_terms=request.max_terms or 12,
    )

    if plan is None:
        raise HTTPException(status_code=500, detail="Failed to generate plan")

    return plan
