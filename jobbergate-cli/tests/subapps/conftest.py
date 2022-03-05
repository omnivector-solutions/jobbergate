import typing

import httpx
import pytest
import snick
from typer import Typer, Context
from typer.testing import CliRunner


from jobbergate_cli.schemas import JobbergateContext
from jobbergate_cli.constants import (
    JOBBERGATE_APPLICATION_MODULE_FILE_NAME,
    JOBBERGATE_APPLICATION_CONFIG_FILE_NAME,
)


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

    def _helper(command_name: str, command_function: typing.Callable):
        main_app = Typer()
        main_app.callback()(_main_callback)
        main_app.command(name=command_name)(command_function)
        return main_app

    return _helper



@pytest.fixture
def dummy_context(dummy_domain):
    return JobbergateContext(
        persona=None,
        client=httpx.Client(
            base_url=dummy_domain,
            headers={"Authorization": "Bearer XXXXXXXX"}
        ),
    )


@pytest.fixture
def dummy_application_data():
    return [
        dict(
            id=1,
            application_name="test-app-1",
            application_identifier="test-app-1",
            application_description="Test Application Number 1",
            application_owner_email="tucker.beck@omnivector.com",
            application_file="print('test1')",
            application_config="config1",
            application_uploaded=True,
            created_at="2022-03-01 17:31:00",
            updated_at="2022-03-01 17:31:00",
        ),
        dict(
            id=2,
            application_name="test-app-2",
            application_identifier="test-app-2",
            application_description="Test Application Number 2",
            application_owner_email="tucker.beck@omnivector.com",
            application_file="print('test2')",
            application_config="config2",
            application_uploaded=True,
            created_at="2022-03-01 17:31:00",
            updated_at="2022-03-01 17:31:00",
        ),
        dict(
            id=3,
            application_name="test-app-3",
            application_identifier="test-app-3",
            application_description="Test Application Number 3",
            application_owner_email="tucker.beck@omnivector.com",
            application_file="print('test3')",
            application_config="config3",
            application_uploaded=True,
            created_at="2022-03-01 17:31:00",
            updated_at="2022-03-01 17:31:00",
        ),
    ]


@pytest.fixture
def dummy_job_script_data():
    return [
        dict(
          id=1,
          created_at="2022-03-02 22:08:00",
          updated_at="2022-03-02 22:08:00",
          job_script_name="script1",
          job_script_description="Job Script 1",
          job_script_data_as_string="{\"application.sh\": \"#!/bin/python3\\n# from conf: test\\n# cluster: Nash\\n# stageup: False\\n\\necho {'blank': '', 'default_template': 'template.j2', 'preexisting': 'test', 'template_files': ['templates/template.j2'], 'cluster': 'Nash', 'simsteps': '100', 'stageup': False}\"}",
          job_script_owner_email="tucker@omnivector.com",
          application_id=1
        ),
        dict(
          id=2,
          created_at="2022-03-02 22:08:00",
          updated_at="2022-03-02 22:08:00",
          job_script_name="script2",
          job_script_description="Job Script 2",
          job_script_data_as_string="{}",
          job_script_owner_email="tucker@omnivector.com",
          application_id=1
        ),
        dict(
          id=3,
          created_at="2022-03-02 22:08:00",
          updated_at="2022-03-02 22:08:00",
          job_script_name="script3",
          job_script_description="Job Script 3",
          job_script_data_as_string="{}",
          job_script_owner_email="james@omnivector.com",
          application_id=1
        ),
    ]


@pytest.fixture(scope="module")
def dummy_config_source():
    return snick.dedent(
        """
        jobbergate_config:
          default_template: test-job-script.py.j2
          output_directory: .
        application_config:
          partition: debug
        """
    )


@pytest.fixture(scope="module")
def dummy_module_source():
    return snick.dedent(
        """
        from jobbergate_cli.application_base import JobbergateApplicationBase
        from jobbergate_cli import appform

        class JobbergateApplication(JobbergateApplicationBase):
            def mainflow(self, data):
                questions = []

                questions.append(appform.Text(
                    "partition",
                    message="Choose a partition",
                    default="compute"
                ))
                return questions
        """
    )


@pytest.fixture(scope="module")
def dummy_template_source():
    return snick.dedent(
        """
        #!/bin/python3

        # Select Partition, Cores, Jobname, Hardware
        #SBATCH --partition {{data.partition}}
        #SBATCH -J 00_smallcase

        # Time limit
        #SBATCH -t 60  # TODO no soft limit in SLURM, check if users want hard limit instead

        import os
        import subprocess


        def parse_slurm_nodes(hostlist):
            ''' Takes a contracted hostlist and returns an expanded one.
                e.g.: "node[1,3-4]" -> "node1,node3,node4"
            '''
            cmd_args = ['scontrol', 'show', 'hostnames', hostlist]
            try:
                cmd_results = subprocess.run(cmd_args, stdout=subprocess.PIPE)
                # Skip last line (empty), strip quotation marks
                expanded_hostlist = cmd_results.stdout.decode().split("\n")[:-1]
            except BaseException:
                print("Could not retrieve queue information from SLURM.")
                return ""

            return ",".join(expanded_hostlist)

        hoststring = os.getenv('SLURM_JOB_NODELIST')
        hostlist = parse_slurm_nodes(hoststring)
        print(f"hosts: {hoststring} ({hostlist})", flush=True)
        """
    )


@pytest.fixture
def dummy_application(tmp_path, dummy_config_source, dummy_module_source, dummy_template_source):
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
        prepared_input: typing.Dict[str, typing.Any]

        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def render(self, question, *_):
            if question.ignore:
                return question.default
            value = self.prepared_input[question.name]
            question.validate(value)
            return value

    return DummyRender
