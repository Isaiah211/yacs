from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Time
from .database import Base
from datetime import time as dt_time

class Course(Base):
    __tablename__ = 'courses'

    id = Column(Integer, primary_key=True)
    course_code = Column(String(10), unique=True, nullable=False)  # e.g., "CSCI-1200"
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    credits = Column(Integer, nullable=False)
    semester = Column(String(20), nullable=False)  # e.g., "Fall 2025"
    department = Column(String(50), nullable=False)
    prerequisites = Column(String(255), nullable=True)
    capacity = Column(Integer, nullable=True)
    instructor = Column(String(100), nullable=True)
    days_of_week = Column(String(10), nullable=True) #formats like "MWR", "TF", "MTWRF", etc
    start_time = Column(Time, nullable=True) #formats like 10:00:00
    end_time = Column(Time, nullable=True) #formats like 11:50:00
    location = Column(String(100), nullable=True) #formats like "DCC 308"

    def to_dict(self):
        """Convert course object to dictionary"""
        return {
            'id': self.id,
            'course_code': self.course_code,
            'name': self.name,
            'description': self.description,
            'credits': self.credits,
            'semester': self.semester,
            'department': self.department,
            'prerequisites': self.prerequisites,
            'capacity': self.capacity,
            'instructor': self.instructor,
            'days_of_week': self.days_of_week,
            'start_time': self.start_time.strftime('%H:%M:%S') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M:%S') if self.end_time else None,
            'location': self.location
        }