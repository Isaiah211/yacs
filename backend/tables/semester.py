from sqlalchemy import Column, String, Date, Integer
from .database import Base

class Semester(Base):
    __tablename__ = 'semesters'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)  # e.g., "Fall 2025", "Spring 2026"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    year = Column(Integer, nullable=False)
    term = Column(String, nullable=False)  # "Fall", "Spring", "Summer"