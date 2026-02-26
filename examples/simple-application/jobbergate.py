from jobbergate_cli.subapps.applications.application_base import JobbergateApplicationBase
from jobbergate_cli.subapps.applications.questions import (
    Text,
    Integer,
    List,
    Checkbox,
    Confirm,
    BooleanList,
    Directory,
)


class JobbergateApplication(JobbergateApplicationBase):
    """Comprehensive example showcasing all question types and TUI features."""

    def mainflow(self, data=None):
        """Main workflow demonstrating basic question types."""
        if data is None:
            data = dict()
        data["nextworkflow"] = "advanced_flow"
        return [
            # Text input with default (should show green)
            Text(
                "job_name",
                message="Enter a name for your job",
                default="my-awesome-job",
            ),
            # Text input without default (should be neutral/empty)
            Text(
                "description",
                message="Enter a job description (optional)",
            ),
            # Integer with validation and default
            Integer(
                "num_nodes",
                message="Number of compute nodes (1-100)",
                minval=1,
                maxval=100,
                default=4,
            ),
            # Integer without default (should be empty)
            Integer(
                "num_tasks",
                message="Number of tasks per node (1-48)",
                minval=1,
                maxval=48,
            ),
            # List/dropdown selection
            List(
                "partition",
                message="Select compute partition",
                choices=["debug", "standard", "gpu", "bigmem"],
                default="standard",
            ),
        ]

    def advanced_flow(self, data=None):
        """Advanced workflow with more question types."""
        if data is None:
            data = dict()
        data["nextworkflow"] = "final_flow"
        return [
            # Checkbox for multi-select
            Checkbox(
                "modules",
                message="Select software modules to load",
                choices=["python/3.11", "gcc/11.2", "openmpi/4.1", "cuda/12.0"],
                default=["python/3.11"],
            ),
            # Confirm (yes/no)
            Confirm(
                "email_notifications",
                message="Enable email notifications?",
                default=True,
            ),
            # BooleanList with conditional follow-up
            BooleanList(
                "use_gpu",
                message="Will this job use GPUs?",
                default=False,
                whentrue=[
                    Integer(
                        "num_gpus",
                        message="Number of GPUs per node (1-4)",
                        minval=1,
                        maxval=4,
                        default=1,
                    ),
                    List(
                        "gpu_type",
                        message="GPU type required",
                        choices=["a100", "v100", "rtx6000"],
                        default="a100",
                    ),
                ],
                whenfalse=[
                    Text(
                        "cpu_type",
                        message="Preferred CPU architecture",
                        default="x86_64",
                    ),
                ],
            ),
        ]

    def final_flow(self, data=None):
        """Final workflow with path inputs."""
        if data is None:
            data = dict()
        return [
            # Directory input (no validation for demo purposes)
            Directory(
                "working_dir",
                message="Working directory path",
                exists=None,  # Don't validate existence
                default="/scratch/user/job-{}".format(data.get("job_name", "default")),
            ),
            # Time allocation
            Integer(
                "walltime_hours",
                message="Maximum runtime in hours (1-72)",
                minval=1,
                maxval=72,
                default=2,
            ),
            # Output filename
            Text(
                "output_file",
                message="Output filename",
                default="results-{}.txt".format(data.get("job_name", "output")),
            ),
        ]
