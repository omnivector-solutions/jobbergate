"""Database models for the job_script_templates resource."""
from sqlalchemy import DateTime, Integer, String, Table, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Column

from jobbergate_api.metadata import metadata

job_script_templates_table = Table(
    "job_script_templates",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False, index=True),
    Column("description", String, default=""),
    Column(
        "template_vars",
        JSONB,
        nullable=False,
        default=text("'{}'::jsonb"),
        server_default=text("'{}'::jsonb"),
    ),
    Column("owner_email", String, nullable=False, index=True),
    Column("created_at", DateTime, nullable=False, default=func.now()),
    Column("updated_at", DateTime, nullable=False, default=func.now(), onupdate=func.now()),
)

searchable_fields = [
    job_script_templates_table.c.name,
    job_script_templates_table.c.description,
    job_script_templates_table.c.owner_email,
]

sortable_fields = [
    job_script_templates_table.c.id,
    job_script_templates_table.c.name,
    job_script_templates_table.c.owner_email,
    job_script_templates_table.c.created_at,
    job_script_templates_table.c.updated_at,
]
