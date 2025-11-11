from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base


class CourseOffering(Base):
    __tablename__ = 'course_offerings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    term = Column(String(20), nullable=False)  # e.g., 'Fall', 'Spring', 'Summer'
    year = Column(Integer, nullable=True)  # if null -> recurring every year in that term
    section = Column(String(50), nullable=True)
    days = Column(String(20), nullable=True)  # e.g., 'MWF', 'TR'
    start_time = Column(String(10), nullable=True)  # e.g., '09:00AM'
    end_time = Column(String(10), nullable=True)    # e.g., '10:15AM'
    instructor = Column(String(100), nullable=True)
    location = Column(String(100), nullable=True)
    capacity = Column(Integer, nullable=True)
    enrolled = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    course = relationship('Course', backref='offerings')

    def __repr__(self):
        return (
            f"<CourseOffering(course_id={self.course_id}, term={self.term}, year={self.year}, "
            f"section={self.section}, days={self.days}, time={self.start_time}-{self.end_time})>"
        )
