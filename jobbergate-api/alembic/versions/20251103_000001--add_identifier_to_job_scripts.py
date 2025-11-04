"""Add identifier column to job_scripts

Revision ID: add_identifier_job_scripts
Revises: 2fb98836df57
Create Date: 2025-11-03 00:00:01

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_identifier_job_scripts"
down_revision = "2fb98836df57"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("job_scripts", sa.Column("identifier", sa.String(), nullable=True))
    op.create_index(
        op.f("ix_job_scripts_identifier"),
        "job_scripts",
        ["identifier"],
        unique=True,
    )


def downgrade():
    op.drop_index(op.f("ix_job_scripts_identifier"), table_name="job_scripts")
    op.drop_column("job_scripts", "identifier")
