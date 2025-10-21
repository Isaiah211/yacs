from pydantic import BaseModel
from typing import Optional


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

class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    credits: Optional[int] = None
    semester: Optional[str] = None
    department: Optional[str] = None
    prerequisites: Optional[str] = None
    capacity: Optional[int] = None
    instructor: Optional[str] = None

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


    
