"""Create student_preferences table

Revision ID: add_student_preferences
Revises:
Create Date: 2025-11-18

"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'student_preferences',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, nullable=True),
        sa.Column('max_credits_per_term', sa.Integer, nullable=True),
        sa.Column('unavailable_days', sa.String(20), nullable=True),
        sa.Column('avoid_mornings', sa.Boolean, nullable=True),
        sa.Column('avoid_evenings', sa.Boolean, nullable=True),
        sa.Column('preferred_instructors', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
    )


def downgrade():
    op.drop_table('student_preferences')
