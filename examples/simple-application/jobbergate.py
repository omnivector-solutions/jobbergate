from jobbergate_cli.subapps.applications.application_base import JobbergateApplicationBase
from jobbergate_cli.subapps.applications.questions import (
    BooleanList,
    Checkbox,
    Integer,
    List,
    Text,
)


class JobbergateApplication(JobbergateApplicationBase):

    def mainflow(self, data=None):
        if data is None:
            data = dict()
        data["nextworkflow"] = "subflow"
        return [
            Text("foo", message="gimme the foo!", default="foo"),
            Text("bar", message="gimme the bar!", default="bar"),
            # Integer with range validation: try answering 0 or 99 to see it rejected
            Integer("ntasks", message="How many tasks? (1 to 8)", default=2, minval=1, maxval=8),
            # Single choice from a fixed list (dropdown on the web form)
            List(
                "queue",
                message="Which partition should run the job?",
                choices=["compute", "form", "debug"],
                default="compute",
            ),
        ]

    def subflow(self, data=None):
        if data is None:
            data = dict()
        return [
            # Multiple selection
            Checkbox(
                "toppings",
                message="Pick your toppings",
                choices=["cheese", "mushrooms", "pineapple"],
            ),
            # Fan favorite: a confirmation with different follow-ups per answer
            BooleanList(
                "notify",
                message="Do you want to be notified when the job finishes?",
                default=True,
                whentrue=[
                    # Custom JSON Schema constraints ride along with the question: the web
                    # form pre-validates the pattern instantly, and the runtime enforces it
                    Text(
                        "email",
                        message="Which email should we notify?",
                        default="user@example.com",
                        schema={"pattern": r"^\S+@\S+\.\S+$"},
                    )
                ],
                whenfalse=[Text("email", message="No notifications then; who takes the blame?", default="nobody")],
            ),
            Text("filename", message="gimme the filename!", default="dummy-result.txt"),
        ]
