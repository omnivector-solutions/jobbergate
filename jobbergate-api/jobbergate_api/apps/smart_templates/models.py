"""Database models for the smart template resource."""
from sqlalchemy import DateTime, Integer, String, Table, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Column

from jobbergate_api.metadata import metadata

smart_templates_table = Table(
    "smart_templates",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False, index=True),
    Column("identifier", String, unique=True, index=True),
    Column(
        "runtime_config",
        JSONB,
        nullable=False,
        default=text("'{}'::jsonb"),
        server_default=text("'{}'::jsonb"),
    ),
    Column("description", String, default=""),
    Column("owner_email", String, nullable=False, index=True),
    Column("created_at", DateTime, nullable=False, default=func.now()),
    Column("updated_at", DateTime, nullable=False, default=func.now(), onupdate=func.now()),
    Column("file_key", String, nullable=True),
)

searchable_fields = [
    smart_templates_table.c.name,
    smart_templates_table.c.identifier,
    smart_templates_table.c.description,
    smart_templates_table.c.owner_email,
]

sortable_fields = [
    smart_templates_table.c.id,
    smart_templates_table.c.name,
    smart_templates_table.c.identifier,
    smart_templates_table.c.owner_email,
    smart_templates_table.c.created_at,
    smart_templates_table.c.updated_at,
]
