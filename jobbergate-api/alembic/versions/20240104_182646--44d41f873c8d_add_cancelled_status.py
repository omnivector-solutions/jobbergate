"""Add cancelled status

Revision ID: 44d41f873c8d
Revises: b15213c159f1
Create Date: 2024-01-04 18:26:46.943872

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers, used by Alembic.
revision = "44d41f873c8d"
down_revision = "b15213c159f1"
branch_labels = None
depends_on = None

old_status_list = ["CREATED", "SUBMITTED", "COMPLETED", "FAILED", "UNKNOWN", "REJECTED"]
new_status_list = old_status_list + ["CANCELLED"]

old_type = postgresql.ENUM(*old_status_list, name="jobsubmissionstatus")
new_type = postgresql.ENUM(*new_status_list, name="jobsubmissionstatus")
tmp_type = postgresql.ENUM(*new_status_list, name="_status")


def upgrade():
    # Create a temporary "_status" type, convert and drop the "old" type
    tmp_type.create(op.get_bind(), checkfirst=False)
    op.execute("ALTER TABLE job_submissions ALTER COLUMN status TYPE _status USING status::text::_status")
    old_type.drop(op.get_bind(), checkfirst=False)
    # Create and convert to the "new" jobsubmissionstatus type
    new_type.create(op.get_bind(), checkfirst=False)
    op.execute(
        "ALTER TABLE job_submissions ALTER COLUMN status TYPE jobsubmissionstatus"
        " USING status::text::jobsubmissionstatus"
    )
    tmp_type.drop(op.get_bind(), checkfirst=False)


def downgrade():
    # Convert 'CANCELLED' status into 'UNKNOWN'
    op.execute("UPDATE job_submissions SET status = 'UNKNOWN' WHERE status = 'CANCELLED'")
    # Create a temporary "_status" type, convert and drop the "new" type
    tmp_type.create(op.get_bind(), checkfirst=False)
    op.execute("ALTER TABLE job_submissions ALTER COLUMN status TYPE _status" " USING status::text::_status")
    new_type.drop(op.get_bind(), checkfirst=False)
    # Create and convert to the "old" status type
    old_type.create(op.get_bind(), checkfirst=False)
    op.execute(
        "ALTER TABLE job_submissions ALTER COLUMN status TYPE _status"
        " USING status::text::jobsubmissionstatus"
    )
    tmp_type.drop(op.get_bind(), checkfirst=False)