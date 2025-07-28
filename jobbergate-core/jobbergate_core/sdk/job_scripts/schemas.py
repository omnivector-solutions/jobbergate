from pydantic import BaseModel, NonNegativeInt

from jobbergate_core.sdk.constants import FileType
from jobbergate_core.sdk.job_templates.schemas import JobTemplateListView
from jobbergate_core.sdk.schemas import PydanticDateTime, TableResource


class JobScriptFileDetailedView(BaseModel):
    """Schema for the response to get a job-script file."""

    parent_id: NonNegativeInt
    filename: str
    file_type: FileType
    created_at: PydanticDateTime
    updated_at: PydanticDateTime


class JobScriptBaseView(TableResource):
    """
    Base schema for the request to an entry.

    Omits parent relationship.
    """

    parent_template_id: NonNegativeInt | None = None
    cloned_from_id: NonNegativeInt | None = None


class JobScriptListView(JobScriptBaseView):
    """
    Schema for the response to get a list of entries.

    Notice files are omitted. Parent template can be included.
    """

    template: JobTemplateListView | None = None


class JobScriptDetailedView(JobScriptBaseView):
    """
    Schema for the request to an entry.

    Notice the files default to None, as they are not always requested, to differentiate between
    an empty list when they are requested, but no file is found.
    """

    files: list[JobScriptFileDetailedView] | None = None
