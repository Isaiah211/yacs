"""Add detailed columns to course_offerings

Revision ID: add_course_offering_details
Revises: add_course_offerings
Create Date: 2025-11-11

"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    # Add additional columns to support sections, meeting times, capacity, etc.
    op.add_column('course_offerings', sa.Column('days', sa.String(20), nullable=True))
    op.add_column('course_offerings', sa.Column('start_time', sa.String(10), nullable=True))
    op.add_column('course_offerings', sa.Column('end_time', sa.String(10), nullable=True))
    op.add_column('course_offerings', sa.Column('instructor', sa.String(100), nullable=True))
    op.add_column('course_offerings', sa.Column('location', sa.String(100), nullable=True))
    op.add_column('course_offerings', sa.Column('capacity', sa.Integer, nullable=True))
    op.add_column('course_offerings', sa.Column('enrolled', sa.Integer, nullable=True))
    op.add_column('course_offerings', sa.Column('notes', sa.Text, nullable=True))


def downgrade():
    op.drop_column('course_offerings', 'notes')
    op.drop_column('course_offerings', 'enrolled')
    op.drop_column('course_offerings', 'capacity')
    op.drop_column('course_offerings', 'location')
    op.drop_column('course_offerings', 'instructor')
    op.drop_column('course_offerings', 'end_time')
    op.drop_column('course_offerings', 'start_time')
    op.drop_column('course_offerings', 'days')
