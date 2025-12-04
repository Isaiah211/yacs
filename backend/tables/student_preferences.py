from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, Time
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
    # Additional preference fields
    earliest_start_time = Column(Time, nullable=True)  # e.g., 09:00:00
    latest_end_time = Column(Time, nullable=True)      # e.g., 17:00:00
    max_days_per_week = Column(Integer, nullable=True)
    preferred_days = Column(String(20), nullable=True)  # e.g., 'MW'
    max_gaps_per_day = Column(Integer, nullable=True)   # minutes
    contiguous_classes = Column(Boolean, default=False)
    preferred_locations = Column(String(255), nullable=True)  # CSV
    preferred_time_of_day = Column(String(20), nullable=True)  # 'morning'|'afternoon'|'none'
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
            'earliest_start_time': self.earliest_start_time.strftime('%H:%M:%S') if self.earliest_start_time else None,
            'latest_end_time': self.latest_end_time.strftime('%H:%M:%S') if self.latest_end_time else None,
            'max_days_per_week': self.max_days_per_week,
            'preferred_days': self.preferred_days,
            'max_gaps_per_day': self.max_gaps_per_day,
            'contiguous_classes': self.contiguous_classes,
            'preferred_locations': (self.preferred_locations or '').split(',') if self.preferred_locations else [],
            'preferred_time_of_day': self.preferred_time_of_day,
            'notes': self.notes,
        }
