from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Optional

from wellbeing.models import BreakEventType, WellbeingBreak


@dataclass(frozen=True)
class SessionWellbeingSummary:
    session_id: int
    started_at: datetime
    ended_at: Optional[datetime]
    total_duration_seconds: int
    work_seconds: int
    break_seconds: int
    completed_breaks: int
    postponed_breaks: int
    max_continuous_usage_seconds: int
    average_break_seconds: float
    break_durations_seconds: tuple[int, ...] = field(default_factory=tuple)
    continuous_before_break_seconds: tuple[int, ...] = field(default_factory=tuple)
    has_break_data: bool = False


@dataclass(frozen=True)
class PeriodWellbeingStats:
    days: int
    session_count: int = 0
    total_usage_seconds: int = 0
    total_break_seconds: int = 0
    completed_breaks: int = 0
    average_breaks_per_session: float = 0.0
    average_continuous_before_break_seconds: float = 0.0
    total_postponed_breaks: int = 0


class WellbeingAnalyticsService:
    def __init__(
        self,
        session_service,
        break_repository,
        now_provider: Callable[[], datetime] = datetime.now,
    ):
        self.session_service = session_service
        self.break_repository = break_repository
        self._now = now_provider

    def session_summary(self, session) -> SessionWellbeingSummary:
        breaks = self.break_repository.get_breaks_by_session(session.id)
        events = self.break_repository.get_by_session(session.id)
        completed = [item for item in breaks if item.ended_at is not None]
        postponed = sum(
            event.event_type == BreakEventType.BREAK_POSTPONED
            for event in events
        )
        break_durations = tuple(item.duration_seconds or 0 for item in completed)
        break_seconds = sum(break_durations)
        total = self._session_duration(session)

        cursor = session.started_at
        continuous_periods = []
        for item in completed:
            continuous_periods.append(
                max(0, int((item.started_at - cursor).total_seconds()))
            )
            cursor = item.ended_at
        end = session.ended_at or self._now()
        final_continuous = max(0, int((end - cursor).total_seconds()))
        all_continuous = continuous_periods + [final_continuous]

        return SessionWellbeingSummary(
            session_id=session.id,
            started_at=session.started_at,
            ended_at=session.ended_at,
            total_duration_seconds=total,
            work_seconds=max(0, total - break_seconds),
            break_seconds=break_seconds,
            completed_breaks=len(completed),
            postponed_breaks=postponed,
            max_continuous_usage_seconds=max(all_continuous, default=0),
            average_break_seconds=(
                break_seconds / len(completed) if completed else 0.0
            ),
            break_durations_seconds=break_durations,
            continuous_before_break_seconds=tuple(continuous_periods),
            has_break_data=bool(breaks or events),
        )

    def period_stats(
        self,
        user_id: int,
        days: int,
        end_at: Optional[datetime] = None,
    ) -> PeriodWellbeingStats:
        end = end_at or self._now()
        start = end - timedelta(days=days)
        sessions = [
            session for session in self.session_service.get_user_sessions(user_id)
            if start <= session.started_at < end
        ]
        summaries = [self.session_summary(session) for session in sessions]
        continuous = [
            seconds
            for summary in summaries
            for seconds in summary.continuous_before_break_seconds
        ]
        completed = sum(item.completed_breaks for item in summaries)
        return PeriodWellbeingStats(
            days=days,
            session_count=len(summaries),
            total_usage_seconds=sum(
                item.work_seconds for item in summaries
            ),
            total_break_seconds=sum(item.break_seconds for item in summaries),
            completed_breaks=completed,
            average_breaks_per_session=(
                completed / len(summaries) if summaries else 0.0
            ),
            average_continuous_before_break_seconds=(
                sum(continuous) / len(continuous) if continuous else 0.0
            ),
            total_postponed_breaks=sum(
                item.postponed_breaks for item in summaries
            ),
        )

    def compare_weekly_breaks(self, user_id: int) -> str:
        now = self._now()
        current = self.period_stats(user_id, 7, now)
        previous = self.period_stats(user_id, 7, now - timedelta(days=7))
        if current.session_count == 0 and previous.session_count == 0:
            return "Aún no hay datos para comparar estas semanas."
        return (
            f"Esta semana realizaste {current.completed_breaks} pausas "
            f"frente a {previous.completed_breaks} la semana anterior."
        )

    def daily_stats(self, user_id: int, days: int = 7) -> list[tuple]:
        end = self._now()
        start = end - timedelta(days=days)
        buckets = {}
        for session in self.session_service.get_user_sessions(user_id):
            if start <= session.started_at < end:
                day = session.started_at.date()
                summary = self.session_summary(session)
                usage, breaks = buckets.get(day, (0, 0))
                buckets[day] = (
                    usage + summary.work_seconds,
                    breaks + summary.completed_breaks,
                )
        return [(day, *buckets[day]) for day in sorted(buckets)]

    def _session_duration(self, session) -> int:
        if session.duration_seconds is not None:
            return max(0, session.duration_seconds)
        return max(0, int(((session.ended_at or self._now()) - session.started_at).total_seconds()))
