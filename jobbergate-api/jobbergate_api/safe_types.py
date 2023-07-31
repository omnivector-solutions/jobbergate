"""
Provide "safe" type annotatons to avoid issues with mypy and Fast api.

Regarding the JobScript and JobSubmission type:
    These are needed for the relationships in the models. This avoids issues with circular imports at runtime.

Regarding the Bucket type:
    This is necessary because the Bucket type isn't importable from the normal boto3 modules. Instead, it must
    be imported from the mypy typing plugin for boto3.

    The "type" must be bound to Any when not type checking because FastAPI does type inspection for its
    dependency injection system. Thus, there must be a type associated with Bucket even when not type
    checking.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mypy_boto3_s3.service_resource import Bucket

    from jobbergate_api.apps.job_script_templates.models import JobScriptTemplate
    from jobbergate_api.apps.job_scripts.models import JobScript
    from jobbergate_api.apps.job_submissions.models import JobSubmission
else:
    Bucket = Any
    JobScriptTemplate = Any
    JobScript = Any
    JobSubmission = Any
