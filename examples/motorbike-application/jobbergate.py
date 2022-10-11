from jobbergate_cli.subapps.applications.application_base import JobbergateApplicationBase
from jobbergate_cli.subapps.applications.questions import Text, Integer, Directory


class JobbergateApplication(JobbergateApplicationBase):
    def mainflow(self, *_, **__):
        questions = []

        questions.append(Text(
            "partition",
            message="Choose a partition",
            default="compute"
        ))
        questions.append(Integer(
            "nodes",
            message="Choose number of nodes for job",
            default=2,
            minval=1,
        ))
        questions.append(Integer(
            "ntasks",
            message="Choose number of tasks per node for job",
            default=6,
            minval=1,
        ))
        questions.append(Text(
            "workdir",
            message="Choose working directory (will hold results as well)",
            default="/nfs",
        ))
        return questions
