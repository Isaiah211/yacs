"""Create reservations table

Revision ID: add_reservations
Revises:
Create Date: 2025-11-21

"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'reservations',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('offering_id', sa.Integer, sa.ForeignKey('course_offerings.id'), nullable=False),
        sa.Column('user_id', sa.Integer, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='held'),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('seats', sa.Integer, nullable=True, server_default='1'),
        sa.Column('notes', sa.Text, nullable=True),
    )


def downgrade():
    op.drop_table('reservations')
