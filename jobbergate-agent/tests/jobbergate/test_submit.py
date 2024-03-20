"""
Define tests for the submission functions of the jobbergate section.
"""

import getpass
import json
import re
from pathlib import Path
from unittest import mock

import httpx
import pytest
import respx

from jobbergate_agent.jobbergate.schemas import JobScriptFile, PendingJobSubmission
from jobbergate_agent.jobbergate.submit import (
    fetch_pending_submissions,
    get_job_script_file,
    mark_as_rejected,
    mark_as_submitted,
    process_supporting_files,
    retrieve_submission_file,
    submit_job_script,
    submit_pending_jobs,
    write_submission_file,
)
from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.exception import JobbergateApiError, JobSubmissionError
from jobbergate_agent.utils.user_mapper import SingleUserMapper, SlurmUserMapper, manufacture


class RegexArgMatcher:
    """
    Specialty class to be used as a matcher for partial args with mock call assertions.
    """

    def __init__(self, pattern, flags=0):
        self.pattern = pattern
        self.flags = flags

    def __eq__(self, other):
        return re.match(self.pattern, other, self.flags)

    def __repr__(self):
        return f"regex='{self.pattern}' (flags={self.flags})"


@pytest.fixture
def user_mapper():
    return SingleUserMapper(getpass.getuser())


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
@pytest.mark.asyncio
async def test_retrieve_submission_file__success():
    """
    Test that the ``retrieve_submission_file()`` function can retrieve a submission file
    from the backend and return its content.
    """
    job_script_file = JobScriptFile(
        parent_id=1,
        filename="application.sh",
        file_type="ENTRYPOINT",
        path="/jobbergate/job-scripts/1/upload/application.sh",
    )

    async with respx.mock:
        download_route = respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-scripts/1/upload/application.sh")
        download_route.mock(
            return_value=httpx.Response(
                status_code=200,
                content="I am a job script".encode("utf-8"),
            ),
        )

        actual_content = await retrieve_submission_file(job_script_file)

        assert actual_content == "I am a job script"
        assert download_route.call_count == 1
        last_request = download_route.calls.last.request
        assert last_request.url == f"{SETTINGS.BASE_API_URL}/jobbergate/job-scripts/1/upload/application.sh"


@pytest.mark.usefixtures("mock_access_token")
@pytest.mark.asyncio
async def test_retrieve_submission_file__raises_exception():
    """
    Test that the ``retrieve_submission_file()`` function raises an exception if the
    backend returns a non-200 response.
    """
    job_script_file = JobScriptFile(
        parent_id=1,
        filename="application.sh",
        file_type="ENTRYPOINT",
        path="/jobbergate/job-scripts/1/upload/application.sh",
    )

    async with respx.mock:
        download_route = respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-scripts/1/upload/application.sh")
        download_route.mock(
            return_value=httpx.Response(
                status_code=400,
            ),
        )

        with pytest.raises(
            httpx.HTTPStatusError,
        ):
            await retrieve_submission_file(job_script_file)


@pytest.mark.asyncio
async def test_write_submission_file__success(tmp_path):
    """
    Test that the ``write_submission_file()`` function can write a submission file to disk.
    """
    job_script_content = "I am a job script"
    submit_dir = tmp_path / "submit"
    submit_dir.mkdir()

    await write_submission_file(job_script_content, "application.sh", submit_dir)

    assert (submit_dir / "application.sh").read_text() == "I am a job script"


@pytest.mark.usefixtures("mock_access_token")
@pytest.mark.asyncio
async def test_process_supporting_files__with_write_submission_files_set_to_true(
    tmp_path,
    dummy_pending_job_submission_with_supporting_files_data,
    tweak_settings,
):
    """
    Test that the ``process_supporting_files()`` function can write submission files to disk.

    The files should be written to the submit_dir if WRITE_SUBMISSION_FILES is set to True.
    """
    pending_job_submission = PendingJobSubmission(**dummy_pending_job_submission_with_supporting_files_data)
    submit_dir = tmp_path / "submit"
    submit_dir.mkdir()

    async with respx.mock:
        download_support_route = respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-scripts/1/upload/input.txt")
        download_support_route.mock(
            return_value=httpx.Response(
                status_code=200,
                content="I am a supporting file".encode("utf-8"),
            ),
        )
        with tweak_settings(WRITE_SUBMISSION_FILES=True):
            supporting_files = await process_supporting_files(pending_job_submission, submit_dir)

    assert supporting_files == [submit_dir / "input.txt"]
    assert (submit_dir / "input.txt").read_text() == "I am a supporting file"
    assert download_support_route.call_count == 1


