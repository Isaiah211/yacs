from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship

from .database import Base


class CollaborativeSchedule(Base):
    __tablename__ = 'collaborative_schedules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    semester = Column(String(50), nullable=True)
    owner_identifier = Column(String(255), nullable=False, index=True)
    owner_display_name = Column(String(255), nullable=True)
    visibility = Column(String(20), nullable=False, default='private')
    is_locked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    courses = relationship('ScheduleCourse', back_populates='schedule', cascade='all, delete-orphan')
    shares = relationship('ScheduleShare', back_populates='schedule', cascade='all, delete-orphan')
    comments = relationship('ScheduleComment', back_populates='schedule', cascade='all, delete-orphan', order_by='ScheduleComment.created_at')

    def to_dict(self, include_relationships: bool = True) -> dict:
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'semester': self.semester,
            'owner_identifier': self.owner_identifier,
            'owner_display_name': self.owner_display_name,
            'visibility': self.visibility,
            'is_locked': self.is_locked,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_relationships:
            data['courses'] = [course.to_dict() for course in getattr(self, 'courses', [])]
            data['shares'] = [share.to_dict() for share in getattr(self, 'shares', [])]
            data['comments'] = [comment.to_dict() for comment in getattr(self, 'comments', [])]
        return data


class ScheduleCourse(Base):
    __tablename__ = 'schedule_courses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_id = Column(Integer, ForeignKey('collaborative_schedules.id', ondelete='CASCADE'), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='SET NULL'), nullable=True)
    color_hex = Column(String(16), nullable=True)
    note = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=True)

    schedule = relationship('CollaborativeSchedule', back_populates='courses')
    course = relationship('Course')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'schedule_id': self.schedule_id,
            'course_id': self.course_id,
            'color_hex': self.color_hex,
            'note': self.note,
            'order_index': self.order_index,
            'course': self.course.to_dict() if self.course and hasattr(self.course, 'to_dict') else None,
        }


class ScheduleShare(Base):
    __tablename__ = 'schedule_shares'

    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_id = Column(Integer, ForeignKey('collaborative_schedules.id', ondelete='CASCADE'), nullable=False)
    collaborator_identifier = Column(String(255), nullable=False)
    collaborator_name = Column(String(255), nullable=True)
    access_level = Column(String(20), nullable=False, default='viewer')
    is_admin_delegate = Column(Boolean, nullable=False, default=False)
    granted_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    schedule = relationship('CollaborativeSchedule', back_populates='shares')

    __table_args__ = (
        UniqueConstraint('schedule_id', 'collaborator_identifier', name='uq_schedule_collaborator'),
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'schedule_id': self.schedule_id,
            'collaborator_identifier': self.collaborator_identifier,
            'collaborator_name': self.collaborator_name,
            'access_level': self.access_level,
            'is_admin_delegate': self.is_admin_delegate,
            'granted_by': self.granted_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ScheduleComment(Base):
    __tablename__ = 'schedule_comments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_id = Column(Integer, ForeignKey('collaborative_schedules.id', ondelete='CASCADE'), nullable=False, index=True)
    author_identifier = Column(String(255), nullable=False)
    author_display_name = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    is_admin_note = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    schedule = relationship('CollaborativeSchedule', back_populates='comments')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'schedule_id': self.schedule_id,
            'author_identifier': self.author_identifier,
            'author_display_name': self.author_display_name,
            'content': self.content,
            'is_admin_note': self.is_admin_note,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
