"""
Router for the JobSubmission resource.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from fastapi import Response as FastAPIResponse
from fastapi import status
from fastapi_pagination import Page
from loguru import logger
from jobbergate_api.apps.job_submissions.models import JobSubmissionMetric
from sqlalchemy import select, insert, text as sa_text
from sqlalchemy.sql.functions import max
import msgpack
from sqlalchemy.exc import IntegrityError

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.dependencies import SecureService, secure_services
from jobbergate_api.apps.job_submissions.constants import (
    JobSubmissionStatus,
    slurm_job_state_details,
    JobSubmissionMetricSampleRate,
)
from jobbergate_api.apps.job_submissions.schemas import (
    ActiveJobSubmission,
    JobSubmissionAgentRejectedRequest,
    JobSubmissionAgentSubmittedRequest,
    JobSubmissionAgentUpdateRequest,
    JobSubmissionCreateRequest,
    JobSubmissionDetailedView,
    JobSubmissionListView,
    JobSubmissionUpdateRequest,
    PendingJobSubmission,
    JobSubmissionAgentMetricsRequest,
    JobSubmissionAgentMaxTimes,
    JobSubmissionMetricSchema,
)
from jobbergate_api.apps.job_submissions.helpers import (
    validate_job_metric_upload_input,
    build_job_metric_aggregation_query,
)
from jobbergate_api.apps.permissions import Permissions, can_bypass_ownership_check
from jobbergate_api.apps.schemas import ListParams
from jobbergate_api.email_notification import notify_submission_rejected
from jobbergate_api.rabbitmq_notification import publish_status_change

router = APIRouter(prefix="/job-submissions", tags=["Job Submissions"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    description="Endpoint for job_submission creation",
    response_model=JobSubmissionDetailedView,
)
async def job_submission_create(
    create_request: JobSubmissionCreateRequest,
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_CREATE, ensure_email=True)
    ),
):
    """
    Create a new job submission.

    Make a post request to this endpoint with the required values to create a new job submission.
    """
    logger.debug(f"Creating job submissions with {create_request=}")

    client_id = create_request.client_id or secure_services.identity_payload.client_id
    if client_id is None:
        message = "Could not find a client_id in the request body or auth token."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )
    create_request.client_id = client_id

    base_job_script = await secure_services.crud.job_script.get(
        create_request.job_script_id, include_files=True
    )

    job_script_files = [f for f in base_job_script.files if f.file_type == FileType.ENTRYPOINT]

    if len(job_script_files) != 1:
        message = "Job script {} has {} entrypoint files, one and only one is required".format(
            create_request.job_script_id, len(job_script_files)
        )
        logger.warning(message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    if create_request.slurm_job_id is None:
        submission_status = JobSubmissionStatus.CREATED
    else:
        submission_status = JobSubmissionStatus.SUBMITTED

    new_job_submission = await secure_services.crud.job_submission.create(
        **create_request.model_dump(exclude_unset=True),
        owner_email=secure_services.identity_payload.email,
        status=submission_status,
    )
    return new_job_submission


@router.post(
    "/clone/{id}",
    status_code=status.HTTP_201_CREATED,
    response_model=JobSubmissionDetailedView,
    description="Endpoint for cloning a job submission under the CREATED status for a new run on the cluster",
)
async def job_submission_clone(
    id: int = Path(...),
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_CREATE, ensure_email=True)
    ),
):
    """Clone a job_submission given its id."""
    logger.info(f"Cloning job submission {id=}")

    original_instance = await secure_services.crud.job_submission.get(id)

    if original_instance.job_script_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot resubmit a job submission without a parent job script",
        )

    cloned_instance = await secure_services.crud.job_submission.clone_instance(
        original_instance,
        owner_email=secure_services.identity_payload.email,
        status=JobSubmissionStatus.CREATED,
        report_message=None,
        slurm_job_id=None,
        slurm_job_info=None,
        slurm_job_state=None,
    )

    return cloned_instance


@router.get(
    "/{id}",
    description="Endpoint to get a job_submission",
    response_model=JobSubmissionDetailedView,
)
async def job_submission_get(
    id: int = Path(...),
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_READ, commit=False)
    ),
):
    """Return the job_submission given its id."""
    logger.debug(f"Getting job submission {id=}")
    return await secure_services.crud.job_submission.get(id)


@router.get(
    "",
    description="Endpoint to list job_submissions",
    response_model=Page[JobSubmissionListView],
)
async def job_submission_get_list(
    list_params: ListParams = Depends(),
    slurm_job_ids: str | None = Query(
        None,
        description="Comma-separated list of slurm-job-ids to match active job_submissions",
    ),
    submit_status: JobSubmissionStatus | None = Query(
        None,
        description="Limit results to those with matching status",
    ),
    from_job_script_id: int | None = Query(
        None,
        description="Filter job-submissions by the job-script-id they were created from.",
    ),
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_READ, commit=False)
    ),
):
    """List job_submissions for the authenticated user."""
    logger.debug("Fetching job submissions")

    list_kwargs = list_params.model_dump(
        exclude_unset=True,
        exclude={"user_only", "include_archived"},
    )
    list_kwargs["include_parent"] = True

    if list_params.user_only:
        list_kwargs["owner_email"] = secure_services.identity_payload.email
    if submit_status:
        list_kwargs["status"] = submit_status
    if from_job_script_id:
        list_kwargs["job_script_id"] = from_job_script_id
    if slurm_job_ids:
        try:
            list_kwargs["filter_slurm_job_ids"] = [int(i) for i in slurm_job_ids.split(",")]
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid slurm_job_ids param. Must be a comma-separated list of integers",
            )

    return await secure_services.crud.job_submission.paginated_list(**list_kwargs)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete job submission",
)
async def job_submission_delete(
    id: int = Path(..., description="id of the job submission to delete"),
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_DELETE, ensure_email=True)
    ),
):
    """Delete job_submission given its id."""
    logger.info(f"Deleting job submission {id=}")
    instance = await secure_services.crud.job_submission.get(id)
    if not can_bypass_ownership_check(secure_services.identity_payload.permissions):
        secure_services.crud.job_submission.ensure_attribute(
            instance, owner_email=secure_services.identity_payload.email
        )
    await secure_services.crud.job_submission.delete(id)
    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/{id}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to update a job_submission given the id",
    response_model=JobSubmissionDetailedView,
)
async def job_submission_update(
    update_params: JobSubmissionUpdateRequest,
    id: int = Path(),
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_UPDATE, ensure_email=True)
    ),
):
    """Update a job_submission given its id."""
    logger.debug(f"Updating {id=} with {update_params=}")
    instance = await secure_services.crud.job_submission.get(id)
    if not can_bypass_ownership_check(secure_services.identity_payload.permissions):
        secure_services.crud.job_submission.ensure_attribute(
            instance, owner_email=secure_services.identity_payload.email
        )
    return await secure_services.crud.job_submission.update(
        id, **update_params.model_dump(exclude_unset=True)
    )


# The "agent" routes are used for agents to fetch pending job submissions and update their statuses
@router.put(
    "/agent/{id}",
    status_code=status.HTTP_202_ACCEPTED,
    description="Endpoint for an agent to update the status of a job_submission",
    tags=["Agent"],
)
async def job_submission_agent_update(
    update_params: JobSubmissionAgentUpdateRequest,
    id: int = Path(),
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_UPDATE, ensure_client_id=True)
    ),
):
    """
    Update a job_submission with slurm_job_state and slurm_job_info.

    Note that if the new slurm_job_state is a termination state, the job submission status will be updated.
    """
    logger.debug(f"Agent is requesting to update {id=}")

    job_submission = await secure_services.crud.job_submission.get(
        id, ensure_attributes={"client_id": secure_services.identity_payload.client_id}
    )

    if job_submission.status != JobSubmissionStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only SUBMITTED jobs may be updated by the agent",
        )

    if job_submission.slurm_job_id != update_params.slurm_job_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Update slurm job id does not match the job id on record for job submission {id}",
        )

    logger.info(
        f"Setting slurm job state status to: {update_params.slurm_job_state} "
        f"for job_submission: {id} "
        f"on client_id: {secure_services.identity_payload.client_id}"
    )

    update_dict: dict[str, Any] = dict(
        slurm_job_id=update_params.slurm_job_id,
        slurm_job_state=update_params.slurm_job_state,
        slurm_job_info=update_params.slurm_job_info,
    )

    job_state_details = slurm_job_state_details[update_params.slurm_job_state]
    if job_state_details.is_abort_status:
        update_dict["status"] = JobSubmissionStatus.ABORTED
        update_dict["report_message"] = update_params.slurm_job_state_reason
    elif job_state_details.is_done_status:
        update_dict["status"] = JobSubmissionStatus.DONE

    job_submission = await secure_services.crud.job_submission.update(id, **update_dict)

    if job_submission.status in (
        JobSubmissionStatus.ABORTED,
        JobSubmissionStatus.DONE,
    ):
        await publish_status_change(
            job_submission,
            organization_id=secure_services.identity_payload.organization_id,
        )

    return FastAPIResponse(status_code=status.HTTP_202_ACCEPTED)


@router.post(
    "/agent/submitted",
    description="Endpoint to report that a pending job_submission was submitted",
    tags=["Agent"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def job_submissions_agent_submitted(
    submitted_request: JobSubmissionAgentSubmittedRequest,
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_UPDATE, ensure_client_id=True)
    ),
):
    """Update a job_submission to indicate that it was submitted to Slurm."""
    logger.debug("Agent is reporting that a pending job has been submitted")

    job_submission = await secure_services.crud.job_submission.get(
        submitted_request.id, ensure_attributes={"client_id": secure_services.identity_payload.client_id}
    )
    if job_submission.status != JobSubmissionStatus.CREATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CREATED Job Submissions can be marked as SUBMITTED",
        )

    logger.info(f"Marking job_submissions {submitted_request.id} as SUBMITTED")

    await secure_services.crud.job_submission.update(
        submitted_request.id,
        slurm_job_id=submitted_request.slurm_job_id,
        slurm_job_state=submitted_request.slurm_job_state,
        slurm_job_info=submitted_request.slurm_job_info,
        report_message=submitted_request.slurm_job_state_reason,
        status=JobSubmissionStatus.SUBMITTED,
    )
    return FastAPIResponse(status_code=status.HTTP_202_ACCEPTED)


@router.post(
    "/agent/rejected",
    description="Endpoint to report that a pending job_submission was rejected by Slurm",
    tags=["Agent"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def job_submissions_agent_rejected(
    rejected_request: JobSubmissionAgentRejectedRequest,
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_UPDATE, ensure_client_id=True)
    ),
):
    """Update a job_submission to indicate that it was rejected by Slurm."""
    logger.debug("Agent is reporting that a pending job has been rejected")

    job_submission = await secure_services.crud.job_submission.get(
        rejected_request.id, ensure_attributes={"client_id": secure_services.identity_payload.client_id}
    )
    if job_submission.status != JobSubmissionStatus.CREATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CREATED Job Submissions can be marked as REJECTED",
        )

    logger.info(f"Marking job_submissions {rejected_request.id} as REJECTED")

    await secure_services.crud.job_submission.update(
        rejected_request.id,
        status=JobSubmissionStatus.REJECTED,
        report_message=rejected_request.report_message,
    )
    notify_submission_rejected(
        rejected_request.id,
        rejected_request.report_message,
        job_submission.owner_email,
    )

    await publish_status_change(
        job_submission,
        organization_id=secure_services.identity_payload.organization_id,
    )

    return FastAPIResponse(status_code=status.HTTP_202_ACCEPTED)


@router.get(
    "/agent/pending",
    description="Endpoint to list pending job_submissions for the requesting client",
    response_model=Page[PendingJobSubmission],
    response_model_exclude_none=True,
    tags=["Agent"],
)
async def job_submissions_agent_pending(
    secure_services: SecureService = Depends(
        secure_services(
            Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_READ, commit=False, ensure_client_id=True
        )
    ),
):
    """Get a list of pending job submissions for the cluster-agent."""
    logger.debug("Agent is requesting a list of pending job submissions")

    client_id = secure_services.identity_payload.client_id

    logger.info(f"Fetching newly created job_submissions for {client_id=}")

    return await secure_services.crud.job_submission.paginated_list(
        status=JobSubmissionStatus.CREATED,
        client_id=client_id,
        include_files=True,
        include_parent=True,
    )


@router.get(
    "/agent/active",
    description="Endpoint to list active job_submissions for the requesting client",
    response_model=Page[ActiveJobSubmission],
    tags=["Agent"],
)
async def job_submissions_agent_active(
    secure_services: SecureService = Depends(
        secure_services(
            Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_READ, commit=False, ensure_client_id=True
        )
    ),
):
    """Get a list of active job submissions for the cluster-agent."""
    logger.debug("Agent is requesting a list of active job submissions")

    client_id = secure_services.identity_payload.client_id

    logger.info(f"Fetching active job_submissions for {client_id=}")

    pages = await secure_services.crud.job_submission.paginated_list(
        status=JobSubmissionStatus.SUBMITTED,
        client_id=client_id,
    )
    return pages


@router.get(
    "/agent/metrics/{job_submission_id}",
    description="Endpoint to get metrics for a job submission",
    response_model=JobSubmissionAgentMetricsRequest,
    tags=["Agent", "Metrics"],
)
async def job_submissions_agent_metrics(
    job_submission_id: int,
    secure_services: SecureService = Depends(
        secure_services(
            Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_READ, commit=False, ensure_client_id=True
        )
    ),
):
    """Get the max times for the tuple (node_host, step, task) of a job submission."""
    logger.debug(f"Agent is requesting metrics for job submission {job_submission_id}")

    query = (
        select(
            max(JobSubmissionMetric.time).label("max_time"),
            JobSubmissionMetric.node_host,
            JobSubmissionMetric.step,
            JobSubmissionMetric.task,
        )
        .where(JobSubmissionMetric.job_submission_id == job_submission_id)
        .group_by(
            JobSubmissionMetric.node_host,
            JobSubmissionMetric.step,
            JobSubmissionMetric.task,
        )
    )

    result = await secure_services.session.execute(query)

    return JobSubmissionAgentMetricsRequest(
        job_submission_id=job_submission_id,
        max_times=[JobSubmissionAgentMaxTimes.model_validate(row) for row in result.all()],
    )


@router.put(
    "/agent/metrics/{job_submission_id}",
    description="Endpoint to upload metrics for a job submission",
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Metrics uploaded successfully"},
        status.HTTP_400_BAD_REQUEST: {"description": "Either invalid metrics data or duplicate metrics data"},
    },
    tags=["Agent", "Metrics"],
)
async def job_submissions_agent_metrics_upload(
    job_submission_id: int,
    body: bytes = Body(..., description="The binary data to upload"),
    secure_services: SecureService = Depends(
        secure_services(
            Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_UPDATE, ensure_client_id=True, commit=True
        )
    ),
):
    """Upload metrics for a job submission."""
    logger.debug(f"Agent is uploading metrics for job submission {job_submission_id}")

    logger.debug(f"Getting slurm_job_id of job submission {job_submission_id}")
    job_submission = await secure_services.crud.job_submission.get(
        job_submission_id, ensure_attributes={"client_id": secure_services.identity_payload.client_id}
    )
    slurm_job_id = job_submission.slurm_job_id
    logger.debug(f"Got slurm_job_id {slurm_job_id}")

    logger.debug("Decoding binary data")
    data = msgpack.unpackb(body)

    logger.debug("Asserting the decoded binary data structure")
    try:
        data = validate_job_metric_upload_input(
            data, (int, str, int, int, float, float, float, int, float, int, int, int, int, int)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    else:
        logger.debug("Decoded data is valid")

    logger.debug("Inserting metrics into the database")
    query = insert(JobSubmissionMetric).values(
        [
            {
                "time": data_point[0],
                "node_host": data_point[1],
                "step": data_point[2],
                "task": data_point[3],
                "cpu_frequency": data_point[4],
                "cpu_time": data_point[5],
                "cpu_utilization": data_point[6],
                "gpu_memory": data_point[7],
                "gpu_utilization": data_point[8],
                "page_faults": data_point[9],
                "memory_rss": data_point[10],
                "memory_virtual": data_point[11],
                "disk_read": data_point[12],
                "disk_write": data_point[13],
                "job_submission_id": job_submission_id,
                "slurm_job_id": slurm_job_id,
            }
            for data_point in data
        ]
    )
    try:
        await secure_services.session.execute(query)
    except IntegrityError as e:
        logger.error(f"Failed to insert metrics: {e.args}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to insert metrics",
        )

    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{job_submission_id}/metrics",
    description="Endpoint to get metrics for a job submission",
    response_model=list[JobSubmissionMetricSchema],
    tags=["Metrics"],
)
async def job_submissions_metrics(
    job_submission_id: int,
    node: str | None = Query(
        None, description="Filter by node_host. If omitted, metrics will be gathered over all nodes."
    ),
    start_time: datetime = Query(
        datetime.now(tz=timezone.utc) - timedelta(hours=1),
        description="Start time for the metrics query. Defaults to one hour ago.",
    ),
    sample_rate: JobSubmissionMetricSampleRate = Query(
        JobSubmissionMetricSampleRate.ten_minutes, description="Sample rate in seconds for the metrics query."
    ),
    end_time: datetime | None = Query(
        None,
        description="End time for the metrics query. If omitted, assume the window to be up to the present.",
    ),
    secure_services: SecureService = Depends(
        secure_services(Permissions.ADMIN, Permissions.JOB_SUBMISSIONS_READ, commit=False)
    ),
):
    """Get the metrics for a job submission."""
    logger.debug(f"Getting metrics for job submission {job_submission_id}")
    if end_time is not None and end_time < start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be greater than the start time.",
        )
    end_time = end_time or datetime.now(tz=timezone.utc)

    query = build_job_metric_aggregation_query(node, sample_rate)
    query_params = {
        "job_submission_id": job_submission_id,
        "start_time": start_time,
        "end_time": end_time,
    }
    if node is not None:
        query_params["node_host"] = node

    result = await secure_services.session.execute(sa_text(query), query_params)
    return [JobSubmissionMetricSchema.from_iterable(row, skip_optional=True) for row in result.fetchall()]
