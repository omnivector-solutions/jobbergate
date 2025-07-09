"""add_cancelled_status_back_to_job_submission_status

Revision ID: 944e578d7b34
Revises: 31382ad313d1
Create Date: 2025-07-09 13:40:11.447842

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '944e578d7b34'
down_revision = '31382ad313d1'
branch_labels = None
depends_on = None


def upgrade():
    # Add CANCELLED to the JobSubmissionStatus enum
    # PostgreSQL requires special handling for enum changes
    op.execute("ALTER TYPE jobsubmissionstatus ADD VALUE 'CANCELLED'")


def downgrade():
    # Remove CANCELLED from the JobSubmissionStatus enum and fallback to SUBMITTED
    # First, update any CANCELLED submissions to SUBMITTED
    op.execute("UPDATE job_submissions SET status = 'SUBMITTED' WHERE status = 'CANCELLED'")
    
    # PostgreSQL doesn't support removing enum values directly in a simple way
    # We need to recreate the enum type without the CANCELLED value
    # This is the safe approach for production environments
    
    # Create new enum without CANCELLED
    new_enum = postgresql.ENUM(
        "CREATED", "SUBMITTED", "REJECTED", "DONE", "ABORTED",
        name="jobsubmissionstatus_new"
    )
    new_enum.create(op.get_bind(), checkfirst=False)
    
    # Convert the column to use the new enum
    op.execute(
        "ALTER TABLE job_submissions "
        "ALTER COLUMN status TYPE jobsubmissionstatus_new "
        "USING status::text::jobsubmissionstatus_new"
    )
    
    # Drop the old enum
    old_enum = postgresql.ENUM(
        "CREATED", "SUBMITTED", "REJECTED", "DONE", "ABORTED", "CANCELLED",
        name="jobsubmissionstatus"
    )
    old_enum.drop(op.get_bind(), checkfirst=False)
    
    # Rename the new enum to the original name
    op.execute("ALTER TYPE jobsubmissionstatus_new RENAME TO jobsubmissionstatus")
