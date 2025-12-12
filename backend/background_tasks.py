from tables.database_session import SessionLocal
import os
import logging

from services.pathway_optimizer import optimize_pathway, gather_pathway_courses, build_prereq_map
from services.global_optimizer import optimize_pathway_exact
import redis
import json
from tables.optimizer_job import OptimizerJob
from datetime import datetime

logger = logging.getLogger("yacs.background")


def run_optimize_task(payload: dict):
    """Background task entrypoint for running the optimizer.

    Payload should match OptimizeRequest fields.
    """
    db = SessionLocal()
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_conn = redis.from_url(redis_url)

    job_db_id = payload.get("job_db_id")
    # update DB record to started
    try:
        if job_db_id:
            job_row = db.query(OptimizerJob).filter(OptimizerJob.id == int(job_db_id)).first()
            if job_row:
                job_row.status = 'started'
                job_row.started_at = datetime.utcnow()
                job_row.progress = 0
                db.add(job_row)
                db.commit()
                # set initial progress key
                try:
                    redis_conn.set(f"optimizer:progress:{job_db_id}", json.dumps({"progress": 0}), ex=3600)
                except Exception:
                    pass
    except Exception:
        # continue even if job row update fails
        db.rollback()

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
            result = {"status": "error", "error": "Failed to generate plan"}
        else:
            result = {"status": "finished", "plan": plan}

        # persist result to DB and update progress
        try:
            if job_db_id:
                job_row = db.query(OptimizerJob).filter(OptimizerJob.id == int(job_db_id)).first()
                if job_row:
                    job_row.status = 'finished' if plan is not None else 'failed'
                    job_row.result = plan if plan is not None else None
                    job_row.error = None if plan is not None else 'No plan'
                    job_row.progress = 100
                    job_row.finished_at = datetime.utcnow()
                    db.add(job_row)
                    db.commit()
                    try:
                        redis_conn.set(f"optimizer:progress:{job_db_id}", json.dumps({"progress": 100}), ex=3600)
                    except Exception:
                        pass
        except Exception:
            db.rollback()

        return result
    except Exception as e:
        logger.exception("Optimizer task failed")
        # persist failure
        try:
            if job_db_id:
                job_row = db.query(OptimizerJob).filter(OptimizerJob.id == int(job_db_id)).first()
                if job_row:
                    job_row.status = 'failed'
                    job_row.error = str(e)
                    job_row.finished_at = datetime.utcnow()
                    db.add(job_row)
                    db.commit()
                    try:
                        redis_conn.set(f"optimizer:progress:{job_db_id}", json.dumps({"progress": -1, "error": str(e)}), ex=3600)
                    except Exception:
                        pass
        except Exception:
            db.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        try:
            db.close()
        except Exception:
            pass
