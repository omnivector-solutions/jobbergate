from jobbergate_core.sdk import Apps
from jobbergate_core.sdk.clusters import ClusterStatus
from jobbergate_core.sdk.job_templates import JobTemplates
from jobbergate_core.sdk.job_submissions import JobSubmissions
from jobbergate_core.sdk.job_scripts import JobScripts
from jobbergate_core.tools.requests import Client

BASE_URL = "https://testserver"


def client_factory() -> Client:
    """Factory to create a Client instance."""
    return Client(base_url=BASE_URL)


class TestApps:
    client = client_factory()
    apps = Apps(client)

    def test_cluster_status(self):
        assert isinstance(self.apps.clusters, ClusterStatus)
        assert self.apps.job_templates.client == self.apps.client
        assert self.apps.job_templates.request_handler_cls == self.apps.request_handler_cls

    def test_job_templates(self):
        assert isinstance(self.apps.job_templates, JobTemplates)
        assert self.apps.job_templates.client == self.apps.client
        assert self.apps.job_templates.request_handler_cls == self.apps.request_handler_cls

    def test_job_scripts(self):
        assert isinstance(self.apps.job_scripts, JobScripts)
        assert self.apps.job_scripts.client == self.apps.client
        assert self.apps.job_scripts.request_handler_cls == self.apps.request_handler_cls

    def test_job_submissions(self):
        assert isinstance(self.apps.job_submissions, JobSubmissions)
        assert self.apps.job_submissions.client == self.apps.client
        assert self.apps.job_submissions.request_handler_cls == self.apps.request_handler_cls
