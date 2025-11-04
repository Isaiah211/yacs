from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship
from .database import Base

# Association table for pathway-course many-to-many relationship
pathway_courses = Table(
    'pathway_courses',
    Base.metadata,
    Column('pathway_id', Integer, ForeignKey('pathways.id')),
    Column('course_id', String, ForeignKey('courses.id'))
)

class Pathway(Base):
    __tablename__ = 'pathways'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)  # e.g., "Computer Science", "Mechanical Engineering"
    code = Column(String, nullable=False, unique=True)  # e.g., "CSCI", "MECH"
    description = Column(String)
    total_credits = Column(Integer, nullable=False)  # Total credits required for completion
    
    # Relationships
    courses = relationship("Course", secondary=pathway_courses, back_populates="pathways")
    requirements = relationship("PathwayRequirement", back_populates="pathway")

class PathwayRequirement(Base):
    __tablename__ = 'pathway_requirements'

    id = Column(Integer, primary_key=True, autoincrement=True)
    pathway_id = Column(Integer, ForeignKey('pathways.id'), nullable=False)
    name = Column(String, nullable=False)  # e.g., "Core Requirements", "Technical Electives"
    description = Column(String)
    credits_required = Column(Integer, nullable=False)
    course_count_required = Column(Integer)  # Number of courses needed (optional)
    
    # Relationships
    pathway = relationship("Pathway", back_populates="requirements")
    courses = relationship("Course", secondary="requirement_courses")

# Association table for requirement-course many-to-many relationship
requirement_courses = Table(
    'requirement_courses',
    Base.metadata,
    Column('requirement_id', Integer, ForeignKey('pathway_requirements.id')),
    Column('course_id', String, ForeignKey('courses.id'))
)