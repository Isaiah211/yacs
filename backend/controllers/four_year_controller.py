from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

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
    if not request.pathway_id and not request.pathway_code:
        raise HTTPException(status_code=400, detail="pathway_id or pathway_code required")

    years = request.years or 4
    terms_per_year = 3 if request.include_summer else 2
    max_terms = years * terms_per_year

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
        raise HTTPException(status_code=500, detail="Failed to generate 4-year plan")

    # If the plan uses fewer terms than max_terms, pad with empty terms to reach the requested horizon
    if len(plan) < max_terms:
        # create future term labels by advancing from last scheduled term (or current if none)
        last_label = plan[-1]['semester'] if plan else None
        sem_label = last_label or None
        # if no last label, optimizer used default current semester; we will not attempt to reconstruct exact labels
        while len(plan) < max_terms:
            if sem_label:
                sem_label = _advance_label(sem_label)
            else:
                sem_label = f"TBD {len(plan)+1}"
            plan.append({'semester': sem_label, 'courses': [], 'total_credits': 0})

    return plan


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
