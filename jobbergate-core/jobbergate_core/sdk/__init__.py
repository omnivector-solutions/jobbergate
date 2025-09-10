from functools import cached_property
from pathlib import Path
from typing import Type

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from jobbergate_core.auth.handler import JobbergateAuthHandler
from jobbergate_core.sdk.clusters import ClusterStatus
from jobbergate_core.sdk.job_scripts import JobScripts
from jobbergate_core.sdk.job_submissions import JobSubmissions
from jobbergate_core.sdk.job_templates import JobTemplates
from jobbergate_core.tools.requests import Client, RequestHandler


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class Apps:
    """
    Main class for Jobbergate SDK applications.

    Arguments:
        client: An instance of Client to handle API requests.
        request_handler_cls: A class that handles requests, defaults to RequestHandler.
    """

    client: Client
    request_handler_cls: Type[RequestHandler] = RequestHandler

    @cached_property
    def clusters(self) -> "ClusterStatus":
        return ClusterStatus(self.client, self.request_handler_cls)

    @cached_property
    def job_templates(self) -> "JobTemplates":
        return JobTemplates(self.client, self.request_handler_cls)

    @cached_property
    def job_scripts(self) -> "JobScripts":
        return JobScripts(self.client, self.request_handler_cls)

    @cached_property
    def job_submissions(self) -> "JobSubmissions":
        return JobSubmissions(self.client, self.request_handler_cls)

    @classmethod
    def build(
        cls,
        base_url: str = "https://apis.vantagecompute.ai",
        login_url: str = "https://auth.vantagecompute.ai/realms/vantage",
        token_dir: Path = Path("~/.local/share/jobbergate3/token"),
        client_kwargs: dict | None = None,
        auth_kwargs: dict | None = None,
    ) -> "Apps":
        """Alternative build method to set client and auth parameters."""
        if client_kwargs is None:
            client_kwargs = {}
        if auth_kwargs is None:
            auth_kwargs = {}
        return cls(
            client=Client(
                base_url=base_url,
                auth=JobbergateAuthHandler(login_domain=login_url, cache_directory=token_dir, **auth_kwargs),
                **client_kwargs,
            )
        )
