"""
Test job-script files.
"""

from pathlib import Path
from textwrap import dedent

import pytest

from jobbergate_api.apps.applications.application_files import ApplicationFiles
from jobbergate_api.apps.job_scripts.job_script_files import (
    JOBSCRIPTS_MAIN_FILE_FOLDER,
    JOBSCRIPTS_SUPPORTING_FILES_FOLDER,
    JOBSCRIPTS_WORK_DIR,
    JobScriptFiles,
    inject_sbatch_params,
)


@pytest.fixture
def job_script_data_as_string():
    """
    Provide a fixture that returns an example of a default application script.
    """
    content = dedent(
        """
        #!/bin/bash

        #SBATCH --job-name=rats
        #SBATCH --partition=debug
        #SBATCH --output=sample-%j.out


        echo $SLURM_TASKS_PER_NODE
        echo $SLURM_SUBMIT_DIR
        """
    ).strip()
    return content


@pytest.fixture
def new_job_script_data_as_string():
    """
    Provide a fixture that returns an application script after the injection of the sbatch params.
    """
    content = dedent(
        """
        #!/bin/bash

        #SBATCH --job-name=rats
        #SBATCH --comment=some_comment
        #SBATCH --nice=-1
        #SBATCH -N 10
        #SBATCH --partition=debug
        #SBATCH --output=sample-%j.out


        echo $SLURM_TASKS_PER_NODE
        echo $SLURM_SUBMIT_DIR
        """
    ).strip()
    return content


@pytest.fixture
def sbatch_params():
    """
    Provide a fixture that returns string content of the argument --sbatch-params.
    """
    return ["--comment=some_comment", "--nice=-1", "-N 10"]


def test_inject_sbatch_params(job_script_data_as_string, sbatch_params, new_job_script_data_as_string):
    """
    Test the injection of sbatch params in a default application script.
    """
    injected_string = inject_sbatch_params(job_script_data_as_string, sbatch_params)
    assert injected_string == new_job_script_data_as_string


@pytest.fixture
def dummy_application_files(
    dummy_application_source_file,
    dummy_application_config,
    dummy_template,
):
    """
    Test fixture with dummy application files.
    """
    return ApplicationFiles(
        templates={"test_job_script.sh": dummy_template},
        source_file=dummy_application_source_file,
        config_file=dummy_application_config,
    )


