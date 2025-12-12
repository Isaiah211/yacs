from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
import logging

from ..tables.database import get_db
from ..services.pathway_optimizer import optimize_pathway

router = APIRouter(prefix="/api/plan", tags=["plan"])


class FourYearRequest(BaseModel):
    pathway_id: Optional[int] = None
    pathway_code: Optional[str] = None
    completed_course_codes: Optional[List[str]] = []
    years: Optional[int] = 4
    include_summer: Optional[bool] = False
    max_credits_per_semester: Optional[int] = 15
    allow_overfull: Optional[bool] = False
    reserve_seats: Optional[bool] = False
    balance_load: Optional[bool] = True


@router.post("/four_year")
def plan_four_year(request: FourYearRequest, db: Session = Depends(get_db)):
    logger = logging.getLogger("four_year_controller")
    # Input validation
    if not request.pathway_id and not request.pathway_code:
        logger.warning("Missing pathway_id or pathway_code in request: %s", request.dict())
        raise HTTPException(status_code=400, detail="pathway_id or pathway_code required")
    if request.years is not None and (request.years < 1 or request.years > 8):
        logger.warning("Invalid years value: %s", request.years)
        raise HTTPException(status_code=400, detail="years must be between 1 and 8")
    if request.max_credits_per_semester is not None and (request.max_credits_per_semester < 1 or request.max_credits_per_semester > 30):
        logger.warning("Invalid max_credits_per_semester: %s", request.max_credits_per_semester)
        raise HTTPException(status_code=400, detail="max_credits_per_semester must be between 1 and 30")

    years = request.years or 4
    terms_per_year = 3 if request.include_summer else 2
    max_terms = years * terms_per_year

    try:
        logger.info("Generating 4-year plan for pathway_id=%s, pathway_code=%s", request.pathway_id, request.pathway_code)
        plan = optimize_pathway(
            db=db,
            pathway_id=request.pathway_id,
            pathway_code=request.pathway_code,
            completed_course_codes=request.completed_course_codes,
            max_credits_per_semester=request.max_credits_per_semester or 15,
            start_semester=None,
            max_terms=max_terms,
            allow_overfull=request.allow_overfull or False,
            reserve_seats=request.reserve_seats or False,
            balance_load=request.balance_load if request.balance_load is not None else True,
        )
        if plan is None:
            logger.error("Failed to generate 4-year plan for request: %s", request.dict())
            raise HTTPException(status_code=500, detail="Failed to generate 4-year plan")

        # If the plan uses fewer terms than max_terms, pad with empty terms to reach the requested horizon
        if len(plan) < max_terms:
            last_label = plan[-1]['semester'] if plan else None
            sem_label = last_label or None
            while len(plan) < max_terms:
                if sem_label:
                    sem_label = _advance_label(sem_label)
                else:
                    sem_label = f"TBD {len(plan)+1}"
                plan.append({'semester': sem_label, 'courses': [], 'total_credits': 0})

        total_credits = sum(term.get('total_credits', 0) for term in plan)
        response = {
            "plan": plan,
            "metadata": {
                "terms": len(plan),
                "total_credits": total_credits,
                "years": years,
                "max_credits_per_semester": request.max_credits_per_semester or 15
            }
        }
        logger.info("4-year plan generated successfully for pathway_id=%s, pathway_code=%s", request.pathway_id, request.pathway_code)
        return response
    except Exception as e:
        logger.exception("Exception during 4-year plan generation: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal error during plan generation")


def _advance_label(label: str) -> str:
    # utility used for padding labels; mirror optimizer's next semester progression
    parts = label.split()
    if len(parts) >= 2:
        term = parts[0]
        try:
            year = int(parts[1])
        except Exception:
            year = None
    else:
        return label + "+1"

    order = ["Fall", "Spring", "Summer"]
    if term not in order:
        return label + "+1"
    idx = order.index(term)
    next_idx = (idx + 1) % len(order)
    next_term = order[next_idx]
    next_year = year
    if term == "Fall" and next_term == "Spring" and year is not None:
        next_year = year + 1
    return f"{next_term} {next_year if next_year is not None else ''}".strip()
