from unittest import mock

import pytest
from sendgrid import SendGridAPIClient

from jobbergate_api.email_notification import EmailManager

EmailManager


class TestEmailManager:
    @pytest.fixture(scope="class")
    def mocked_email_client(self):
        return SendGridAPIClient()

    def test_send_email__success(self):
        pass
