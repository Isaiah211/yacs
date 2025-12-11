from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Literal
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


class ConflictResolutionRequest(BaseModel):
    course_ids: List[int]
    max_suggestions: Optional[int] = Field(default=5, ge=1, le=20)


class ScheduleCoursePayload(BaseModel):
    course_id: int
    color_hex: Optional[str] = Field(default=None, max_length=16)
    note: Optional[str] = Field(default=None, max_length=500)
    order_index: Optional[int] = None


class CollaborativeScheduleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    owner_identifier: str = Field(..., min_length=1, max_length=255)
    owner_display_name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    semester: Optional[str] = Field(default=None, max_length=50)
    courses: Optional[List[ScheduleCoursePayload]] = None


class CollaborativeScheduleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    semester: Optional[str] = Field(default=None, max_length=50)
    visibility: Optional[str] = Field(default=None, max_length=20)
    is_locked: Optional[bool] = None


class ScheduleCoursesUpsertRequest(BaseModel):
    requester_identifier: str = Field(..., min_length=1, max_length=255)
    courses: List[ScheduleCoursePayload] = Field(default_factory=list)


class ScheduleShareRequest(BaseModel):
    requester_identifier: str = Field(..., min_length=1, max_length=255)
    collaborator_identifier: str = Field(..., min_length=1, max_length=255)
    collaborator_name: Optional[str] = Field(default=None, max_length=255)
    access_level: Literal['viewer', 'commenter', 'editor'] = 'viewer'
    is_admin_delegate: Optional[bool] = False


class ScheduleCommentCreate(BaseModel):
    author_identifier: str = Field(..., min_length=1, max_length=255)
    author_display_name: Optional[str] = Field(default=None, max_length=255)
    content: str = Field(..., min_length=1, max_length=2000)


    
