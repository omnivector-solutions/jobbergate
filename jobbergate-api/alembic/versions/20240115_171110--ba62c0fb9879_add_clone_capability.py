"""Add clone capability

Revision ID: ba62c0fb9879
Revises: 44d41f873c8d
Create Date: 2024-01-15 17:11:10.626366

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "ba62c0fb9879"
down_revision = "44d41f873c8d"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("job_script_templates", sa.Column("cloned_from_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "clone",
        "job_script_templates",
        "job_script_templates",
        ["cloned_from_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("job_scripts", sa.Column("cloned_from_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "clone", "job_scripts", "job_scripts", ["cloned_from_id"], ["id"], ondelete="SET NULL"
    )
    op.add_column("job_submissions", sa.Column("cloned_from_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "clone", "job_submissions", "job_submissions", ["cloned_from_id"], ["id"], ondelete="SET NULL"
    )


def downgrade():
    op.drop_constraint("clone", "job_submissions", type_="foreignkey")
    op.drop_column("job_submissions", "cloned_from_id")
    op.drop_constraint("clone", "job_scripts", type_="foreignkey")
    op.drop_column("job_scripts", "cloned_from_id")
    op.drop_constraint("clone", "job_script_templates", type_="foreignkey")
    op.drop_column("job_script_templates", "cloned_from_id")
