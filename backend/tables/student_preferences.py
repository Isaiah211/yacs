from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class StudentPreferences(Base):
    __tablename__ = 'student_preferences'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)  # optional link to users table if available
    max_credits_per_term = Column(Integer, nullable=True)
    unavailable_days = Column(String(20), nullable=True)  # e.g., 'MWF' or 'TR'
    avoid_mornings = Column(Boolean, default=False)
    avoid_evenings = Column(Boolean, default=False)
    preferred_instructors = Column(String(255), nullable=True)  # CSV list
    notes = Column(Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'max_credits_per_term': self.max_credits_per_term,
            'unavailable_days': self.unavailable_days,
            'avoid_mornings': self.avoid_mornings,
            'avoid_evenings': self.avoid_evenings,
            'preferred_instructors': (self.preferred_instructors or '').split(',') if self.preferred_instructors else [],
            'notes': self.notes,
        }
