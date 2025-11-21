from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Reservation(Base):
    __tablename__ = 'reservations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    offering_id = Column(Integer, ForeignKey('course_offerings.id'), nullable=False)
    user_id = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default='held')  # held, committed, released, expired
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    seats = Column(Integer, default=1)
    notes = Column(Text, nullable=True)

    offering = relationship('CourseOffering', backref='reservations')

    def to_dict(self):
        return {
            'id': self.id,
            'offering_id': self.offering_id,
            'user_id': self.user_id,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'seats': self.seats,
            'notes': self.notes,
        }
