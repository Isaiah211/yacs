from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import Session

from .database import Base

class SemesterInfo(Base):
    __tablename__ = "semester_info"

    semester = Column(String(length=255), primary_key=True)
    public = Column(Boolean, nullable=False, default=False)
