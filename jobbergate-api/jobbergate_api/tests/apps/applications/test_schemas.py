"""
Test schemas for Jobbergate applications.
"""

from jobbergate_api.apps.applications.schemas import JobbergateConfig


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
