"""
Test the email notification system at Jobbergate.
"""
from unittest import mock

import pytest
from fastapi import HTTPException
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from jobbergate_api.email_notification import EmailManager, EmailNotificationError, notify_submission_rejected


class TestEmailManager:
    """
    A suite of tests for the email manager.
    """

    @pytest.fixture(scope="class")
    def email_client(self):
        """
        Build a dummy email client for tests.
        """
        return SendGridAPIClient("dummy-api-key")

    @pytest.fixture(scope="class")
    def email_manager(self, email_client):
        """
        Build a dummy email manager for tests.
        """
        return EmailManager(email_client, "me@pytesting.com")

    @pytest.fixture(scope="class")
    def email_options(self):
        """
        Return a dictionary with the parameters used to send an email using the manager.
        """
        return dict(
            to_emails="you@pytesting.com",
            subject="TEST",
            plain_text_content="The content!",
        )

    def test_build_message__success(self, email_manager, email_options):
        """
        Test that a message was usefully built and returned using the provided parameters.
        """
        message = email_manager._build_message(**email_options)
        assert isinstance(message, Mail)

    def test_build_message__error_when_from_email_is_empty(self, email_client, email_options):
        """
        Test if build_message raises EmailNotificationError when the parameter from_email is empty.
        """
        email_manager = EmailManager(email_client, "")
        with pytest.raises(EmailNotificationError, match="The value from_email is empty"):
            email_manager._build_message(**email_options)

    def test_build_message__error_at_mail_arguments(self, email_manager, email_options):
        """
        Test if build_message raises EmailNotificationError.

        In this case, when some invalid parameters are provided to the Mail constructor.
        """
        dummy_options = dict(**email_options, foo="foo", bar="bar")
        with pytest.raises(EmailNotificationError, match="Error while creating the message"):
            email_manager._build_message(**dummy_options)

    def test_send_email__success(self, email_manager, email_options):
        """
        Test that the email manager can send an email successfully using the SendGrid API.
        """
        with mock.patch.object(email_manager.email_client, "send") as mocked:
            email_manager.send_email(**email_options)
        mocked.assert_called_once()

    def test_send_email__fail(self, email_manager, email_options):
        """
        Test if the email manager raises EmailNotificationError.

        In this case, when it can not connect to the SendGrid API.
        """
        with pytest.raises(EmailNotificationError, match="Error while sending email"):
            with mock.patch.object(
                email_manager.email_client,
                "send",
                side_effect=HTTPException(status_code=401, detail="Unauthorized"),
            ) as mocked:
                email_manager.send_email(**email_options)
        mocked.assert_called_once()

    def test_send_email__skip_on_failure(self, email_manager, email_options):
        """
        Test if the email manager can skip on failure when it can not connect to the SendGrid API.
        """
        with mock.patch.object(
            email_manager.email_client,
            "send",
            side_effect=HTTPException(status_code=401, detail="Unauthorized"),
        ) as mocked:
            email_manager.send_email(skip_on_failure=True, **email_options)
        mocked.assert_called_once()


def test_notify_submission_rejected():
    """
    Test if an email is sent to inform that a job submission has been rejected.
    """
    with mock.patch("jobbergate_api.email_notification.email_manager.email_client.send") as mocked:
        notify_submission_rejected(
            job_submission_id=0,
            report_message="something went wrong!",
            to_emails=["support@pytesting.com", "someone@pytesting.com"],
        )
    mocked.assert_called_once()
