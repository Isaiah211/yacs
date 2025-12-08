from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from datetime import time


class SessionPydantic(BaseModel):
    email: str
    password: str

class SessionDeletePydantic(BaseModel):
    sessionID: str

class CourseCreate(BaseModel):
    course_code: str
    name: str
    description: Optional[str] = None
    credits: int
    semester: str
    department: str
    prerequisites: Optional[str] = None
    capacity: Optional[int] = None
    instructor: Optional[str] = None
    days_of_week: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    location: Optional[str] = None

class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    credits: Optional[int] = None
    semester: Optional[str] = None
    department: Optional[str] = None
    prerequisites: Optional[str] = None
    capacity: Optional[int] = None
    instructor: Optional[str] = None
    days_of_week: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    location: Optional[str] = None


class CourseReviewCreate(BaseModel):
    course_id: Optional[int] = None
    course_code: Optional[str] = None
    semester: Optional[str] = None
    user_identifier: Optional[str] = None
    user_name: Optional[str] = None
    rating: int = Field(..., ge=1, le=5)
    difficulty: Optional[int] = Field(None, ge=1, le=5)
    workload_hours: Optional[int] = Field(None, ge=0)
    would_recommend: Optional[bool] = None
    comment: Optional[str] = Field(None, max_length=2000)


class CourseReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    difficulty: Optional[int] = Field(None, ge=1, le=5)
    workload_hours: Optional[int] = Field(None, ge=0)
    would_recommend: Optional[bool] = None
    comment: Optional[str] = Field(None, max_length=2000)

class CourseDelete(BaseModel):
    course_code: str
    semester: str

class updateUser(BaseModel):
    name:str
    sessionID:str
    email:str
    phone:str
    newPassword:str
    major:str
    degree:str

class UserPydantic(BaseModel):
     name: str
     email: str
     phone: str
     password: str
     major: str
     degree: str

class UserDeletePydantic(BaseModel):
    sessionID: str
    password: str

class UserCoursePydantic(BaseModel):
    name: str
    semester: str
    cid: str

class SubsemesterPydantic(BaseModel):
    semester: Optional[str] = None

class DefaultSemesterSetPydantic(BaseModel):
    default: str


class CalendarExportRequest(BaseModel):
    course_ids: Optional[List[int]] = Field(default=None, description="course ids to export")
    course_codes: Optional[List[str]] = Field(default=None, description="course codes to export")
    semester: Optional[str] = Field(default=None, description="semester name")
    calendar_name: Optional[str] = Field(default="Course Schedule", min_length=1, max_length=128)
    timezone: Optional[str] = Field(default="America/New_York", min_length=1, max_length=64)

    @model_validator(mode="after")
    def ensure_selection(cls, values: "CalendarExportRequest"):
        if not values.course_ids and not values.course_codes:
            raise ValueError("provide course_ids or course_codes")
        return values


    