@pytest.mark.asyncio
async def test_process_supporting_files__with_write_submission_files_set_to_false_and_supporting_files(
    tmp_path,
    dummy_pending_job_submission_with_supporting_files_data,
    tweak_settings,
):
    """
    Test that the ``process_supporting_files()`` function can reject a submission if there
    are supporting files and WRITE_SUBMISSION_FILES is set to False.
    """
    pending_job_submission = PendingJobSubmission(**dummy_pending_job_submission_with_supporting_files_data)
    submit_dir = tmp_path / "submit"
    submit_dir.mkdir()

    with tweak_settings(WRITE_SUBMISSION_FILES=False):
        with pytest.raises(
            JobSubmissionError,
            match="Job submission rejected. The submission has supporting files that can't be downloaded to "
            "the execution dir. Set `WRITE_SUBMISSION_FILES` setting to `True` to download the "
            "job script files to the execution dir.",
        ):
            await process_supporting_files(pending_job_submission, submit_dir)


@pytest.mark.asyncio
async def test_process_supporting_files__with_write_submission_files_set_to_false_and_no_supporting_files(
    tmp_path,
    dummy_pending_job_submission_data,
    tweak_settings,
):
    """
    Test that the ``process_supporting_files()`` function can accept a submission if there
    are no supporting files and WRITE_SUBMISSION_FILES is set to False.
    """
    pending_job_submission = PendingJobSubmission(**dummy_pending_job_submission_data)
    submit_dir = tmp_path / "submit"
    submit_dir.mkdir()

    with tweak_settings(WRITE_SUBMISSION_FILES=False):
        await process_supporting_files(pending_job_submission, submit_dir)


