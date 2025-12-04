from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
from sqlalchemy.orm import Session

from ..tables.database import get_db
from ..services.pathway_optimizer import optimize_pathway, gather_pathway_courses, build_prereq_map
from ..services.global_optimizer import optimize_pathway_exact

router = APIRouter(prefix="/api/optimizer", tags=["optimizer"])


class OptimizeRequest(BaseModel):
    pathway_id: Optional[int] = None
    pathway_code: Optional[str] = None
    completed_course_codes: Optional[List[str]] = []
    max_credits_per_semester: Optional[int] = 15
    user_id: Optional[int] = None
    start_semester: Optional[str] = None
    max_terms: Optional[int] = 12
    allow_overfull: Optional[bool] = False
    reserve_seats: Optional[bool] = False
    solver: Optional[str] = 'heuristic'  # 'heuristic' or 'exact'


class SemesterPlan(BaseModel):
    semester: str
    courses: List[Dict]
    total_credits: int


class ScoreRequest(BaseModel):
    course_ids: List[int]
    weights: Optional[Dict[str, float]] = None


@router.post("/", response_model=List[SemesterPlan])
def optimize(request: OptimizeRequest, db: Session = Depends(get_db)):
    if not request.pathway_id and not request.pathway_code:
        raise HTTPException(status_code=400, detail="pathway_id or pathway_code required")
    if request.solver and request.solver.lower() == 'exact':
        courses = gather_pathway_courses(db, pathway_id=request.pathway_id, pathway_code=request.pathway_code)
        prereq_map = build_prereq_map(db)
        completed = set((request.completed_course_codes or []))
        plan = optimize_pathway_exact(
            db=db,
            pathway_courses=courses,
            prereq_map=prereq_map,
            completed=completed,
            start_semester=request.start_semester,
            max_terms=request.max_terms or 12,
            max_credits_per_semester=request.max_credits_per_semester or 15,
            allow_overfull=request.allow_overfull or False,
        )
    else:
        plan = optimize_pathway(
            db=db,
            pathway_id=request.pathway_id,
            pathway_code=request.pathway_code,
            completed_course_codes=request.completed_course_codes,
            max_credits_per_semester=request.max_credits_per_semester or 15,
            user_id=request.user_id,
            start_semester=request.start_semester,
            max_terms=request.max_terms or 12,
            allow_overfull=request.allow_overfull or False,
            reserve_seats=request.reserve_seats or False,
        )

    if plan is None:
        raise HTTPException(status_code=500, detail="Failed to generate plan")

    return plan


@router.post('/score')
def score_schedule_endpoint(req: ScoreRequest, db: Session = Depends(get_db)):
    """Score a proposed schedule (list of course ids) and return breakdown."""
    from ..services import score as score_service

    result = score_service.score_schedule(req.course_ids, db, weights=req.weights)
    return result
