from auto_name_enum import AutoNameEnum, NoMangleMixin, auto


class JobSubmissionStatus(AutoNameEnum, NoMangleMixin):
    CREATED = auto()
    SUBMITTED = auto()
    COMPLETED = auto()
