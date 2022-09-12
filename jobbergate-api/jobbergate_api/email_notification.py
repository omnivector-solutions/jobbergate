"""
Email notification system for Jobbergate.
"""
from dataclasses import dataclass
from typing import List, Optional, Union

from buzz import Buzz
from loguru import logger
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from jobbergate_api.config import settings


class EmailNotificationError(Buzz):
    """
    Custom error to be raised for problems at the email notification system.
    """

    pass


@dataclass
class EmailManager:
    """
    Email manager.
    """

    email_client: SendGridAPIClient
    from_email: Optional[str] = ""

    def send_email(
        self, to_emails: Union[str, List[str]], subject: str, skip_on_failure: bool = False, **kwargs
    ) -> None:
        """
        Send an email using this manager.
        """
        with EmailNotificationError.handle_errors(
            f"Error while sending email from_email={self.from_email}, {to_emails=}",
            do_except=lambda params: logger.warning(params.final_message),
            re_raise=not skip_on_failure,
        ):
            message = self._build_message(to_emails, subject, **kwargs)
            self.email_client.send(message)

    def _build_message(self, to_emails: Union[str, List[str]], subject: str, **kwargs) -> Mail:
        """
        Build an email message.
        """
        EmailNotificationError.require_condition(self.from_email, "The value from_email is empty.")

        with EmailNotificationError.handle_errors(
            "Error while creating the message",
            do_except=lambda params: logger.error(params.final_message),
        ):
            message = Mail(
                from_email=self.from_email,
                to_emails=to_emails,
                subject=subject,
                **kwargs,
            )
        return message


def notify_submission_rejected(
    job_submission_id: Union[str, int], report_message: str, to_emails: Union[str, List[str]]
) -> None:
    """
    Notify an email or a list of emails about a job submission that has been rejected.
    """
    subject = f"Job Submission Rejected (id={job_submission_id})"

    logger.debug(f"Notifying {to_emails=} that {job_submission_id=} was rejected: {report_message=}")
    email_manager.send_email(to_emails, subject, skip_on_failure=True, plain_text_content=report_message)


email_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
email_manager = EmailManager(
    email_client,
    settings.SENDGRID_FROM_EMAIL,
)
