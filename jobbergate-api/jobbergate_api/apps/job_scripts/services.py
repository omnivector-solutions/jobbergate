"""Services for the job_scripts resource, including module specific business logic."""

from jobbergate_api.apps.job_scripts.models import JobScript, JobScriptFile
from jobbergate_api.apps.services import CrudService, FileService


class JobScriptCrudService(CrudService):
    """
    Provide an empty derived class of CrudService.

    Although it doesn't do anything, it fixes an error with mypy:
        error: Value of type variable "CrudModel" of "CrudService" cannot be "JobScript"
    """


class JobScriptFileService(FileService):
    """
    Provide an empty derived class of FileService.

    Although it doesn't do anything, it fixes an error with mypy:
        error: Value of type variable "FileModel" of "FileService" cannot be "JobScriptFile"
    """


crud_service = JobScriptCrudService(model_type=JobScript)
file_service = JobScriptFileService(model_type=JobScriptFile)
