"""Add cluster statuses endpoints

Revision ID: 815022877cfe
Revises: 64edbf695d69
Create Date: 2024-04-17 14:48:52.956389

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "815022877cfe"
down_revision = "64edbf695d69"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cluster_statuses",
        sa.Column("client_id", sa.String(), nullable=False),
        sa.Column("interval", sa.Integer(), nullable=False),
        sa.Column("last_reported", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("client_id"),
    )


def downgrade():
    op.drop_table("cluster_statuses")
