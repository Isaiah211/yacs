#!/usr/bin/python3
from fastapi import FastAPI, Request, Response, HTTPException
from starlette.middleware.sessions import SessionMiddleware
import os
from typing import Optional, List
import uuid
import logging
import json

# async redis client
import redis.asyncio as aioredis
from pythonjsonlogger import jsonlogger
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from redis import Redis
from rq import Queue

# Import Pydantic models and controllers
from fastapi import Depends
from sqlalchemy.orm import Session
from api_models import (
    UserPydantic, SessionPydantic, CourseCreate,
    CourseUpdate, CourseDelete, UserCoursePydantic,
    CourseReviewCreate, CourseReviewUpdate, CalendarExportRequest,
    ConflictResolutionRequest, CollaborativeScheduleCreate,
    CollaborativeScheduleUpdate, ScheduleCoursesUpsertRequest,
    ScheduleShareRequest, ScheduleCommentCreate
)
from controllers import (
    user_controller, session_controller, course_controller,
    semester_controller, pathway_controller, optimizer_controller,
    review_controller, calendar_controller, collaborative_schedule_controller
)
from controllers import four_year_controller, preferences_controller, reservations_controller
from tables.database import get_db
from tables.course import Course

# --- Initialize FastAPI App ---
app = FastAPI()

# --- Add Middleware ---
app.add_middleware(SessionMiddleware, secret_key="a_very_secret_key")

# --- Include Routers ---
app.include_router(semester_controller.router, tags=["semesters"])
app.include_router(pathway_controller.router, tags=["pathways"])
app.include_router(optimizer_controller.router, tags=["optimizer"])
app.include_router(four_year_controller.router, tags=["plan"])
app.include_router(preferences_controller.router, tags=["preferences"])
app.include_router(reservations_controller.router, tags=["reservations"])


# --- Structured logging setup ---
logger = logging.getLogger("yacs")
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)


