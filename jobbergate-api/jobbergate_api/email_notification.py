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
from jobbergate_api.retry_utils import sync_retry


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
        self,
        to_emails: Union[str, List[str]],
        subject: str,
        skip_on_failure: bool = False,
        enable_retry: bool = False,
        **kwargs,
    ) -> bool:
        """
        Send an email using this manager.

        Args:
            to_emails: Email or list of emails to send to
            subject: Email subject
            skip_on_failure: If True, log errors instead of raising exceptions
            enable_retry: If True, attempt delivery with retry logic (3 attempts, exponential backoff)
            **kwargs: Additional arguments for Mail construction

        Returns:
            True if email was sent successfully, False if skipped on failure
        """

        def _send() -> None:
            with EmailNotificationError.handle_errors(
                f"Error while sending email from_email={self.from_email}, {to_emails=}",
                do_except=lambda params: logger.warning(params.final_message),
                re_raise=not skip_on_failure,
            ):
                message = self._build_message(to_emails, subject, **kwargs)
                self.email_client.send(message)

        if enable_retry:
            def on_retry_error(exc: Exception, attempt: int) -> None:
                logger.warning(f"Failed to send email (attempt {attempt}): {exc}")

            result = sync_retry(
                _send,
                max_attempts=3,
                initial_delay=1.0,
                backoff_factor=2.0,
                on_error=on_retry_error,
            )
            if result is None:
                logger.error("Failed to send email after 3 retry attempts")
                return False
        else:
            try:
                _send()
            except EmailNotificationError:
                if skip_on_failure:
                    return False
                raise
        return True

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
