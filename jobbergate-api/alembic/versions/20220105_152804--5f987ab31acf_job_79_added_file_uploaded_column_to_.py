"""JOB-79 Added file_uploaded column to applications

Revision ID: 5f987ab31acf
Revises: d3388a22e0e9
Create Date: 2022-01-05 15:28:04.021859

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "5f987ab31acf"
down_revision = "d3388a22e0e9"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "applications",
        sa.Column("application_uploaded", sa.Boolean(), server_default="false", nullable=False),
    )
    op.drop_index("ix_applications_identifier", table_name="applications")
    op.drop_column("applications", "identifier")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("applications", sa.Column("identifier", sa.VARCHAR(), autoincrement=False, nullable=True))
    op.create_index("ix_applications_identifier", "applications", ["identifier"], unique=False)
    op.drop_column("applications", "application_uploaded")
    # ### end Alembic commands ###