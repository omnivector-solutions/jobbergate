from typing import Any, Callable, Dict

import httpx
import pytest
import yaml
from typer import Context, Typer
from typer.testing import CliRunner

from jobbergate_cli.constants import JOBBERGATE_APPLICATION_CONFIG_FILE_NAME, JOBBERGATE_APPLICATION_MODULE_FILE_NAME
from jobbergate_cli.schemas import IdentityData, JobbergateApplicationConfig, JobbergateContext, Persona, TokenSet
from jobbergate_cli.subapps.applications.tools import load_application_from_source
from jobbergate_cli.text_tools import dedent


@pytest.fixture
def dummy_domain():
    return "https://dummy.com"


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def make_test_app(dummy_context):
    def _main_callback(ctx: Context):
        ctx.obj = dummy_context

    def _helper(command_name: str, command_function: Callable):
        main_app = Typer()
        main_app.callback()(_main_callback)
        main_app.command(name=command_name)(command_function)
        return main_app

    return _helper


@pytest.fixture
def dummy_context(dummy_domain):
    return JobbergateContext(
        persona=None,
        client=httpx.Client(base_url=dummy_domain, headers={"Authorization": "Bearer XXXXXXXX"}),
    )


@pytest.fixture
def attach_persona(dummy_context):
    def _helper(email: str, client_id: str = "dummy-client", access_token: str = "foo"):
        dummy_context.persona = Persona(
            token_set=TokenSet(access_token=access_token),
            identity_data=IdentityData(
                client_id=client_id,
                email=email,
            ),
        )

    return _helper


@pytest.fixture
def seed_clusters(mocker):
    def _helper(*client_ids):
        mocker.patch("jobbergate_cli.subapps.clusters.tools.pull_client_ids_from_api", return_value=client_ids)

    yield _helper


@pytest.fixture
def dummy_application_data():
    return [
        dict(
            id=1,
            name="test-app-1",
            identifier="test-app-1",
            description="Test Application Number 1",
            owner_email="tucker.beck@omnivector.solutions",
            created_at="2022-03-01 17:31:00",
            updated_at="2022-03-01 17:31:00",
            template_files=[
                {
                    "filename": "test-job-script.py.j2",
                    "parent_id": 1,
                    "created_at": "2022-03-01 17:31:00",
                    "updated_at": "2022-03-01 17:31:00",
                    "file_type": "ENTRYPOINT",
                }
            ],
            workflow_files=[
                {
                    "filename": "jobbergate.py",
                    "parent_id": 1,
                    "created_at": "2022-03-01 17:31:00",
                    "updated_at": "2022-03-01 17:31:00",
                },
            ],
        ),
        dict(
            id=2,
            name="test-app-2",
            identifier="test-app-2",
            description="Test Application Number 2",
            owner_email="tucker.beck@omnivector.solutions",
            created_at="2022-03-01 17:31:00",
            updated_at="2022-03-01 17:31:00",
        ),
        dict(
            id=3,
            name="test-app-3",
            identifier="test-app-3",
            description="Test Application Number 3",
            owner_email="tucker.beck@omnivector.solutions",
            created_at="2022-03-01 17:31:00",
            updated_at="2022-03-01 17:31:00",
        ),
    ]


@pytest.fixture
def dummy_job_script_file():
    return {
        "filename": "application.sh",
        "file_type": "ENTRYPOINT",
        "created_at": "2022-03-01 17:31:00",
        "updated_at": "2022-03-01 17:31:00",
    }


@pytest.fixture
def dummy_job_script_data(dummy_application_data, dummy_job_script_file):
    return [
        dict(
            id=1,
            created_at="2022-03-02 22:08:00",
            updated_at="2022-03-02 22:08:00",
            name="script1",
            description="Job Script 1",
            owner_email="tucker@omnivector.solutions",
            application_id=dummy_application_data[0]["id"],
            files=[dict(parent_id=1, **dummy_job_script_file)],
        ),
        dict(
            id=2,
            created_at="2022-03-02 22:08:00",
            updated_at="2022-03-02 22:08:00",
            name="script2",
            description="Job Script 2",
            owner_email="tucker@omnivector.solutions",
            application_id=1,
            files=[dict(parent_id=2, **dummy_job_script_file)],
        ),
        dict(
            id=3,
            created_at="2022-03-02 22:08:00",
            updated_at="2022-03-02 22:08:00",
            name="script3",
            description="Job Script 3",
            owner_email="james@omnivector.solutions",
            application_id=1,
            files=[dict(parent_id=3, **dummy_job_script_file)],
        ),
    ]


