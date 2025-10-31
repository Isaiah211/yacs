"""Add semester table

Revision ID: add_semester_table
Revises: 
Create Date: 2023-10-31

"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'semesters',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date, nullable=False),
        sa.Column('year', sa.Integer, nullable=False),
        sa.Column('term', sa.String, nullable=False)
    )


def downgrade():
    op.drop_table('semesters')