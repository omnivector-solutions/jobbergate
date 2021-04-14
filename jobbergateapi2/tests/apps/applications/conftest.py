from pytest import fixture


@fixture
def application_data():
    """
    Default appliation data for testing
    """
    return {
        "application_name": "test_name",
        "application_file": "the\nfile",
        "application_config": "the configuration is here",
    }
