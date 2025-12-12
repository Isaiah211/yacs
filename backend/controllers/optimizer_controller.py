from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
import logging

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
    user_id: Optional[int] = None
    # inline preferences may be provided to override/replace stored preferences
    preferences: Optional[Dict[str, Any]] = None


@router.post("/", response_model=List[SemesterPlan])
def optimize(request: OptimizeRequest, db: Session = Depends(get_db)):
    logger = logging.getLogger("optimizer_controller")
    # Input validation
    if not request.pathway_id and not request.pathway_code:
        logger.warning("Missing pathway_id or pathway_code in request: %s", request.dict())
        raise HTTPException(status_code=400, detail="pathway_id or pathway_code required")
    if request.max_credits_per_semester is not None and (request.max_credits_per_semester < 1 or request.max_credits_per_semester > 30):
        logger.warning("Invalid max_credits_per_semester: %s", request.max_credits_per_semester)
        raise HTTPException(status_code=400, detail="max_credits_per_semester must be between 1 and 30")
    if request.max_terms is not None and (request.max_terms < 1 or request.max_terms > 20):
        logger.warning("Invalid max_terms: %s", request.max_terms)
        raise HTTPException(status_code=400, detail="max_terms must be between 1 and 20")

    try:
        logger.info("Running optimizer for pathway_id=%s, pathway_code=%s", request.pathway_id, request.pathway_code)
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
            logger.error("Failed to generate plan for request: %s", request.dict())
            raise HTTPException(status_code=500, detail="Failed to generate plan")

        # Collect unscheduled courses if possible
        unscheduled = []
        if hasattr(plan, 'unscheduled_courses'):
            unscheduled = plan.unscheduled_courses

        total_credits = sum(term.get('total_credits', 0) for term in plan)
        response = {
            "plan": plan,
            "metadata": {
                "terms": len(plan),
                "total_credits": total_credits,
                "max_credits_per_semester": request.max_credits_per_semester or 15,
                "unscheduled_courses": unscheduled
            }
        }
        logger.info("Optimizer completed successfully for pathway_id=%s, pathway_code=%s", request.pathway_id, request.pathway_code)
        return response
    except Exception as e:
        logger.exception("Exception during optimizer run: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal error during optimization")


@router.post('/score')
def score_schedule_endpoint(req: ScoreRequest, db: Session = Depends(get_db)):
    """Score a proposed schedule (list of course ids) and return breakdown."""
    from ..services import score as score_service
    from ..tables.student_preferences import StudentPreferences

    prefs = None
    # if preferences included in payload use them
    if req.preferences:
        prefs = req.preferences
    # else if user_id provided, fetch stored preferences
    elif req.user_id:
        prefs_obj = db.query(StudentPreferences).filter(StudentPreferences.user_id == req.user_id).first()
        if prefs_obj:
            prefs = prefs_obj.to_dict()

    # score_schedule in service expects course ids and db; we will fetch courses and call score_courses to pass preferences
    from tables.course import Course as CourseModel
    courses = db.query(CourseModel).filter(CourseModel.id.in_(req.course_ids)).all()
    if len(courses) != len(req.course_ids):
        return {'error': 'One or more courses not found', 'requested': len(req.course_ids), 'found': len(courses)}

    result = score_service.score_courses(courses, weights=req.weights, db=db, preferences=prefs)
    return result
