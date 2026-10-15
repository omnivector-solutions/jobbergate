"""add index for submission status metrics

Revision ID: c7a1d94e2f38
Revises: b16b218ef5d6
Create Date: 2026-10-14 16:05:00.000000

The metrics endpoints aggregate all retained job submissions on every scrape.
This composite index lets the /metrics/submissions GROUP BY run as an
index-only scan instead of a sequential scan over the whole table.

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "c7a1d94e2f38"
down_revision = "b16b218ef5d6"
branch_labels = None
depends_on = None


def upgrade():
    """
    Add a composite index covering the submission status metrics aggregation.
    """
    op.create_index(
        "idx_job_submissions_client_id_status_slurm_job_state",
        "job_submissions",
        ["client_id", "status", "slurm_job_state"],
    )


def downgrade():
    """
    Drop the submission status metrics index.
    """
    op.drop_index(
        "idx_job_submissions_client_id_status_slurm_job_state",
        table_name="job_submissions",
    )
