"""Smart template links models."""
from sqlalchemy import ForeignKey, Integer, Table
from sqlalchemy.sql.schema import Column

from jobbergate_api.metadata import metadata

smart_template_links_table = Table(
    "smart_template_links",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("smart_template_id", ForeignKey("smart_templates.id"), nullable=False),
    Column("job_script_template_id", ForeignKey("job_script_templates.id"), nullable=False),
)

searchable_fields = [
    smart_template_links_table.c.smart_template_id,
    smart_template_links_table.c.job_script_template_id,
]

sortable_fields = [
    smart_template_links_table.c.id,
    smart_template_links_table.c.smart_template_id,
    smart_template_links_table.c.job_script_template_id,
]
