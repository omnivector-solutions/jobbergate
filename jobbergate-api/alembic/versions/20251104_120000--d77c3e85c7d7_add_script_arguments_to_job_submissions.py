"""Add script_arguments column to job_submissions

Revision ID: d77c3e85c7d7
Revises: d0285508f97f
Create Date: 2025-11-04 12:00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d77c3e85c7d7"
down_revision = "d0285508f97f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "job_submissions",
        sa.Column("script_arguments", sa.ARRAY(sa.String()), nullable=True),
    )


def downgrade():
    op.drop_column("job_submissions", "script_arguments")
