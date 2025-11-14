#!/usr/bin/python3
from fastapi import FastAPI, Request, Response
from starlette.middleware.sessions import SessionMiddleware
import os
from typing import Optional, List

# Import Pydantic models and controllers
from fastapi import Depends
from sqlalchemy.orm import Session
from api_models import (
    UserPydantic, SessionPydantic, CourseCreate,
    CourseUpdate, CourseDelete, UserCoursePydantic
)
from controllers import (
    user_controller, session_controller, course_controller,
    semester_controller, pathway_controller, optimizer_controller
)
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

# --- API Endpoints ---

@app.get('/')
async def root():
    """Confirms the API is running."""
    return {"message": "YACS API is Up!"}

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
    return course_controller.create_course(course.dict(), db)

@app.get('/api/courses')
async def get_courses(
    semester: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db)
):
    return course_controller.get_courses(semester, department, db)

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
    return course_controller.update_course(course_code, semester, updates.dict(exclude_unset=True), db)

@app.delete('/api/courses/{course_code}')
async def delete_course(
    course_code: str,
    semester: str,
    db: Session = Depends(get_db)
):
    return course_controller.delete_course(course_code, semester, db)
    return course_controller.get_courses()

@app.get('/api/course/{course_id}')
async def get_course_by_id(request: Request, course_id: int):
    return course_controller.get_course_by_id(course_id, request.session)

@app.put('/api/course/{course_id}')
async def update_course(request: Request, course_id: int, credentials: UserCoursePydantic):
    return course_controller.update_course(credentials.dict(), request.session)

@app.delete('/api/course')
async def delete_course_alt(request: Request, credentials: CourseDelete):
    return course_controller.delete_course(credentials.dict(), request.session)

@app.delete('/api/course/{course_id}')
async def delete_course_by_id(request: Request, course_id: int):
    return course_controller.delete_course_by_id(course_id, request.session)

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
        return course_controller.add_prerequisite(course_code, prerequisite_code, db)
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
        return course_controller.add_corequisite(course_code, corequisite_code, db)
    except ValueError as e:
        return {"error": str(e)}

@app.get('/api/courses/{course_code}/required-with')
async def get_courses_requiring_coreq(course_code: str, db: Session = Depends(get_db)):
    courses = course_controller.get_courses_requiring_corequisite(course_code, db)
    return [{"course_code": c.course_code, "title": getattr(c, "title", None)} for c in courses]

@app.get('/api/courses/search')
async def search_courses(
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
    return course_controller.search_courses(
        db=db,
        query=query,
        semester=semester,
        department=department,
        credits=credits,
        instructor=instructor,
        min_credits=min_credits,
        max_credits=max_credits,
        level=level,
        has_capacity=has_capacity,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset
    )

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


# --- Add your Course, Professor, and other endpoints below ---
# Example:
# from controllers import course_controller
#
# @app.get('/api/semester')
# async def get_semesters():
#     return course_controller.get_all_semesters()