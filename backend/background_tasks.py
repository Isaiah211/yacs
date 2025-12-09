from tables.database_session import SessionLocal
import os
import logging

from services.pathway_optimizer import optimize_pathway, gather_pathway_courses, build_prereq_map
from services.global_optimizer import optimize_pathway_exact

logger = logging.getLogger("yacs.background")


def run_optimize_task(payload: dict):
    """Background task entrypoint for running the optimizer.

    Payload should match OptimizeRequest fields.
    """
    db = SessionLocal()
    try:
        solver = payload.get("solver", "heuristic")
        if solver and solver.lower() == 'exact':
            courses = gather_pathway_courses(db, pathway_id=payload.get('pathway_id'), pathway_code=payload.get('pathway_code'))
            prereq_map = build_prereq_map(db)
            completed = set(payload.get('completed_course_codes') or [])
            plan = optimize_pathway_exact(
                db=db,
                pathway_courses=courses,
                prereq_map=prereq_map,
                completed=completed,
                start_semester=payload.get('start_semester'),
                max_terms=payload.get('max_terms') or 12,
                max_credits_per_semester=payload.get('max_credits_per_semester') or 15,
                allow_overfull=payload.get('allow_overfull') or False,
            )
        else:
            plan = optimize_pathway(
                db=db,
                pathway_id=payload.get('pathway_id'),
                pathway_code=payload.get('pathway_code'),
                completed_course_codes=payload.get('completed_course_codes'),
                max_credits_per_semester=payload.get('max_credits_per_semester') or 15,
                user_id=payload.get('user_id'),
                start_semester=payload.get('start_semester'),
                max_terms=payload.get('max_terms') or 12,
                allow_overfull=payload.get('allow_overfull') or False,
                reserve_seats=payload.get('reserve_seats') or False,
            )

        if plan is None:
            return {"status": "error", "error": "Failed to generate plan"}

        return {"status": "finished", "plan": plan}
    except Exception as e:
        logger.exception("Optimizer task failed")
        return {"status": "error", "error": str(e)}
    finally:
        try:
            db.close()
        except Exception:
            pass
