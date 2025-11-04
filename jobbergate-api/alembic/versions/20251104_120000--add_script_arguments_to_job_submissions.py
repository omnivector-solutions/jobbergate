"""Add script_arguments column to job_submissions

Revision ID: add_script_arguments_job_submissions
Revises: add_identifier_job_scripts
Create Date: 2025-11-04 12:00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_script_arguments_job_submissions"
down_revision = "add_identifier_job_scripts"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "job_submissions",
        sa.Column("script_arguments", sa.ARRAY(sa.String()), nullable=True),
    )


def downgrade():
    op.drop_column("job_submissions", "script_arguments")
