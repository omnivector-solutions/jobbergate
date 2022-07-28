import pytest

DUMMY_TEMPLATE = """
#!/bin/bash

#SBATCH --job-name={{data.job_name}}
#SBATCH --partition={{data.partition}}
#SBATCH --output=sample-%j.out


echo $SLURM_TASKS_PER_NODE
echo $SLURM_SUBMIT_DIR
"""

DUMMY_APPLICATION_SOURCE_FILE = """
from jobbergate_cli.application_base import JobbergateApplicationBase
from jobbergate_cli import appform

class JobbergateApplication(JobbergateApplicationBase):

    def mainflow(self, data):
        questions = []

        questions.append(appform.List(
            variablename="partition",
            message="Choose slurm partition:",
            choices=self.application_config['partitions'],
        ))

        questions.append(appform.Text(
            variablename="job_name",
            message="Please enter a jobname",
            default=self.application_config['job_name']
        ))
        return questions
"""

DUMMY_APPLICATION_CONFIG = """
application_config:
  job_name: rats
  partitions:
  - debug
  - partition1
jobbergate_config:
  default_template: test_job_script.sh
  output_directory: .
  supporting_files:
  - test_job_script.sh
  supporting_files_output_name:
    test_job_script.sh:
    - support_file_b.py
  template_files:
  - templates/test_job_script.sh
"""


@pytest.mark.parametrize(
    "is_valid, source_code",
    [
        (False, "for i in range(10):\nprint(i)"),
        (True, "for i in range(10):\n    print(i)"),
    ],
)
def test_is_valid_python_file(is_valid, source_code):
    """
    Test if a given python source code is correctly checked as valid or not.
    """
    assert is_valid_python_file(source_code) is is_valid


@pytest.mark.parametrize(
    "is_valid, source_code",
    [
        (False, "unbalanced blackets: ]["),
        (True, "balanced blackets: []"),
    ],
)
def test_is_valid_yaml_file(is_valid, source_code):
    """
    Test if a given YAML file is correctly checked as valid or not.
    """
    assert is_valid_yaml_file(source_code) is is_valid
