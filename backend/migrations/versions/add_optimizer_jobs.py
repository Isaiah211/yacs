"""Create optimizer_jobs table

Revision ID: add_optimizer_jobs
Revises: add_indexes
Create Date: 2025-12-12

"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'optimizer_jobs',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('rq_job_id', sa.String(64), nullable=True, unique=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='queued'),
        sa.Column('params', sa.JSON, nullable=True),
        sa.Column('result', sa.JSON, nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('progress', sa.Integer, nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('finished_at', sa.DateTime, nullable=True),
    )


def downgrade():
    op.drop_table('optimizer_jobs')
