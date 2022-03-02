import pytest


@pytest.fixture
def dummy_data():
    return [
        dict(
            id=1,
            application_name="test-app-1",
            application_identifier="test-app-1",
            application_description="Test Application Number 1",
            application_owner_email="tucker.beck@omnivector.com",
            application_file="print('test1')",
            application_config="config1",
            application_uploaded=True,
            created_at="2022-03-01 17:31:00",
            updated_at="2022-03-01 17:31:00",
        ),
        dict(
            id=2,
            application_name="test-app-2",
            application_identifier="test-app-2",
            application_description="Test Application Number 2",
            application_owner_email="tucker.beck@omnivector.com",
            application_file="print('test2')",
            application_config="config2",
            application_uploaded=True,
            created_at="2022-03-01 17:31:00",
            updated_at="2022-03-01 17:31:00",
        ),
        dict(
            id=3,
            application_name="test-app-3",
            application_identifier="test-app-3",
            application_description="Test Application Number 3",
            application_owner_email="tucker.beck@omnivector.com",
            application_file="print('test3')",
            application_config="config3",
            application_uploaded=True,
            created_at="2022-03-01 17:31:00",
            updated_at="2022-03-01 17:31:00",
        ),
    ]
