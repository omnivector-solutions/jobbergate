from functools import cached_property
from typing import Type

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from jobbergate_core.sdk.job_scripts.app import JobScripts
from jobbergate_core.sdk.job_templates.app import JobTemplates
from jobbergate_core.tools.requests import Client, RequestHandler


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class Apps:
    client: Client
    request_handler_cls: Type[RequestHandler] = RequestHandler

    @cached_property
    def job_templates(self) -> "JobTemplates":
        return JobTemplates(self.client, self.request_handler_cls)

    @cached_property
    def job_scripts(self) -> "JobScripts":
        return JobScripts(self.client, self.request_handler_cls)
