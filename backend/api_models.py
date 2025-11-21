from pydantic import BaseModel, Field
from typing import Optional
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


    
