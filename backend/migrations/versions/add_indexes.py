"""Add indexes to speed common queries

Revision ID: add_indexes
Revises: add_course_offering_details
Create Date: 2025-12-12

"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    # B-tree indexes for common filters and joins
    op.create_index('ix_courses_semester', 'courses', ['semester'], unique=False)
    op.create_index('ix_courses_department', 'courses', ['department'], unique=False)
    op.create_index('ix_courses_instructor', 'courses', ['instructor'], unique=False)
    # composite index for queries filtering by course_code + semester
    op.create_index('ix_courses_course_code_semester', 'courses', ['course_code', 'semester'], unique=False)

    # course_offerings lookups
    op.create_index('ix_course_offerings_course_id', 'course_offerings', ['course_id'], unique=False)
    op.create_index('ix_course_offerings_term', 'course_offerings', ['term'], unique=False)

    # reservations: frequently filter by offering_id and status
    op.create_index('ix_reservations_offering_status', 'reservations', ['offering_id', 'status'], unique=False)
    op.create_index('ix_reservations_user_id', 'reservations', ['user_id'], unique=False)

    # For faster ILIKE searches on text fields, create pg_trgm GIN index if Postgres is used
    conn = op.get_bind()
    try:
        # enable pg_trgm extension if available
        conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        # GIN trigram index on concatenated name + description for faster ILIKE searches
        conn.execute("CREATE INDEX IF NOT EXISTS ix_courses_name_description_trgm ON courses USING gin((coalesce(name,'') || ' ' || coalesce(description,'')) gin_trgm_ops);")
    except Exception:
        # ignore if not Postgres or extension not available
        pass


def downgrade():
    # drop indexes created above
    try:
        op.drop_index('ix_courses_name_description_trgm', table_name='courses')
    except Exception:
        pass
    try:
        op.drop_index('ix_reservations_user_id', table_name='reservations')
    except Exception:
        pass
    try:
        op.drop_index('ix_reservations_offering_status', table_name='reservations')
    except Exception:
        pass
    try:
        op.drop_index('ix_course_offerings_term', table_name='course_offerings')
    except Exception:
        pass
    try:
        op.drop_index('ix_course_offerings_course_id', table_name='course_offerings')
    except Exception:
        pass
    try:
        op.drop_index('ix_courses_course_code_semester', table_name='courses')
    except Exception:
        pass
    try:
        op.drop_index('ix_courses_instructor', table_name='courses')
    except Exception:
        pass
    try:
        op.drop_index('ix_courses_department', table_name='courses')
    except Exception:
        pass
    try:
        op.drop_index('ix_courses_semester', table_name='courses')
    except Exception:
        pass
