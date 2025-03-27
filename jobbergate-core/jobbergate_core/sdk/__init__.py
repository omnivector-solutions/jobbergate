from functools import cached_property
from typing import Type

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from jobbergate_core.sdk.clusters import ClusterStatus
from jobbergate_core.sdk.job_scripts import JobScripts
from jobbergate_core.sdk.job_submissions import JobSubmissions
from jobbergate_core.sdk.job_templates import JobTemplates
from jobbergate_core.tools.requests import Client, RequestHandler


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class Apps:
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