@pytest.mark.usefixtures("mock_access_token")
@pytest.mark.asyncio
async def test_get_job_script_file__success_with_write(tmp_path, dummy_pending_job_submission_data, tweak_settings):
    """
    Test that the ``get_job_script_file()`` function can retrieve a job script file
    from the backend, write the content to the submit dir, and return its content.
    """
    pending_job_submission = PendingJobSubmission(**dummy_pending_job_submission_data)
    submit_dir = tmp_path / "submit"
    submit_dir.mkdir()

    async with respx.mock:
        download_route = respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-scripts/1/upload/application.sh")
        download_route.mock(
            return_value=httpx.Response(
                status_code=200,
                content="I am a job script".encode("utf-8"),
            ),
        )

        file_path = await get_job_script_file(pending_job_submission, submit_dir)

    assert file_path == submit_dir / "application.sh"
    assert file_path.read_text() == "I am a job script"
    assert (submit_dir / "application.sh").read_text() == "I am a job script"
    assert download_route.call_count == 1
    last_request = download_route.calls.last.request
    assert last_request.url == f"{SETTINGS.BASE_API_URL}/jobbergate/job-scripts/1/upload/application.sh"


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_fetch_pending_submissions__success(dummy_job_script_files):
    """
    Test that the ``fetch_pending_submissions()`` function can successfully retrieve
    PendingJobSubmission objects from the API.
    """
    pending_job_submissions_data = {
        "items": [
            dict(
                id=1,
                name="sub1",
                owner_email="email1@dummy.com",
                job_script={"files": dummy_job_script_files},
                slurm_job_id=111,
            ),
            dict(
                id=2,
                name="sub2",
                owner_email="email2@dummy.com",
                job_script={"files": dummy_job_script_files},
                slurm_job_id=222,
            ),
            dict(
                id=3,
                name="sub3",
                owner_email="email3@dummy.com",
                job_script={"files": dummy_job_script_files},
                slurm_job_id=333,
            ),
        ]
    }
    async with respx.mock:
        respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/pending").mock(
            return_value=httpx.Response(
                status_code=200,
                json=pending_job_submissions_data,
            )
        )

        pending_job_submissions = await fetch_pending_submissions()
        for i, pending_job_submission in enumerate(pending_job_submissions):
            assert isinstance(pending_job_submission, PendingJobSubmission)
            assert i + 1 == pending_job_submission.id


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_fetch_pending_submissions__raises_JobbergateApiError_if_response_is_not_200():  # noqa
    """
    Test that the ``fetch_pending_submissions()`` function will raise a
    JobbergateApiError if the response from the API is not OK (200).
    """
    with respx.mock:
        respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/pending").mock(
            return_value=httpx.Response(status_code=400)
        )

        with pytest.raises(JobbergateApiError, match="Failed to fetch pending"):
            await fetch_pending_submissions()


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_fetch_pending_submissions__raises_JobbergateApiError_if_response_cannot_be_deserialized():  # noqa
    """
    Test that the ``fetch_pending_submissions()`` function will raise a
    JobbergateApiError if it fails to convert the response to a PendingJobSubmission.
    """
    pending_job_submissions_data = [
        dict(bad="data"),
    ]
    with respx.mock:
        respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/pending").mock(
            return_value=httpx.Response(
                status_code=200,
                json=pending_job_submissions_data,
            )
        )

        with pytest.raises(JobbergateApiError, match="Failed to fetch pending"):
            await fetch_pending_submissions()


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_mark_as_submitted__success():
    """
    Test that ``mark_as_submitted()`` can successfully report a job submission as submitted to the Jobbergate API
    with its ``slurm_job_id``.
    """
    with respx.mock:
        update_route = respx.post(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/submitted")
        update_route.mock(return_value=httpx.Response(status_code=200))

        await mark_as_submitted(1, 111)
        assert update_route.called
        last_request = update_route.calls.last.request
        assert json.loads(last_request.content) == dict(id=1, slurm_job_id=111)


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_mark_as_submitted__raises_JobbergateApiError_if_the_response_is_not_200():
    """
    Test that the ``mark_as_submitted()`` function will raise a JobbergateApiError if
    the response from the API is not OK (200).
    """
    with respx.mock:
        update_route = respx.post(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/submitted")
        update_route.mock(return_value=httpx.Response(status_code=400))

        with pytest.raises(
            JobbergateApiError,
            match="Could not mark job submission 1 as submitted",
        ):
            await mark_as_submitted(1, 111)
        assert update_route.called


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_mark_as_rejected__success():
    """
    Test that ``mark_as_rejected()`` can successfully report a job submission as rejected to the Jobbergate API
    with its ``report_message``.
    """
    with respx.mock:
        update_route = respx.post(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/rejected")
        update_route.mock(return_value=httpx.Response(status_code=200))

        await mark_as_rejected(1, "something went wrong")
        assert update_route.called
        last_request = update_route.calls.last.request
        assert json.loads(last_request.content) == dict(id=1, report_message="something went wrong")


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_mark_as_rejected__raises_JobbergateApiError_if_the_response_is_not_200():
    """
    Test that the ``mark_as_rejected()`` function will raise a JobbergateApiError if
    the response from the API is not OK (200).
    """
    with respx.mock:
        update_route = respx.post(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/rejected")
        update_route.mock(return_value=httpx.Response(status_code=400))

        with pytest.raises(
            JobbergateApiError,
            match="Could not mark job submission 1 as rejected",
        ):
            await mark_as_rejected(1, "something went wrong")
        assert update_route.called


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_submit_job_script__success_with_files(
    mocker, dummy_pending_job_submission_data, dummy_template_source, tweak_settings, user_mapper
):
    """
    Test that the ``submit_job_script()`` successfully submits a job.

    Verifies that a PendingJobSubmission instance is submitted via the Slurm REST API
    and that a ``slurm_job_id`` is returned.
    """
    pending_job_submission = PendingJobSubmission(**dummy_pending_job_submission_data)

    mocked_sbatch = mock.MagicMock()
    mocked_sbatch.submit_job = lambda *args, **kwargs: 13
    mocker.patch("jobbergate_agent.jobbergate.submit.SubmissionHandler", return_value=mocked_sbatch)

    async with respx.mock:
        download_route = respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-scripts/1/upload/application.sh")
        download_route.mock(
            return_value=httpx.Response(
                status_code=200,
                content=dummy_template_source.encode("utf-8"),
            ),
        )
        with tweak_settings(WRITE_SUBMISSION_FILES=True):
            slurm_job_id = await submit_job_script(pending_job_submission, user_mapper)

    assert slurm_job_id == 13
    assert download_route.call_count == 1

    assert mocked_sbatch.copy_file_to_submission_directory.call_count == len(pending_job_submission.job_script.files)


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_submit_job_script__success_without_files(
    mocker, dummy_pending_job_submission_data, dummy_template_source, tweak_settings, user_mapper
):
    """
    Test that the ``submit_job_script()`` successfully submits a job.

    Verifies that a PendingJobSubmission instance is submitted via the Slurm REST API
    and that a ``slurm_job_id`` is returned.
    """
    pending_job_submission = PendingJobSubmission(**dummy_pending_job_submission_data)

    mocked_sbatch = mock.MagicMock()
    mocked_sbatch.submit_job = lambda *args, **kwargs: 13
    mocker.patch("jobbergate_agent.jobbergate.submit.SubmissionHandler", return_value=mocked_sbatch)

    async with respx.mock:
        download_route = respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-scripts/1/upload/application.sh")
        download_route.mock(
            return_value=httpx.Response(
                status_code=200,
                content=dummy_template_source.encode("utf-8"),
            ),
        )
        with tweak_settings(WRITE_SUBMISSION_FILES=False):
            slurm_job_id = await submit_job_script(pending_job_submission, user_mapper)

    assert slurm_job_id == 13
    assert download_route.call_count == 1

    assert mocked_sbatch.copy_file_to_submission_directory.call_count == 0


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_submit_job_script__with_non_default_execution_directory(
    dummy_pending_job_submission_data,
    dummy_template_source,
    mocker,
    tmp_path,
    user_mapper,
):
    """
    Test that the ``submit_job_script()`` successfully submits a job with an exec dir.

    Verifies that a PendingJobSubmission instance is submitted via the Slurm REST API
    and that a ``slurm_job_id`` is returned. Verifies that the execution_directory is
    taken from the request and submitted to slurm rest api.
    """
    exe_path = tmp_path / "exec"
    exe_path.mkdir()
    pending_job_submission = PendingJobSubmission(
        **dummy_pending_job_submission_data,
        execution_directory=exe_path,
    )

    mocked_sbatch = mock.MagicMock()
    mocked_sbatch.submit_job = lambda *args, **kwargs: 13
    mocker.patch("jobbergate_agent.jobbergate.submit.SubmissionHandler", return_value=mocked_sbatch)

    async with respx.mock:
        download_route = respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-scripts/1/upload/application.sh")
        download_route.mock(
            return_value=httpx.Response(
                status_code=200,
                content=dummy_template_source.encode("utf-8"),
            ),
        )

        slurm_job_id = await submit_job_script(pending_job_submission, user_mapper)

        assert slurm_job_id == 13
        assert download_route.call_count == 1


@pytest.mark.usefixtures("mock_access_token")
async def test_submit_job_script__raises_exception_if_no_executable_script_was_found(
    dummy_pending_job_submission_data, mocker, user_mapper
):
    """
    Test that the ``submit_job_script()`` will raise a JobSubmissionError if it cannot
    find an executable job script in the retrieved pending job submission data
    and that the ``mark_as_rejected`` method is called for the job submission.
    """
    pending_job_submission = PendingJobSubmission(**dummy_pending_job_submission_data)
    pending_job_submission.job_script.files = []

    mock_mark_as_rejected = mocker.patch("jobbergate_agent.jobbergate.submit.mark_as_rejected")

    mocked_sbatch = mock.MagicMock()
    mocker.patch("jobbergate_agent.jobbergate.submit.SubmissionHandler", return_value=mocked_sbatch)

    with pytest.raises(JobSubmissionError, match="Could not find an executable"):
        await submit_job_script(pending_job_submission, user_mapper)

    mock_mark_as_rejected.assert_called_once_with(
        dummy_pending_job_submission_data["id"],
        RegexArgMatcher(".*Could not find an executable.*"),
    )


@pytest.mark.usefixtures("mock_access_token")
async def test_submit_job_script__raises_exception_if_execution_dir_does_not_exist(
    dummy_pending_job_submission_data, mocker, user_mapper
):
    pending_job_submission = PendingJobSubmission(**dummy_pending_job_submission_data)
    pending_job_submission.execution_directory = Path("/non/existing/path")

    mock_mark_as_rejected = mocker.patch("jobbergate_agent.jobbergate.submit.mark_as_rejected")

    mocked_sbatch = mock.MagicMock()
    mocker.patch("jobbergate_agent.jobbergate.submit.SubmissionHandler", return_value=mocked_sbatch)

    with pytest.raises(JobSubmissionError, match="The submission directory must exist and be an absolute path"):
        await submit_job_script(pending_job_submission, user_mapper)

    mock_mark_as_rejected.assert_called_once_with(
        dummy_pending_job_submission_data["id"],
        RegexArgMatcher(".*The submission directory must exist and be an absolute path.*"),
    )


@pytest.mark.usefixtures("mock_access_token")
async def test_submit_job_script__raises_exception_if_execution_dir_is_relative(
    dummy_pending_job_submission_data, mocker, user_mapper, tmp_path
):
    pending_job_submission = PendingJobSubmission(**dummy_pending_job_submission_data)
    pending_job_submission.execution_directory = Path("./existing/")

    submit_dir = tmp_path / pending_job_submission.execution_directory
    submit_dir.mkdir()
    assert submit_dir.is_dir()

    mock_mark_as_rejected = mocker.patch("jobbergate_agent.jobbergate.submit.mark_as_rejected")

    mocked_sbatch = mock.MagicMock()
    mocker.patch("jobbergate_agent.jobbergate.submit.SubmissionHandler", return_value=mocked_sbatch)

    with pytest.raises(JobSubmissionError, match="The submission directory must exist and be an absolute path"):
        await submit_job_script(pending_job_submission, user_mapper)

    mock_mark_as_rejected.assert_called_once_with(
        dummy_pending_job_submission_data["id"],
        RegexArgMatcher(".*The submission directory must exist and be an absolute path.*"),
    )


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_submit_job_script__raises_exception_if_sbatch_fails(
    dummy_pending_job_submission_data, mocker, dummy_template_source, user_mapper
):
    """
    Test that ``submit_job_script()`` raises an exception if the response from sbatch
    is not 0. Verifies that the error message is included in the raised
    exception and that the ``mark_as_rejected`` method is called for the job submission.
    """
    pending_job_submission = PendingJobSubmission(**dummy_pending_job_submission_data)

    mock_mark_as_rejected = mocker.patch("jobbergate_agent.jobbergate.submit.mark_as_rejected")

    mocked_sbatch = mock.MagicMock()
    mocked_sbatch.submit_job.side_effect = RuntimeError("BOOM!")
    mocker.patch("jobbergate_agent.jobbergate.submit.SubmissionHandler", return_value=mocked_sbatch)

    async with respx.mock:
        respx.post(f"https://{SETTINGS.OIDC_DOMAIN}/oauth/token").mock(
            return_value=httpx.Response(
                status_code=200,
                json=dict(access_token="dummy-token"),
            )
        )

        download_route = respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-scripts/1/upload/application.sh")
        download_route.mock(
            return_value=httpx.Response(
                status_code=200,
                content=dummy_template_source.encode("utf-8"),
            ),
        )

        with pytest.raises(
            JobSubmissionError,
            match="Failed to submit job to slurm",
        ):
            await submit_job_script(pending_job_submission, user_mapper)

    assert download_route.call_count == 1

    mock_mark_as_rejected.assert_called_once_with(
        dummy_pending_job_submission_data["id"],
        RegexArgMatcher(".*Failed to submit job to slurm.*BOOM!.*"),
    )


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_submit_pending_jobs(
    dummy_job_script_files,
    dummy_template_source,
    mocker,
):
    """
    Test that the ``submit_pending_jobs()`` function can fetch pending job submissions,
    submit each to slurm via the Slurm REST API, and update the job submission via the
    Jobbergate API.
    """

    pending_submissions = [
        PendingJobSubmission(
            id=1,
            name="sub1",
            owner_email="email1@dummy.com",
            job_script={"files": dummy_job_script_files},
        ),
        PendingJobSubmission(
            id=2,
            name="sub2",
            owner_email="email2@dummy.com",
            job_script={"files": dummy_job_script_files},
        ),
        PendingJobSubmission(
            id=3,
            name="sub3",
            owner_email="email3@dummy.com",
            job_script={"files": dummy_job_script_files},
        ),
    ]

    mocker.patch(
        "jobbergate_agent.jobbergate.submit.fetch_pending_submissions",
        return_value=pending_submissions,
    )

    def _mocked_submit_job_script(pending_job_submission: PendingJobSubmission, user_mapper: SlurmUserMapper):
        if pending_job_submission.id == 3:
            raise Exception("BOOM!")
        return pending_job_submission.id * 11

    def _mocked_mark_as_submitted(job_submission_id: int, slurm_job_id: int):
        if job_submission_id == 2:
            raise Exception("BANG!")

    mock_submit = mocker.patch(
        "jobbergate_agent.jobbergate.submit.submit_job_script", side_effect=_mocked_submit_job_script
    )
    mock_mark = mocker.patch(
        "jobbergate_agent.jobbergate.submit.mark_as_submitted", side_effect=_mocked_mark_as_submitted
    )

    test_mapper = manufacture()

    await submit_pending_jobs()

    mock_submit.assert_has_calls(
        [
            mocker.call(pending_submissions[0], test_mapper),
            mocker.call(pending_submissions[1], test_mapper),
            mocker.call(pending_submissions[2], test_mapper),
        ]
    )
    assert mock_submit.call_count == 3

    mock_mark.assert_has_calls(
        [
            mocker.call(1, 11),
            mocker.call(2, 22),
        ]
    )
    assert mock_mark.call_count == 2
