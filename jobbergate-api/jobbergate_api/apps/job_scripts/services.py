"""Services for the job_scripts resource, including module specific business logic."""

from jobbergate_api.apps.job_scripts.models import JobScript, JobScriptFile
from jobbergate_api.apps.services import CrudService, FileService

crud_service = CrudService(model_type=JobScript)
file_service = FileService(model_type=JobScriptFile)
