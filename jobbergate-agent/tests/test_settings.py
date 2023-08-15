from jobbergate_agent.settings import Settings


class TestSettingsSlurmrestdUrl:
    def test_default_version_is_added_for_backward_compatibility(self):
        """
        Test that the default version is added to the url if it is not present.
        """
        url = "http://localhost:6820"
        settings = Settings(BASE_SLURMRESTD_URL=url)
        assert settings.SLURM_RESTD_VERSIONED_URL == f"{url}/slurm/v0.0.36"

    def test_default_version_is_not_added_if_already_present(self):
        """
        Test that the default version is not added to the url if it is already present.
        """
        url = "http://localhost:6820/slurm/v0.0.39"
        settings = Settings(SLURM_RESTD_VERSIONED_URL=url)
        assert settings.SLURM_RESTD_VERSIONED_URL == url