class TestJobScriptFiles:
    """
    Test JobScriptFiles.
    """

    def test_check_main_file_path_is_in_files_keys__success(self):
        """
        Test a case were JobScriptFiles is created with success.
        """
        jobscript_files = JobScriptFiles(
            main_file_path="jobbergate.sh", files={"jobbergate.sh": "dummy-file-content"}
        )

        assert isinstance(jobscript_files, JobScriptFiles)

    def test_check_main_file_path_is_in_files_keys__error_main_file_path(self):
        """
        Test that ValueError is raised when the main file is not included in the files.
        """
        with pytest.raises(ValueError):
            JobScriptFiles(
                main_file_path="wrong-filename",
                files={"jobbergate.sh": "dummy-file-content"},
            )

    def test_get_from_s3(self, mocked_file_manager_factory):
        """
        Test that JobScriptFiles can be obtained from the file manager.
        """
        job_script_id = 1

        work_dir = mocked_file_manager_factory / JOBSCRIPTS_WORK_DIR / str(job_script_id)
        output_dir = Path("test-output-dir")

        main_file_name = output_dir / "jobbergate.sh"
        main_file_content = "test-main-file"
        main_file_path = work_dir / JOBSCRIPTS_MAIN_FILE_FOLDER / main_file_name
        main_file_path.parent.mkdir(parents=True, exist_ok=True)
        main_file_path.write_text(main_file_content)

        supporting_file_name = output_dir / "support.sh"
        supporting_file_content = "test-support-file"
        supporting_file_path = work_dir / JOBSCRIPTS_SUPPORTING_FILES_FOLDER / supporting_file_name
        supporting_file_path.parent.mkdir(parents=True, exist_ok=True)
        supporting_file_path.write_text(supporting_file_content)

        desired_jobscript_files = JobScriptFiles(
            main_file_path=main_file_name,
            files={
                main_file_name: main_file_content,
                supporting_file_name: supporting_file_content,
            },
        )

        actual_jobscript_files = JobScriptFiles.get_from_s3(job_script_id)

        assert desired_jobscript_files == actual_jobscript_files

    def test_get_from_s3__no_main_file(self, mocked_file_manager_factory):
        """
        Test that ValueError is raised when no main file is found.
        """
        job_script_id = 1
        with pytest.raises(
            ValueError,
            match="One and only one main file is expected for a job-script, found 0",
        ):
            JobScriptFiles.get_from_s3(job_script_id)

    def test_delete_from_s3(self, mocked_file_manager_factory):
        """
        Test that JobScriptFiles are deleted as expected.
        """
        job_script_id = 1

        work_dir = mocked_file_manager_factory / JOBSCRIPTS_WORK_DIR / str(job_script_id)
        output_dir = Path("test-output-dir")

        main_file_name = output_dir / "jobbergate.sh"
        main_file_content = "test-main-file"
        main_file_path = work_dir / JOBSCRIPTS_MAIN_FILE_FOLDER / main_file_name
        main_file_path.parent.mkdir(parents=True, exist_ok=True)
        main_file_path.write_text(main_file_content)

        supporting_file_name = output_dir / "support.sh"
        supporting_file_content = "test-support-file"
        supporting_file_path = work_dir / JOBSCRIPTS_SUPPORTING_FILES_FOLDER / supporting_file_name
        supporting_file_path.parent.mkdir(parents=True, exist_ok=True)
        supporting_file_path.write_text(supporting_file_content)

        assert main_file_path.is_file()
        assert supporting_file_path.is_file()

        JobScriptFiles.delete_from_s3(job_script_id)

        assert not main_file_path.is_file()
        assert not supporting_file_path.is_file()

    def test_write_to_s3(self, mocked_file_manager_factory):
        """
        Test that JobScriptFiles are written as expected.
        """
        job_script_id = 1

        work_dir = mocked_file_manager_factory / JOBSCRIPTS_WORK_DIR / str(job_script_id)
        output_dir = Path("test-output-dir")

        main_file_name = output_dir / "jobbergate.sh"
        main_file_content = "test-main-file"
        main_file_path = work_dir / JOBSCRIPTS_MAIN_FILE_FOLDER / main_file_name

        supporting_file_name = output_dir / "support.sh"
        supporting_file_content = "test-support-file"
        supporting_file_path = work_dir / JOBSCRIPTS_SUPPORTING_FILES_FOLDER / supporting_file_name

        JobScriptFiles(
            main_file_path=main_file_name,
            files={
                main_file_name: main_file_content,
                supporting_file_name: supporting_file_content,
            },
        ).write_to_s3(job_script_id)

        assert main_file_path.is_file()
        assert main_file_path.read_text() == main_file_content

        assert supporting_file_path.is_file()
        assert supporting_file_path.read_text() == supporting_file_content

    def test_io_integration_with_s3(self, mocked_file_manager_factory):
        """
        End-to-end test where the JobScriptFiles are written and read from s3.
        """
        job_script_id = 1
        output_dir = Path("test-output-dir")

        main_file_name = output_dir / "jobbergate.sh"
        main_file_content = "test-main-file"

        supporting_file_name = output_dir / "support.sh"
        supporting_file_content = "test-support-file"

        actual_jobscript_files = JobScriptFiles(
            main_file_path=main_file_name,
            files={
                main_file_name: main_file_content,
                supporting_file_name: supporting_file_content,
            },
        )

        actual_jobscript_files.write_to_s3(job_script_id)

        desired_jobscript_files = JobScriptFiles.get_from_s3(job_script_id)

        assert desired_jobscript_files == actual_jobscript_files

        JobScriptFiles.delete_from_s3(job_script_id)

        with pytest.raises(
            ValueError,
            match="One and only one main file is expected for a job-script, found 0",
        ):
            JobScriptFiles.get_from_s3(job_script_id)

    def test_render_from_application__success(
        self,
        param_dict,
        job_script_data_as_string,
        dummy_application_files,
    ):
        """
        Test that JobScriptFiles can be obtained when rendering ApplicationFiles.
        """
        desired_job_script_files = JobScriptFiles(
            main_file_path="test_job_script.sh",
            files={
                "test_job_script.sh": job_script_data_as_string,
                "support_file_b.py": job_script_data_as_string,
            },
        )

        actual_job_script_files = JobScriptFiles.render_from_application(
            dummy_application_files,
            param_dict,
        )

        assert actual_job_script_files == desired_job_script_files

    def test_render_from_application__ignores_template_path_prefix_in_default_template_file(
        self,
        param_dict,
        job_script_data_as_string,
        dummy_application_files,
    ):
        """
        Test that JobScriptFiles can be obtained when rendering ApplicationFiles.
        """
        mangled_param_dict = param_dict.copy()
        mangled_param_dict["jobbergate_config"]["default_template"] = "templates/test_job_script.sh"

        desired_job_script_files = JobScriptFiles(
            main_file_path="test_job_script.sh",
            files={
                "test_job_script.sh": job_script_data_as_string,
                "support_file_b.py": job_script_data_as_string,
            },
        )

        actual_job_script_files = JobScriptFiles.render_from_application(
            dummy_application_files,
            mangled_param_dict,
        )

        assert actual_job_script_files == desired_job_script_files
