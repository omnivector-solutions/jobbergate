"""Services for the job_script_templates resource, including module specific business logic."""
from typing import Any

from sqlalchemy import not_
from sqlalchemy.sql.expression import Select

from jobbergate_api.apps.job_script_templates.models import (
    JobScriptTemplate,
    JobScriptTemplateFile,
    WorkflowFile,
)
from jobbergate_api.apps.services import CrudService, FileService


class JobScriptTemplateService(CrudService):
    def build_list_query(
        self,
        include_null_identifier: bool = True,
        **filter_kwargs,
    ) -> Select:
        """List all job_script_templates."""
        query: Select = super().build_list_query(**filter_kwargs)
        if not include_null_identifier:
            query = query.where(not_(JobScriptTemplate.identifier.is_(None)))
        return query

    def locate_where_clause(self, id_or_identifier: Any) -> Any:
        if isinstance(id_or_identifier, str):
            return JobScriptTemplate.identifier == id_or_identifier
        elif isinstance(id_or_identifier, int):
            return JobScriptTemplate.id == id_or_identifier
        else:
            raise ValueError("id_or_identifier must be a string or integer")


crud_service = JobScriptTemplateService(model_type=JobScriptTemplate)
template_file_service = FileService(model_type=JobScriptTemplateFile)
workflow_file_service = FileService(model_type=WorkflowFile)
