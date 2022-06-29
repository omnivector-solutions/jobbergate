"""
Email notification system for Jobbergate.
"""
from dataclasses import dataclass
from typing import List, Union

from buzz import Buzz
from loguru import logger
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from jobbergate_api.config import settings


class EmailNotificationError(Buzz):
    pass


@dataclass
class EmailManager:

    email_client: SendGridAPIClient
    from_email: str

    async def send_email(self, to_emails: str, subject: str, html_content: str, **kwargs) -> None:

        EmailNotificationError.require_condition(self.from_email, "The value from_email is empty.")

        with EmailNotificationError.handle_errors("Error while creating the message"):
            message = Mail(
                from_email=self.from_email,
                to_emails=to_emails,
                subject=subject,
                html_content=html_content,
                **kwargs,
            )

        with EmailNotificationError.handle_errors("Error while sending email"):
            response = await self.email_client.send(message)
        logger.trace(f"Response status code after sending the email: {response.status_code}")


def notify_submission_aborted(
    job_submission_id: Union[str, int], report_message: str, to_emails: Union[str, List[str]]
) -> None:
    subject = f"Job Submission Aborted (id={job_submission_id})"
    html_content = f"<strong>{report_message}</strong>"

    logger.debug(f"Notifying {to_emails=} that {job_submission_id=} was aborted: {report_message=}")
    try:
        email_manager.send_email(to_emails, subject, html_content)
    except EmailNotificationError:
        logger.debug("Email not sent!")


email_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
email_manager = EmailManager(
    email_client,
    settings.SENDGRID_FROM_EMAIL,
)
