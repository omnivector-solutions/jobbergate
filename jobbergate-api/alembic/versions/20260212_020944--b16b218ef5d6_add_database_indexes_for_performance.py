"""add database indexes for performance optimization

Revision ID: b16b218ef5d6
Revises: 944e578d7b34
Create Date: 2026-02-12 02:09:44.000000

This migration adds several indexes to improve query performance:
1. Foreign key indexes for faster joins and lookups
2. Composite indexes for cleanup operations that filter by is_archived and updated_at
3. Indexes on frequently queried columns like slurm_job_id

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "b16b218ef5d6"
down_revision = "944e578d7b34"
branch_labels = None
depends_on = None


def upgrade():
    """
    Add indexes to improve query performance.
    """
    # 1. Add index on job_submissions.job_script_id (foreign key, frequently filtered)
    op.create_index(
        "idx_job_submissions_job_script_id",
        "job_submissions",
        ["job_script_id"],
        unique=False,
    )

    # 2. Add index on job_submissions.slurm_job_id (frequently queried for job lookups)
    op.create_index(
        "idx_job_submissions_slurm_job_id",
        "job_submissions",
        ["slurm_job_id"],
        unique=False,
    )

    # 3. Add composite index on job_submissions for cleanup queries
    # Used in queries that filter by: WHERE is_archived = ? AND updated_at < ?
    op.create_index(
        "idx_job_submissions_is_archived_updated_at",
        "job_submissions",
        ["is_archived", "updated_at"],
        unique=False,
    )

    # 4. Add index on job_scripts.parent_template_id (foreign key, used in joins)
    op.create_index(
        "idx_job_scripts_parent_template_id",
        "job_scripts",
        ["parent_template_id"],
        unique=False,
    )

    # 5. Add composite index on job_scripts for cleanup queries
    op.create_index(
        "idx_job_scripts_is_archived_updated_at",
        "job_scripts",
        ["is_archived", "updated_at"],
        unique=False,
    )

    # 6. Add composite index on job_script_templates for cleanup queries
    op.create_index(
        "idx_job_script_templates_is_archived_updated_at",
        "job_script_templates",
        ["is_archived", "updated_at"],
        unique=False,
    )

    # 7. Add index on job_submission_metrics.job_submission_id
    # Note: This is part of the composite primary key, but adding a standalone
    # index helps with foreign key lookups and cascade operations
    op.create_index(
        "idx_job_submission_metrics_job_submission_id",
        "job_submission_metrics",
        ["job_submission_id"],
        unique=False,
    )

    # 8. Add index on job_progress.job_submission_id (foreign key for cascade queries)
    op.create_index(
        "idx_job_progress_job_submission_id",
        "job_progress",
        ["job_submission_id"],
        unique=False,
    )


def downgrade():
    """
    Remove all indexes added in upgrade.
    """
    # Drop indexes in reverse order
    op.drop_index("idx_job_progress_job_submission_id", table_name="job_progress")
    op.drop_index(
        "idx_job_submission_metrics_job_submission_id",
        table_name="job_submission_metrics",
    )
    op.drop_index(
        "idx_job_script_templates_is_archived_updated_at",
        table_name="job_script_templates",
    )
    op.drop_index("idx_job_scripts_is_archived_updated_at", table_name="job_scripts")
    op.drop_index("idx_job_scripts_parent_template_id", table_name="job_scripts")
    op.drop_index(
        "idx_job_submissions_is_archived_updated_at",
        table_name="job_submissions",
    )
    op.drop_index("idx_job_submissions_slurm_job_id", table_name="job_submissions")
    op.drop_index("idx_job_submissions_job_script_id", table_name="job_submissions")
