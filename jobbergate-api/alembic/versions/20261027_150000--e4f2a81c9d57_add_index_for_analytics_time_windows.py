"""add index for analytics time windows

Revision ID: e4f2a81c9d57
Revises: c7a1d94e2f38
Create Date: 2026-10-27 15:00:00.000000

The analytics endpoints select job submissions by a created_at window on every
report request (Grafana panels, CLI reports). This index lets those WHERE
clauses run as range scans instead of sequential scans over the whole table.

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e4f2a81c9d57"
down_revision = "c7a1d94e2f38"
branch_labels = None
depends_on = None


def upgrade():
    """
    Add an index covering the analytics created_at window filters.
    """
    op.create_index(
        "idx_job_submissions_created_at",
        "job_submissions",
        ["created_at"],
    )


def downgrade():
    """
    Drop the analytics created_at index.
    """
    op.drop_index("idx_job_submissions_created_at", table_name="job_submissions")
