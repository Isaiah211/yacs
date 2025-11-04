"""Add pathway tables

Revision ID: add_pathway_tables
Revises: add_semester_table
Create Date: 2023-11-04

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create pathways table
    op.create_table(
        'pathways',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('code', sa.String, nullable=False),
        sa.Column('description', sa.String),
        sa.Column('total_credits', sa.Integer, nullable=False)
    )

    # Create unique index on pathway code
    op.create_index('uix_pathway_code', 'pathways', ['code'], unique=True)

    # Create pathway requirements table
    op.create_table(
        'pathway_requirements',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('pathway_id', sa.Integer, sa.ForeignKey('pathways.id'), nullable=False),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('description', sa.String),
        sa.Column('credits_required', sa.Integer, nullable=False),
        sa.Column('course_count_required', sa.Integer)
    )

    # Create association tables
    op.create_table(
        'pathway_courses',
        sa.Column('pathway_id', sa.Integer, sa.ForeignKey('pathways.id')),
        sa.Column('course_id', sa.String, sa.ForeignKey('courses.id')),
        sa.PrimaryKeyConstraint('pathway_id', 'course_id')
    )

    op.create_table(
        'requirement_courses',
        sa.Column('requirement_id', sa.Integer, sa.ForeignKey('pathway_requirements.id')),
        sa.Column('course_id', sa.String, sa.ForeignKey('courses.id')),
        sa.PrimaryKeyConstraint('requirement_id', 'course_id')
    )

def downgrade():
    # Drop tables in reverse order
    op.drop_table('requirement_courses')
    op.drop_table('pathway_courses')
    op.drop_table('pathway_requirements')
    op.drop_index('uix_pathway_code', table_name='pathways')
    op.drop_table('pathways')