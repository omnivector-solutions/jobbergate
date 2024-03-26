"""Remap job submissions statuses

Revision ID: ec2d2948fb41
Revises: ba62c0fb9879
Create Date: 2024-01-30 10:52:38.671713

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "ec2d2948fb41"
down_revision = "ba62c0fb9879"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "job_submissions",
        sa.Column(
            "slurm_job_state",
            sa.Enum(
                "BOOT_FAIL",
                "CANCELLED",
                "COMPLETED",
                "CONFIGURING",
                "COMPLETING",
                "DEADLINE",
                "FAILED",
                "NODE_FAIL",
                "OUT_OF_MEMORY",
                "PENDING",
                "PREEMPTED",
                "RUNNING",
                "RESV_DEL_HOLD",
                "REQUEUE_FED",
                "REQUEUE_HOLD",
                "REQUEUED",
                "RESIZING",
                "REVOKED",
                "SIGNALING",
                "SPECIAL_EXIT",
                "STAGE_OUT",
                "STOPPED",
                "SUSPENDED",
                "TIMEOUT",
                "UNKNOWN",
                name="slurmjobstate",
                native_enum=False,
            ),
            nullable=True,
        ),
    )
    op.add_column("job_submissions", sa.Column("slurm_job_info", sa.String(), nullable=True))
    op.alter_column(
        "job_submissions",
        "status",
        existing_type=postgresql.ENUM(
            "CREATED",
            "SUBMITTED",
            "COMPLETED",
            "FAILED",
            "UNKNOWN",
            "REJECTED",
            "CANCELLED",
            name="jobsubmissionstatus",
        ),
        type_=sa.Enum(
            "CREATED",
            "SUBMITTED",
            "REJECTED",
            "DONE",
            "ABORTED",
            # -- Temporarily included until after remapping --
            "COMPLETED",
            "FAILED",
            "UNKNOWN",
            "CANCELLED",
            # ----
            name="jobsubmissionstatus",
            native_enum=False,
        ),
        existing_nullable=False,
    )

    # -- do the remapping --
    op.execute("UPDATE job_submissions SET status = 'DONE' WHERE status = 'COMPLETED'")
    op.execute("UPDATE job_submissions SET status = 'ABORTED' WHERE status = 'FAILED'")
    op.execute("UPDATE job_submissions SET status = 'ABORTED' WHERE status = 'UNKNOWN'")
    op.execute(
        """
        UPDATE job_submissions
        SET status = 'ABORTED',
            slurm_job_state = 'CANCELLED'
        WHERE status = 'CANCELLED'
    """
    )
    # ----

    op.alter_column(
        "job_submissions",
        "status",
        existing_type=postgresql.ENUM(
            "CREATED",
            "SUBMITTED",
            "REJECTED",
            "DONE",
            "ABORTED",
            "COMPLETED",
            "FAILED",
            "UNKNOWN",
            "CANCELLED",
            name="jobsubmissionstatus",
        ),
        type_=sa.Enum(
            "CREATED",
            "SUBMITTED",
            "REJECTED",
            "DONE",
            "ABORTED",
            name="jobsubmissionstatus",
            native_enum=False,
        ),
        existing_nullable=False,
    )


def downgrade():
    op.alter_column(
        "job_submissions",
        "status",
        existing_type=postgresql.ENUM(
            "CREATED",
            "SUBMITTED",
            "REJECTED",
            "DONE",
            "ABORTED",
            name="jobsubmissionstatus",
        ),
        type_=sa.Enum(
            "CREATED",
            "SUBMITTED",
            "COMPLETED",
            "FAILED",
            "UNKNOWN",
            "REJECTED",
            "CANCELLED",
            # -- Temporarily included until after remapping --
            "DONE",
            "ABORTED",
            # ----
            name="jobsubmissionstatus",
            native_enum=False,
        ),
        existing_nullable=False,
    )

    # -- do the remapping --
    op.execute(
        """
        UPDATE job_submissions
        SET status = 'CANCELLED'
        WHERE status = 'ABORTED'
        AND slurm_job_state = 'CANCELLED'
    """
    )
    op.execute("UPDATE job_submissions SET status = 'FAILED' WHERE status = 'ABORTED'")
    op.execute("UPDATE job_submissions SET status = 'COMPLETED' WHERE status = 'DONE'")
    # ----

    op.alter_column(
        "job_submissions",
        "status",
        existing_type=postgresql.ENUM(
            "CREATED",
            "SUBMITTED",
            "COMPLETED",
            "FAILED",
            "UNKNOWN",
            "REJECTED",
            "CANCELLED",
            "DONE",
            "ABORTED",
            name="jobsubmissionstatus",
        ),
        type_=sa.Enum(
            "CREATED",
            "SUBMITTED",
            "REJECTED",
            "DONE",
            "ABORTED",
            name="jobsubmissionstatus",
            native_enum=False,
        ),
        existing_nullable=False,
    )

    op.drop_column("job_submissions", "slurm_job_info")
    op.drop_column("job_submissions", "slurm_job_state")
