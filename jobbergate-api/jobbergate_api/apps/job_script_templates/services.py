"""Services for the job_script_templates resource, including module specific business logic."""

from typing import Any

from buzz import require_condition
from fastapi import status
from sqlalchemy import not_
from sqlalchemy.sql.expression import Select

from jobbergate_api.apps.job_script_templates.models import JobScriptTemplate
from jobbergate_api.apps.services import CrudModel, CrudService, FileService, ServiceError


class JobScriptTemplateService(CrudService):
    """
    Provide a CrudService that overloads the list query builder and locator logic.
    """

    def build_list_query(
        self,
        sort_ascending: bool = True,
        search: str | None = None,
        sort_field: str | None = None,
        include_archived: bool = True,
        include_files: bool = False,
        include_parent: bool = False,
        include_null_identifier: bool = True,
        **additional_filters,
    ) -> Select:
        """List all job_script_templates."""
        query: Select = super().build_list_query(
            sort_ascending=sort_ascending,
            search=search,
            sort_field=sort_field,
            include_archived=include_archived,
            include_files=include_files,
            include_parent=include_parent,
            **additional_filters,
        )
        if not include_null_identifier:
            query = query.where(not_(JobScriptTemplate.identifier.is_(None)))
        return query

    async def create(self, **incoming_data) -> CrudModel:
        """
        Add a new row for the model to the database.
        """
        self.validate_identifier(incoming_data.get("identifier"))
        return await super().create(**incoming_data)

    async def update(self, locator: Any, **incoming_data) -> CrudModel:
        """
        Update a row by locator with supplied data.
        """
        self.validate_identifier(incoming_data.get("identifier"))
        return await super().update(locator, **incoming_data)

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

    def validate_identifier(self, identifier: str | None) -> None:
        """
        Validate that the identifier is not an empty string nor composed only by digits.

        Raise a ServiceError with status code 422 if the validation fails.

        Many of the job-script-template endpoints use the id or identifier interchangeably
        as a path parameter. With that, we need to ensure that the identifier is
        not a number, as that would be identified as id.
        """
        if identifier is not None:
            require_condition(
                identifier.strip() and not identifier.isdigit(),
                "Identifier on {} can not be a empty string nor be composed only by digits. Got {}".format(
                    self.name, identifier
                ),
                raise_exc_class=ServiceError,
                raise_kwargs=dict(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY),
            )


class JobScriptTemplateFileService(FileService):
    """
    Provide an empty derived class of FileService.

    Although it doesn't do anything, it fixes errors with mypy:
        error: Value of type variable "FileModel" of "FileService" cannot be "JobScriptTemplateFile"
        error: Value of type variable "FileModel" of "FileService" cannot be "WorkflowFile"
    """
