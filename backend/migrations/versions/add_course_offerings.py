"""Add course_offerings table

Revision ID: add_course_offerings
Revises: add_pathway_tables
Create Date: 2025-11-11

"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'course_offerings',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('course_id', sa.Integer, sa.ForeignKey('courses.id'), nullable=False),
        sa.Column('term', sa.String(20), nullable=False),
        sa.Column('year', sa.Integer, nullable=True),
        sa.Column('section', sa.String(50), nullable=True),
    )


def downgrade():
    op.drop_table('course_offerings')
