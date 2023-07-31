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
    """
    Provide a CrudService that overloads the list query builder and locator logic.
    """

    def build_list_query(
        self,
        sort_ascending: bool = True,
        user_email: str | None = None,
        search: str | None = None,
        sort_field: str | None = None,
        include_archived: bool = True,
        include_null_identifier: bool = True,
        **additional_filters,
    ) -> Select:
        """List all job_script_templates."""
        query: Select = super().build_list_query(
            sort_ascending=sort_ascending,
            user_email=user_email,
            search=search,
            sort_field=sort_field,
            include_archived=include_archived,
            **additional_filters,
        )
        if not include_null_identifier:
            query = query.where(not_(JobScriptTemplate.identifier.is_(None)))
        return query

    def locate_where_clause(self, id_or_identifier: Any) -> Any:
        """
        Locate an instance using the id or identifier field.
        """
        if isinstance(id_or_identifier, str):
            return JobScriptTemplate.identifier == id_or_identifier
        elif isinstance(id_or_identifier, int):
            return JobScriptTemplate.id == id_or_identifier
        else:
            raise ValueError("id_or_identifier must be a string or integer")


class JobScriptTemplateFileService(FileService):
    """
    Provide an empty derived class of FileService.

    Although it doesn't do anything, it fixes errors with mypy:
        error: Value of type variable "FileModel" of "FileService" cannot be "JobScriptTemplateFile"
        error: Value of type variable "FileModel" of "FileService" cannot be "WorkflowFile"
    """


crud_service = JobScriptTemplateService(model_type=JobScriptTemplate)
template_file_service = JobScriptTemplateFileService(model_type=JobScriptTemplateFile)
workflow_file_service = JobScriptTemplateFileService(model_type=WorkflowFile)
