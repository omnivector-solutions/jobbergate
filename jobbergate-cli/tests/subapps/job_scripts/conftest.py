import pytest


@pytest.fixture
def dummy_data():
    return [
        dict(
          id=1,
          created_at="2022-03-02 22:08:00",
          updated_at="2022-03-02 22:08:00",
          job_script_name="script1",
          job_script_description="Job Script 1",
          job_script_data_as_string="{\"application.sh\": \"#!/bin/python3\\n# from conf: test\\n# cluster: Nash\\n# stageup: False\\n\\necho {'blank': '', 'default_template': 'template.j2', 'preexisting': 'test', 'template_files': ['templates/template.j2'], 'cluster': 'Nash', 'simsteps': '100', 'stageup': False}\"}",
          job_script_owner_email="tucker@omnivector.com",
          application_id=1
        ),
        dict(
          id=2,
          created_at="2022-03-02 22:08:00",
          updated_at="2022-03-02 22:08:00",
          job_script_name="script2",
          job_script_description="Job Script 2",
          job_script_data_as_string="{}",
          job_script_owner_email="tucker@omnivector.com",
          application_id=1
        ),
        dict(
          id=3,
          created_at="2022-03-02 22:08:00",
          updated_at="2022-03-02 22:08:00",
          job_script_name="script3",
          job_script_description="Job Script 3",
          job_script_data_as_string="{}",
          job_script_owner_email="james@omnivector.com",
          application_id=1
        ),
    ]
