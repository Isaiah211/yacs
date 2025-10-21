#!/usr/bin/python3
from fastapi import FastAPI, Request, Response
from starlette.middleware.sessions import SessionMiddleware
import os

# Import Pydantic models and controllers
from fastapi import Depends
from sqlalchemy.orm import Session
from api_models import (
    UserPydantic, SessionPydantic, CourseCreate,
    CourseUpdate, CourseDelete
)
from controllers import user_controller, session_controller, course_controller
from tables.database import get_db

# --- Initialize FastAPI App ---
app = FastAPI()

# --- Add Middleware ---
app.add_middleware(SessionMiddleware, secret_key="a_very_secret_key")

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
async def delete_course(request: Request, credentials: CourseDeletePydantic):
    return course_controller.delete_course(credentials.dict(), request.session)

@app.delete('/api/course/{course_id}')
async def delete_course_by_id(request: Request, course_id: int):
    return course_controller.delete_course_by_id(course_id, request.session)

# --- Add your Course, Professor, and other endpoints below ---
# Example:
# from controllers import course_controller
#
# @app.get('/api/semester')
# async def get_semesters():
#     return course_controller.get_all_semesters()