@pytest.fixture
def dummy_job_submission_data(dummy_job_script_data):
    return [
        dict(
            id=1,
            created_at="2022-03-02 22:08:00",
            updated_at="2022-03-02 22:08:00",
            name="sub1",
            description="Job Submission 1",
            owner_email="tucker@omnivector.solutions",
            job_script_id=dummy_job_script_data[0]["id"],
            slurm_job_id=13,
            status="CREATED",
            execution_parameters={
                "name": "job-submission-name-1",
                "comment": "I am a comment",
            },
        ),
        dict(
            id=1,
            created_at="2022-03-02 22:08:00",
            updated_at="2022-03-02 22:08:00",
            name="sub1",
            description="Job Submission 1",
            owner_email="tucker@omnivector.solutions",
            job_script_id=88,
            slurm_job_id=8888,
            status="CREATED",
            execution_parameters={
                "name": "job-submission-name-2",
                "comment": "I am a comment",
            },
        ),
        dict(
            id=3,
            created_at="2022-03-02 22:08:00",
            updated_at="2022-03-02 22:08:00",
            name="sub3",
            description="Job Submission 3",
            owner_email="tucker@omnivector.solutions",
            job_script_id=99,
            slurm_job_id=9999,
            status="CREATED",
            execution_parameters={
                "name": "job-submission-name-3",
                "comment": "I am a comment",
            },
        ),
        dict(
            id=4,
            created_at="2022-11-17 11:17:00",
            updated_at="2022-11-17 11:17:00",
            name="sub4",
            description="Job Submission 4",
            owner_email="felipe@omnivector.solutions",
            job_script_id=99,
            slurm_job_id=9999,
            status="REJECTED",
            report_message="Failed to submit job to slurm",
            execution_parameters={
                "name": "job-submission-name-4",
                "comment": "I am a comment",
            },
        ),
    ]


@pytest.fixture(scope="module")
def dummy_config_source():
    return dedent(
        """
        jobbergate_config:
          default_template: test-job-script.py.j2
          template_files:
            - test-job-script.py.j2
          output_directory: .
          supporting_files_output_name:
          supporting_files:
          user_supplied_key: user-supplied-value
        application_config:
          foo: foo
          bar: bar
          baz: baz
        """
    )


@pytest.fixture(scope="module")
def dummy_module_source():
    return dedent(
        """
        from jobbergate_cli.subapps.applications.application_base import JobbergateApplicationBase
        from jobbergate_cli.subapps.applications.questions import Text


        class JobbergateApplication(JobbergateApplicationBase):

            def mainflow(self, data):
                data["nextworkflow"] = "subflow"
                return [Text("foo", message="gimme the foo!"), Text("bar", message="gimme the bar!")]

            def subflow(self, data):
                return [Text("baz", message="gimme the baz!", default="zab")]
        """
    )


@pytest.fixture(scope="module")
def dummy_template_source():
    return dedent(
        """
        #!/bin/python3

        #SBATCH -J dummy_job
        #SBATCH -t 60
        print("I am a very, very dumb job script")
        print(f"foo='{{foo}}'")
        print(f"bar='{{bar}}'")
        print(f"baz='{{baz}}'")
        """
    )


@pytest.fixture
def dummy_jobbergate_application_config(dummy_config_source):
    return JobbergateApplicationConfig(**yaml.safe_load(dummy_config_source))


@pytest.fixture
def dummy_jobbergate_application_module(dummy_module_source, dummy_jobbergate_application_config):
    return load_application_from_source(dummy_module_source, dummy_jobbergate_application_config)


@pytest.fixture
def dummy_application_dir(tmp_path, dummy_config_source, dummy_module_source, dummy_template_source):
    application_path = tmp_path / "dummy"
    application_path.mkdir()

    module_path = application_path / JOBBERGATE_APPLICATION_MODULE_FILE_NAME
    module_path.write_text(dummy_module_source)

    config_path = application_path / JOBBERGATE_APPLICATION_CONFIG_FILE_NAME
    config_path.write_text(dummy_config_source)

    template_root_path = application_path / "templates"
    template_root_path.mkdir()

    template_path = template_root_path / "job-script-template.py.j2"
    template_path.write_text(dummy_template_source)

    ignored_path = application_path / "ignored"
    ignored_path.mkdir()

    ignored_file = ignored_path / "ignored.txt"
    ignored_file.write_text("This file should be ignored")

    return application_path


@pytest.fixture
def dummy_render_class():
    class DummyRender:
        prepared_input: Dict[str, Any]

        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def render(self, question, answers=None):
            question.answers = answers if answers is not None else dict()

            try:
                ignore = question.ignore(answers)
            except TypeError:
                ignore = question.ignore

            if ignore:
                return question.default

            value = self.prepared_input[question.name]
            question.validate(value)
            return value

    return DummyRender


@pytest.fixture
def dummy_one_page_results():
    return {
        "items": [{"id": 1, "name": "Item 1"}],
        "total": 1,
        "page": 1,
        "size": 50,
        "pages": 1,
    }


@pytest.fixture
def dummy_two_pages_results():
    return [
        {
            "items": [{"id": i + 1, "name": f"Item {i + 1}"} for i in range(50)],
            "total": 80,
            "page": 1,
            "size": 50,
            "pages": 2,
        },
        {
            "items": [{"id": i + 1, "name": f"Item {i + 1}"} for i in range(30)],
            "total": 30,
            "page": 2,
            "size": 50,
            "pages": 2,
        },
    ]
