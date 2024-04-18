"""Database models for the cluster health resource."""

from pendulum.datetime import DateTime as PendulumDateTime
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from jobbergate_api.apps.models import Base, CommonMixin, TimestampMixin


class ClusterStatus(CommonMixin, TimestampMixin, Base):
    """Cluster status table definition."""

    client_id: Mapped[str] = mapped_column(String, primary_key=True)
    interval: Mapped[int] = mapped_column(Integer, nullable=False)
    last_reported: Mapped[PendulumDateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=PendulumDateTime.utcnow,
    )

    @property
    def is_healthy(self) -> bool:
        """Return True if the last_reported time is before now plus the interval in seconds between pings."""
        return PendulumDateTime.utcnow().subtract(seconds=self.interval) <= self.last_reported
