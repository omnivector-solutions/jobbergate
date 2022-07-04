"""
Email notification system for Jobbergate.
"""
from dataclasses import dataclass
from typing import List, Optional, Union

from buzz import Buzz
from loguru import logger
from sendgrid import SendGridAPIClient  # type: ignore # no type hints or library stubs
from sendgrid.helpers.mail import Mail  # type: ignore # no type hints or library stubs

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

    def send_email(self, to_emails: Union[str, List[str]], subject: str, **kwargs) -> None:
        """
        Send an email using this manager.
        """
        message = self._build_message(to_emails, subject, **kwargs)

        with EmailNotificationError.handle_errors("Error while sending email"):
            self.email_client.send(message)

    def _build_message(self, to_emails: Union[str, List[str]], subject: str, **kwargs) -> Mail:
        """
        Build an email message.
        """
        EmailNotificationError.require_condition(self.from_email, "The value from_email is empty.")

        with EmailNotificationError.handle_errors("Error while creating the message"):
            message = Mail(
                from_email=self.from_email,
                to_emails=to_emails,
                subject=subject,
                **kwargs,
            )
        return message


def notify_submission_aborted(
    job_submission_id: Union[str, int], report_message: str, to_emails: Union[str, List[str]]
) -> None:
    """
    Notify an email or a list of emails about a job submission that has been aborted.
    """
    subject = f"Job Submission Aborted (id={job_submission_id})"

    logger.debug(f"Notifying {to_emails=} that {job_submission_id=} was aborted: {report_message=}")
    try:
        email_manager.send_email(to_emails, subject, plain_text_content=report_message)
    except EmailNotificationError:
        logger.warning(f"Couldn't sent email to {to_emails}")


email_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
email_manager = EmailManager(
    email_client,
    settings.SENDGRID_FROM_EMAIL,
)
