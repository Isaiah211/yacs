from sqlalchemy import Column, String
from sqlalchemy.orm import Session

from .database import Base

class Professor(Base):
    __tablename__ = "professor"

    email = Column(String(length=255), primary_key=True, nullable=False)
    name = Column(String(length=255), nullable=True)
    title = Column(String(length=255), nullable=True)
    phone_number = Column(String(length=255), nullable=True)
    department = Column(String(length=255), nullable=True)
    portfolio_page = Column(String(length=255), nullable=True)
    profile_page = Column(String(length=255), nullable=True)
