from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from .database import Base


class OptimizerJob(Base):
    __tablename__ = 'optimizer_jobs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    rq_job_id = Column(String(64), nullable=True, unique=True)
    status = Column(String(32), nullable=False, default='queued')
    params = Column(JSONB, nullable=True)
    result = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    progress = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'rq_job_id': self.rq_job_id,
            'status': self.status,
            'params': self.params,
            'result': self.result,
            'error': self.error,
            'progress': self.progress,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
        }
