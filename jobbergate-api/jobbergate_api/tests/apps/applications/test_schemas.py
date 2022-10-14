"""
Test schemas for Jobbergate applications.
"""

from textwrap import dedent

import pytest

from jobbergate_api.apps.applications.schemas import ApplicationConfig, JobbergateConfig


@pytest.fixture
def reference_application_config() -> str:
    """
    Fixture to return a complete application config file.
    """
    return dedent(
        """
        application_config:
            job_name: rats
            partitions:
                - debug
                - partition1
        jobbergate_config:
            default_template: test_job_script.sh
            output_directory: .
            supporting_files:
                - test_job_script.sh
                - test_another_job_script.sh
            supporting_files_output_name:
                test_job_script.sh:
                    - support_file_b.py
                test_another_job_script.sh:
                    - support_file_c.py
            template_files:
                - templates/test_job_script.sh
        """
    ).strip()


@pytest.fixture
def dummy_application_config() -> str:
    """
    Fixture to return a dummy application config file.

    Due to the business logic, this file should be parsed to an object
    to the config file above (reference_application_config).
    """
    return dedent(
        """
        application_config:
            job_name: rats
            partitions:
                - debug
                - partition1
        jobbergate_config:
            default_template: test_job_script.sh
            output_directory: .
            supporting_files_output_name:
                test_job_script.sh:
                    - support_file_b.py
                test_another_job_script.sh: support_file_c.py
            template_files:
                - templates/test_job_script.sh
        """
    ).strip()


class TestJobbergateConfig:
    """
    Test jobbergate configuration.
    """

    def test_get_supporting_files_from_supporting_files_output_name__success(self):
        """
        Test that supporting_files is obtained from the keys of supporting_files_output_name.
        """
        config = JobbergateConfig(supporting_files_output_name=dict(foo="string", bar="string"))

        assert config.supporting_files == ["foo", "bar"]

    def test_get_supporting_files_from_supporting_files_output_name__no_replacement(self):
        """
        Test that supporting_files is not overwritten when provided initially.
        """
        config = JobbergateConfig(
            supporting_files_output_name=dict(foo="string", bar="string"), supporting_files=["baz"]
        )

        assert config.supporting_files == ["baz"]

    def test_get_supporting_files_from_supporting_files_output_name__missing_value(self):
        """
        Test that supporting_files is still None if supporting_files_output_name is not provided.
        """
        config = JobbergateConfig()

        assert config.supporting_files is None

    def test_supporting_files_output_name_provided_as_string(self):
        """
        Test that string values at supporting_files_output_name are converted to lists of strings.
        """
        config = JobbergateConfig(supporting_files_output_name=dict(foo="bar", baz=["qux"]))

        assert config.supporting_files_output_name == dict(foo=["bar"], baz=["qux"])


def test_application_config(reference_application_config, dummy_application_config):
    """
    Test that the business logic to fill missing values in the application config is working.
    """
    desired_config = ApplicationConfig.get_from_yaml_file(reference_application_config)
    actual_config = ApplicationConfig.get_from_yaml_file(dummy_application_config)

    assert actual_config == desired_config
