"""
Provide a time-loop class that can be used to to iterate during a given window of time.
"""

from typing import Optional, Union

import pendulum
import pydantic
from rich.progress import Progress

from jobbergate_cli.exceptions import JobbergateCliError


class Tick(pydantic.BaseModel):
    """
    A helper class describing a "tick".

    Contains a counter, elapsed time since the last tick, and total elapsed time.
    """

    counter: int
    elapsed: pendulum.Duration
    total_elapsed: pendulum.Duration


class TimeLoop:
    """
    A special iterator that will iterate for a specified duration of time.

    Uses a progress meter to show the user how much time is left.
    Each iteration of the time-loop produces a tick.
    """

    advent: Optional[pendulum.DateTime]
    moment: Optional[pendulum.DateTime]
    last_moment: Optional[pendulum.DateTime]
    counter: int
    progress: Optional[Progress]
    duration: pendulum.Duration
    message: str
    color: str

    def __init__(
        self,
        duration: Union[pendulum.Duration, int],
        message: str = "Processing",
        color: str = "green",
    ):
        """
        Initialize the time-loop.

        Duration may be either a count of seconds or a ``pendulum.duration``.
        """
        self.moment = None
        self.last_moment = None
        self.counter = 0
        self.progress = None
        if isinstance(duration, int):
            JobbergateCliError.require_condition(duration > 0, "The duration must be a positive integer")
            self.duration = pendulum.duration(seconds=duration)
        else:
            self.duration = duration
        self.message = message
        self.color = color

    def __del__(self):
        """
        Explicitly clear the progress meter if the time-loop is destroyed.
        """
        self.clear()

    def __iter__(self) -> "TimeLoop":
        """
        Start the iterator.

        Creates and starts the progress meter
        """
        self.advent = self.last_moment = self.moment = pendulum.now()
        self.counter = 0
        self.progress = Progress()
        self.progress.add_task(
            f"[{self.color}]{self.message}...",
            total=self.duration.total_seconds(),
        )
        self.progress.start()
        return self

    def __next__(self) -> Tick:
        """
        Iterates the time loop and returns a tick.

        If the duration is complete, clear the progress meter and stop iteration.
        """
        # Keep mypy happy
        assert self.progress is not None

        self.counter += 1
        self.last_moment = self.moment
        self.moment: pendulum.DateTime = pendulum.now()
        elapsed: pendulum.Duration = self.moment - self.last_moment
        total_elapsed: pendulum.Duration = self.moment - self.advent

        for task_id in self.progress.task_ids:
            self.progress.advance(task_id, elapsed.total_seconds())

        if self.progress.finished:
            self.clear()
            raise StopIteration

        return Tick(
            counter=self.counter,
            elapsed=elapsed,
            total_elapsed=total_elapsed,
        )

    def clear(self):
        """
        Clear the time-loop.

        Stops the progress meter (if it is set) and reset moments, counter, progress meter.
        """
        if self.progress is not None:
            self.progress.stop()
        self.counter = 0
        self.progress = None
        self.moment = None
        self.last_moment = None
