"""Make parent job-script null on delete

Revision ID: b15213c159f1
Revises: 3bc095975b53
Create Date: 2023-09-06 18:15:40.385837

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b15213c159f1"
down_revision = "3bc095975b53"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("job_submissions_job_script_id_fkey", "job_submissions", type_="foreignkey")
    op.create_foreign_key(
        None, "job_submissions", "job_scripts", ["job_script_id"], ["id"], ondelete="SET NULL"
    )


def downgrade():
    op.drop_constraint(None, "job_submissions", type_="foreignkey")
    op.create_foreign_key(
        "job_submissions_job_script_id_fkey", "job_submissions", "job_scripts", ["job_script_id"], ["id"]
    )
