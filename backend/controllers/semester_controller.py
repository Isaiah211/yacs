from fastapi import APIRouter, HTTPException
from typing import List
from datetime import date
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..tables.semester import Semester
from ..tables.database import get_db

router = APIRouter()

class SemesterCreate(BaseModel):
    name: str
    start_date: date
    end_date: date
    year: int
    term: str

class SemesterResponse(BaseModel):
    id: int
    name: str
    start_date: date
    end_date: date
    year: int
    term: str

    class Config:
        orm_mode = True

@router.post("/semesters/", response_model=SemesterResponse)
def create_semester(semester: SemesterCreate, db: Session = get_db()):
    db_semester = Semester(
        name=semester.name,
        start_date=semester.start_date,
        end_date=semester.end_date,
        year=semester.year,
        term=semester.term
    )
    db.add(db_semester)
    db.commit()
    db.refresh(db_semester)
    return db_semester

@router.get("/semesters/", response_model=List[SemesterResponse])
def get_semesters(db: Session = get_db()):
    return db.query(Semester).all()

@router.get("/semesters/current", response_model=SemesterResponse)
def get_current_semester(db: Session = get_db()):
    today = date.today()
    current_semester = db.query(Semester)\
        .filter(Semester.start_date <= today)\
        .filter(Semester.end_date >= today)\
        .first()
    if not current_semester:
        raise HTTPException(status_code=404, detail="No current semester found")
    return current_semester

@router.get("/semesters/{semester_id}", response_model=SemesterResponse)
def get_semester(semester_id: int, db: Session = get_db()):
    semester = db.query(Semester).filter(Semester.id == semester_id).first()
    if not semester:
        raise HTTPException(status_code=404, detail="Semester not found")
    return semester