# --- Redis client setup (attached to app.state) ---
@app.on_event("startup")
async def startup_event():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        app.state.redis = aioredis.from_url(redis_url, decode_responses=True)
        # test connection
        await app.state.redis.ping()
        logger.info("redis_connected")
    except Exception as e:
        app.state.redis = None
        logger.warning(f"Redis not available: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    r = getattr(app.state, "redis", None)
    if r:
        try:
            await r.close()
        except Exception:
            pass


# --- Middleware: attach request id and basic request logging ---
@app.middleware("http")
async def add_request_id_and_log(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    logger.info("request_start", extra={"path": request.url.path, "method": request.method, "request_id": request_id})
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info("request_end", extra={"path": request.url.path, "method": request.method, "status_code": response.status_code, "request_id": request_id})
    return response


# --- Helper functions for simple Redis caching ---
async def _get_cached(key: str):
    r = getattr(app.state, "redis", None)
    if not r:
        return None
    try:
        raw = await r.get(key)
        if not raw:
            return None
        return json.loads(raw)
    except Exception:
        return None


async def _set_cached(key: str, value, ttl: int = 300):
    r = getattr(app.state, "redis", None)
    if not r:
        return
    try:
        await r.set(key, json.dumps(value), ex=ttl)
    except Exception:
        return


async def _invalidate_course_caches():
    """Remove cached keys related to course lists and searches."""
    r = getattr(app.state, "redis", None)
    if not r:
        return
    try:
        # delete keys matching our cache prefixes
        async for key in r.scan_iter(match="get_courses*"):
            try:
                await r.delete(key)
            except Exception:
                pass
        async for key in r.scan_iter(match="search_courses*"):
            try:
                await r.delete(key)
            except Exception:
                pass
        logger.info("cache_invalidated", extra={"scope": "courses"})
    except Exception as e:
        logger.warning(f"Error invalidating cache: {e}")

# --- API Endpoints ---

@app.get('/')
async def root():
    """Confirms the API is running."""
    return {"message": "YACS API is Up!"}


@app.get('/health')
async def health():
    """Basic health endpoint reporting redis availability."""
    r = getattr(app.state, "redis", None)
    redis_ok = False
    if r:
        try:
            await r.ping()
            redis_ok = True
        except Exception:
            redis_ok = False
    return {"status": "ok", "redis": redis_ok}


# --- Background job endpoints (RQ) ---
@app.post('/api/optimizer/async')
async def enqueue_optimize(request: Request, payload: dict):
    """Enqueue an optimizer job and return job id. Payload should mirror OptimizeRequest."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    # use sync Redis for RQ
    redis_conn = Redis.from_url(redis_url)
    q = Queue("default", connection=redis_conn)
    # import background runner path (must be importable by worker)
    job = q.enqueue("background_tasks.run_optimize_task", payload)
    return {"job_id": job.get_id(), "status": job.get_status()}


@app.get('/api/optimizer/jobs/{job_id}')
async def get_job_status(job_id: str):
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_conn = Redis.from_url(redis_url)
    from rq.job import Job

    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")

    data = {
        "id": job.get_id(),
        "status": job.get_status(),
        "result": job.result,
        "exc_info": job.exc_info,
    }
    return data

## User Account Management ##
@app.post('/api/user')
async def add_user(user: UserPydantic):
    return user_controller.create_user(user.dict())

@app.delete('/api/user')
async def delete_user(request: Request):
    if 'user' not in request.session:
        return Response("Not authorized", status_code=403)
    user_id = request.session['user']['user_id']
    return user_controller.delete_current_user(user_id)

## Session Management (Login/Logout) ##
@app.post('/api/session')
async def log_in(request: Request, credentials: SessionPydantic):
    return session_controller.log_user_in(credentials.dict(), request.session)

@app.delete('/api/session')
def log_out(request: Request):
    return session_controller.log_user_out(request.session)

## Course Management ##
@app.post('/api/courses')
async def create_course(
    course: CourseCreate,
    db: Session = Depends(get_db)
):
    # run controller in threadpool and invalidate caches after create
    result = await run_in_threadpool(course_controller.create_course, course.dict(), db)
    await _invalidate_course_caches()
    return result

@app.get('/api/courses')
async def get_courses(request: Request, semester: Optional[str] = None, department: Optional[str] = None, db: Session = Depends(get_db)):
    """Return courses, with a short Redis-backed cache keyed by semester+department."""
    cache_key = f"get_courses:semester={semester or ''}:department={department or ''}"
    cached = await _get_cached(cache_key)
    if cached is not None:
        return JSONResponse(content=cached)

    # run controller in threadpool to avoid blocking event loop
    result = await run_in_threadpool(course_controller.get_courses, semester, department, db)
    enc = jsonable_encoder(result)
    await _set_cached(cache_key, enc, ttl=300)
    return enc

@app.get('/api/courses/{course_code}')
async def get_course(
    course_code: str,
    semester: str,
    db: Session = Depends(get_db)
):
    return course_controller.get_course(course_code, semester, db)

@app.put('/api/courses/{course_code}')
async def update_course(
    course_code: str,
    semester: str,
    updates: CourseUpdate,
    db: Session = Depends(get_db)
):
    result = await run_in_threadpool(course_controller.update_course, course_code, semester, updates.dict(exclude_unset=True), db)
    await _invalidate_course_caches()
    return result

@app.delete('/api/courses/{course_code}')
async def delete_course(
    course_code: str,
    semester: str,
    db: Session = Depends(get_db)
):
    result = await run_in_threadpool(course_controller.delete_course, course_code, semester, db)
    await _invalidate_course_caches()
    return result

@app.get('/api/course/{course_id}')
async def get_course_by_id(request: Request, course_id: int):
    return course_controller.get_course_by_id(course_id, request.session)

@app.put('/api/course/{course_id}')
async def update_course(request: Request, course_id: int, credentials: UserCoursePydantic):
    result = await run_in_threadpool(course_controller.update_course, credentials.dict(), request.session)
    await _invalidate_course_caches()
    return result

@app.delete('/api/course')
async def delete_course_alt(request: Request, credentials: CourseDelete):
    result = await run_in_threadpool(course_controller.delete_course, credentials.dict(), request.session)
    await _invalidate_course_caches()
    return result

@app.delete('/api/course/{course_id}')
async def delete_course_by_id(request: Request, course_id: int):
    result = await run_in_threadpool(course_controller.delete_course_by_id, course_id, request.session)
    await _invalidate_course_caches()
    return result

@app.get('/api/courses/{course_code}/prerequisites')
async def get_prerequisites(
    course_code: str,
    db: Session = Depends(get_db)
):
    """get all prerequisites for a course"""
    course = db.query(Course).filter(Course.course_code == course_code).first()
    if not course:
        return {"error": "Course not found"}, 404
    
    return course_controller.get_course_with_prerequisites(course.id, db)

@app.post('/api/courses/{course_code}/prerequisites')
async def add_prerequisite_endpoint(
    course_code: str,
    prerequisite_code: str,
    db: Session = Depends(get_db)
):
    """add a prerequisite to a course"""
    try:
        result = await run_in_threadpool(course_controller.add_prerequisite, course_code, prerequisite_code, db)
        await _invalidate_course_caches()
        return result
    except ValueError as e:
        return {"error": str(e)}, 400

@app.get('/api/courses/{course_code}/required-by')
async def get_courses_requiring(
    course_code: str,
    db: Session = Depends(get_db)
):
    """find courses that require this course as a prerequisite"""
    courses = course_controller.get_courses_requiring_prerequisite(course_code, db)
    return [{"course_code": c.course_code, "title": c.title} for c in courses]

@app.get('/api/courses/{course_code}/corequisites')
async def get_corequisites(course_code: str, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.course_code == course_code).first()
    if not course:
        return {"error": "Course not found"}
    return course_controller.get_course_with_corequisites(course.id, db)

@app.post('/api/courses/{course_code}/corequisites')
async def add_corequisite_endpoint(
    course_code: str,
    corequisite_code: str, #pass as query param ?corequisite_code=CSCI-XXXX
    db: Session = Depends(get_db)
):
    try:
        result = await run_in_threadpool(course_controller.add_corequisite, course_code, corequisite_code, db)
        await _invalidate_course_caches()
        return result
    except ValueError as e:
        return {"error": str(e)}

@app.get('/api/courses/{course_code}/required-with')
async def get_courses_requiring_coreq(course_code: str, db: Session = Depends(get_db)):
    courses = course_controller.get_courses_requiring_corequisite(course_code, db)
    return [{"course_code": c.course_code, "title": getattr(c, "title", None)} for c in courses]

@app.get('/api/courses/search')
async def search_courses(request: Request,
    query: Optional[str] = None,
    semester: Optional[str] = None,
    department: Optional[str] = None,
    credits: Optional[int] = None,
    instructor: Optional[str] = None,
    min_credits: Optional[int] = None,
    max_credits: Optional[int] = None,
    level: Optional[str] = None,
    has_capacity: Optional[bool] = None,
    sort_by: Optional[str] = "course_code",
    sort_order: Optional[str] = "asc",
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    db: Session = Depends(get_db)
):
    # use query params map to build cache key (simple)
    qitems = sorted(list(request.query_params.items()))
    cache_key = f"search_courses:{qitems}"
    cached = await _get_cached(cache_key)
    if cached is not None:
        return JSONResponse(content=cached)

    result = await run_in_threadpool(
        course_controller.search_courses,
        {
            'db': db,
            'query': query,
            'semester': semester,
            'department': department,
            'credits': credits,
            'instructor': instructor,
            'min_credits': min_credits,
            'max_credits': max_credits,
            'level': level,
            'has_capacity': has_capacity,
            'sort_by': sort_by,
            'sort_order': sort_order,
            'limit': limit,
            'offset': offset
        }
    )
    # note: controller expects kwargs; if it returns an object, we attempt to encode
    enc = jsonable_encoder(result)
    await _set_cached(cache_key, enc, ttl=120)
    return enc

@app.get('/api/courses/departments')
async def get_departments(semester: Optional[str] = None, db: Session = Depends(get_db)):
    return course_controller.get_departments(db, semester)

@app.get('/api/courses/instructors')
async def get_instructors(semester: Optional[str] = None, department: Optional[str] = None, db: Session = Depends(get_db)):
    return course_controller.get_instructors(db, semester, department)

@app.get('/api/courses/levels')
async def get_course_levels(department: Optional[str] = None, db: Session = Depends(get_db)):
    return course_controller.get_course_levels(db, department)

@app.get('/api/courses/department/{department}/level/{level}')
async def get_courses_by_dept_level(department: str, level: str, semester: Optional[str] = None, db: Session = Depends(get_db)):
    return course_controller.get_courses_by_department_level(db, department, level, semester)

#conflict detection endpoints
@app.post('/api/courses/check-conflicts')
async def check_conflicts(course_ids: List[int], db: Session = Depends(get_db)):
    """
    check scheduling conflicts by ids
    returns:
        has_conflicts: boolean
        conflict_count: # of conflicts
        conflicts: list of conflict details
        courses_checked: details of all courses checked
    """
    return course_controller.check_schedule_conflicts(course_ids, db)

@app.post('/api/courses/check-conflicts-by-code')
async def check_conflicts_by_code(course_codes: List[str], semester: str, db: Session = Depends(get_db)):
    #check scheduling conflicts by course codes
    return course_controller.check_schedule_conflicts_by_codes(course_codes, semester, db)

@app.post('/api/courses/find-non-conflicting')
async def find_non_conflicting(enrolled_course_ids: List[int], semester: str, department: Optional[str] = None, level: Optional[str] = None, db: Session = Depends(get_db)):
    """
    find courses that dont conflict with currently enrolled courses
    returns:
        enrolled_courses
        non_conflicting_courses: courses without conflicts
        conflicting_courses: courses with conflicts
    """
    return course_controller.find_non_conflicting_courses(enrolled_course_ids, semester, db, department, level)

@app.post('/api/courses/resolve-conflicts')
async def resolve_conflicts(payload: ConflictResolutionRequest, db: Session = Depends(get_db)):
    return course_controller.suggest_conflict_resolutions(
        payload.course_ids,
        db,
        payload.max_suggestions or 5
    )

#calendar exporting endpoint
@app.post('/api/calendar/export')
async def export_calendar(payload: CalendarExportRequest, db: Session = Depends(get_db)):
    result = calendar_controller.build_calendar_export(db, course_ids=payload.course_ids, course_codes=payload.course_codes, semester=payload.semester, calendar_name=payload.calendar_name or "YACS Schedule", timezone=payload.timezone or "America/New_York")

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Unable to export calendar."))

    filename = result.get("filename", "yacs-schedule.ics")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}

    metadata = result.get("metadata") or {}
    headers["X-YACS-Exported"] = str(metadata.get("exported", 0))
    if metadata.get("skipped"):
        headers["X-YACS-Skipped"] = ",".join(metadata["skipped"])

    return Response(content=result["ics"], media_type="text/calendar", headers=headers)

#course review endpoints
@app.post('/api/courses/{course_code}/reviews')
async def add_course_review(course_code: str, review: CourseReviewCreate, semester: Optional[str] = None, db: Session = Depends(get_db)):
    payload = review.model_dump(exclude_unset=True)
    payload['course_code'] = course_code
    if semester:
        payload['semester'] = semester
    return review_controller.create_review(payload, db)

@app.get('/api/courses/{course_code}/reviews')
async def list_course_reviews(course_code: str, semester: Optional[str] = None, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    return review_controller.list_reviews(db, course_code=course_code, semester=semester, limit=limit, offset=offset)

@app.get('/api/reviews/{review_id}')
async def get_single_review(review_id: int, db: Session = Depends(get_db)):
    return review_controller.get_review(review_id, db)

@app.put('/api/reviews/{review_id}')
async def update_course_review(review_id: int, updates: CourseReviewUpdate, db: Session = Depends(get_db)):
    return review_controller.update_review(review_id, updates.model_dump(exclude_unset=True), db)

@app.delete('/api/reviews/{review_id}')
async def delete_course_review(review_id: int, db: Session = Depends(get_db)):
    return review_controller.delete_review(review_id, db)

@app.get('/api/courses/{course_code}/reviews/summary')
async def get_course_review_summary(course_code: str, semester: Optional[str] = None, db: Session = Depends(get_db)):
    return review_controller.get_course_rating_summary(db, course_code=course_code, semester=semester)

@app.get('/api/courses/top-rated')
async def get_top_rated_courses(semester: Optional[str] = None, department: Optional[str] = None, min_reviews: int = 3, limit: int = 10, db: Session = Depends(get_db)):
    return review_controller.get_top_rated_courses(db, semester=semester, department=department, min_reviews=min_reviews, limit=limit)

#collaborative schedule endpoints
@app.post('/api/schedules')
async def create_collaborative_schedule(payload: CollaborativeScheduleCreate, db: Session = Depends(get_db)):
    return collaborative_schedule_controller.create_schedule(payload.model_dump(exclude_unset=True), db)


@app.get('/api/schedules')
async def list_collaborative_schedules(requester_id: str, include_shared: bool = True, db: Session = Depends(get_db)):
    return collaborative_schedule_controller.list_user_schedules(requester_id, include_shared, db)


@app.get('/api/schedules/{schedule_id}')
async def get_collaborative_schedule(schedule_id: int, requester_id: str, db: Session = Depends(get_db)):
    return collaborative_schedule_controller.get_schedule(schedule_id, requester_id, db)


@app.put('/api/schedules/{schedule_id}')
async def update_collaborative_schedule(schedule_id: int, requester_id: str, payload: CollaborativeScheduleUpdate, db: Session = Depends(get_db)):
    return collaborative_schedule_controller.update_schedule(
        schedule_id,
        requester_id,
        payload.model_dump(exclude_unset=True),
        db
    )


@app.put('/api/schedules/{schedule_id}/courses')
async def replace_collaborative_schedule_courses(schedule_id: int, payload: ScheduleCoursesUpsertRequest, db: Session = Depends(get_db)):
    course_payloads = [course.model_dump(exclude_unset=True) for course in payload.courses]
    return collaborative_schedule_controller.replace_schedule_courses(
        schedule_id,
        payload.requester_identifier,
        course_payloads,
        db
    )


@app.post('/api/schedules/{schedule_id}/share')
async def share_collaborative_schedule(schedule_id: int, payload: ScheduleShareRequest, db: Session = Depends(get_db)):
    share_payload = payload.model_dump(exclude={'requester_identifier'})
    return collaborative_schedule_controller.share_schedule(
        schedule_id,
        payload.requester_identifier,
        share_payload,
        db
    )


@app.post('/api/schedules/{schedule_id}/comments')
async def add_schedule_comment(schedule_id: int, payload: ScheduleCommentCreate, db: Session = Depends(get_db)):
    return collaborative_schedule_controller.add_comment(
        schedule_id,
        payload.author_identifier,
        payload.model_dump(exclude_unset=True),
        db
    )

# --- Add your Course, Professor, and other endpoints below ---
# Example:
# from controllers import course_controller
#
# @app.get('/api/semester')
# async def get_semesters():
#     return course_controller.get_all_semesters()