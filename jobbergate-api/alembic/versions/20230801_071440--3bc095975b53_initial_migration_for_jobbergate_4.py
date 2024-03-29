"""Initial migration for Jobbergate 4.x

Revision ID: 3bc095975b53
Revises: 
Create Date: 2023-08-01 07:14:40.860152

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "3bc095975b53"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "job_script_templates",
        sa.Column("identifier", sa.String(), nullable=True),
        sa.Column(
            "template_vars",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("owner_email", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_job_script_templates_identifier"), "job_script_templates", ["identifier"], unique=True
    )
    op.create_index(op.f("ix_job_script_templates_name"), "job_script_templates", ["name"], unique=False)
    op.create_index(
        op.f("ix_job_script_templates_owner_email"), "job_script_templates", ["owner_email"], unique=False
    )
    op.create_table(
        "job_script_template_files",
        sa.Column("parent_id", sa.Integer(), nullable=False),
        sa.Column(
            "file_type", sa.Enum("ENTRYPOINT", "SUPPORT", name="filetype", native_enum=False), nullable=False
        ),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["job_script_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("parent_id", "filename"),
    )
    op.create_table(
        "job_scripts",
        sa.Column("parent_template_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("owner_email", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["parent_template_id"], ["job_script_templates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_job_scripts_name"), "job_scripts", ["name"], unique=False)
    op.create_index(op.f("ix_job_scripts_owner_email"), "job_scripts", ["owner_email"], unique=False)
    op.create_table(
        "workflow_files",
        sa.Column("parent_id", sa.Integer(), nullable=False),
        sa.Column(
            "runtime_config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["job_script_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("parent_id", "filename"),
    )
    op.create_table(
        "job_script_files",
        sa.Column("parent_id", sa.Integer(), nullable=False),
        sa.Column(
            "file_type", sa.Enum("ENTRYPOINT", "SUPPORT", name="filetype", native_enum=False), nullable=False
        ),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["job_scripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("parent_id", "filename"),
    )
    op.create_table(
        "job_submissions",
        sa.Column("job_script_id", sa.Integer(), nullable=True),
        sa.Column("execution_directory", sa.String(), nullable=True),
        sa.Column("slurm_job_id", sa.Integer(), nullable=True),
        sa.Column("client_id", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "CREATED",
                "SUBMITTED",
                "COMPLETED",
                "FAILED",
                "UNKNOWN",
                "REJECTED",
                name="jobsubmissionstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("report_message", sa.String(), nullable=True),
        sa.Column(
            "template_vars",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("owner_email", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(
            ["job_script_id"],
            ["job_scripts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_job_submissions_client_id"), "job_submissions", ["client_id"], unique=False)
    op.create_index(op.f("ix_job_submissions_name"), "job_submissions", ["name"], unique=False)
    op.create_index(op.f("ix_job_submissions_owner_email"), "job_submissions", ["owner_email"], unique=False)
    op.create_index(op.f("ix_job_submissions_status"), "job_submissions", ["status"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_job_submissions_status"), table_name="job_submissions")
    op.drop_index(op.f("ix_job_submissions_owner_email"), table_name="job_submissions")
    op.drop_index(op.f("ix_job_submissions_name"), table_name="job_submissions")
    op.drop_index(op.f("ix_job_submissions_client_id"), table_name="job_submissions")
    op.drop_table("job_submissions")
    op.drop_table("job_script_files")
    op.drop_table("workflow_files")
    op.drop_index(op.f("ix_job_scripts_owner_email"), table_name="job_scripts")
    op.drop_index(op.f("ix_job_scripts_name"), table_name="job_scripts")
    op.drop_table("job_scripts")
    op.drop_table("job_script_template_files")
    op.drop_index(op.f("ix_job_script_templates_owner_email"), table_name="job_script_templates")
    op.drop_index(op.f("ix_job_script_templates_name"), table_name="job_script_templates")
    op.drop_index(op.f("ix_job_script_templates_identifier"), table_name="job_script_templates")
    op.drop_table("job_script_templates")
