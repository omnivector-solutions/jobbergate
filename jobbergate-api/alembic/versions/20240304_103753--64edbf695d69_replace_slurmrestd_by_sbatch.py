"""Replace slurmrestd by sbatch

Revision ID: 64edbf695d69
Revises: ec2d2948fb41
Create Date: 2024-03-04 10:37:53.921645

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "64edbf695d69"
down_revision = "ec2d2948fb41"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("job_submissions", sa.Column("sbatch_arguments", sa.ARRAY(sa.String()), nullable=True))
    op.drop_column("job_submissions", "template_vars")


def downgrade():
    op.add_column(
        "job_submissions",
        sa.Column(
            "template_vars",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.drop_column("job_submissions", "sbatch_arguments")
