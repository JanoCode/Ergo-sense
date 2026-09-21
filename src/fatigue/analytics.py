from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional

from fatigue.models import (
    AnalyticsChange, AnalyticsPeriod, DailyFatigueStats, FatigueLevel,
    FatigueTrend, HistoricalFatigueSession, PeriodFatigueStats,
    SessionFatigueSummary, UserFatigueAnalytics,
)


_LEVEL_RANK = {
    FatigueLevel.NORMAL: 0,
    FatigueLevel.MILD: 1,
    FatigueLevel.MODERATE: 2,
    FatigueLevel.HIGH: 3,
    FatigueLevel.VERY_HIGH: 4,
}


@dataclass(frozen=True)
class FatigueAnalyticsConfig:
    minimum_comparable_duration_seconds: int = 30 * 60
    minimum_sessions_for_trend: int = 3
    stable_relative_change: float = 0.10
    stable_high_percentage_points: float = 10.0


class SQLiteFatigueAnalyticsRepository:
    def __init__(self, database_manager):
        self.db = database_manager

    def get_user_history(
        self,
        user_id: int,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[HistoricalFatigueSession]:
        query = '''
            SELECT s.started_at, fs.*
            FROM fatigue_session_summaries fs
            JOIN sessions s ON s.id = fs.session_id
            WHERE fs.user_id = ?
        '''
        params = [user_id]
        if start is not None:
            query += " AND s.started_at >= ?"
            params.append(start.isoformat())
        if end is not None:
            query += " AND s.started_at < ?"
            params.append(end.isoformat())
        query += " ORDER BY s.started_at ASC"
        with closing(self.db.get_connection()) as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._from_row(row) for row in rows]

    @staticmethod
    def _from_row(row) -> HistoricalFatigueSession:
        summary = SessionFatigueSummary(
            session_id=row["session_id"], user_id=row["user_id"],
            duration_seconds=row["duration_seconds"],
            total_blinks=row["total_blinks"],
            average_blink_rate=row["average_blink_rate"],
            average_blink_duration=row["average_blink_duration"],
            average_perclos=row["average_perclos"], max_perclos=row["max_perclos"],
            prolonged_closures=row["prolonged_closures"], yawns=row["yawns"],
            max_head_deviation_degrees=row["max_head_deviation_degrees"],
            average_score=row["average_score"], max_score=row["max_score"],
            max_level=FatigueLevel(row["max_level"]) if row["max_level"] else None,
            time_to_mild_seconds=row["time_to_mild_seconds"],
            time_to_moderate_seconds=row["time_to_moderate_seconds"],
            time_to_high_seconds=row["time_to_high_seconds"],
        )
        return HistoricalFatigueSession(
            started_at=datetime.fromisoformat(row["started_at"]), summary=summary
        )


class FatigueAnalyticsService:
    METRICS_TO_COMPARE = (
        "average_session_duration_seconds", "average_score", "average_max_score",
        "moderate_session_percentage", "high_session_percentage",
        "average_time_to_mild_seconds", "average_time_to_moderate_seconds",
        "average_time_to_high_seconds", "average_perclos",
        "average_prolonged_closures", "average_yawns",
    )

    def __init__(self, repository, config: Optional[FatigueAnalyticsConfig] = None):
        self.repository = repository
        self.config = config or FatigueAnalyticsConfig()

    def analyze(
        self,
        user_id: int,
        period: AnalyticsPeriod = AnalyticsPeriod.LAST_7_DAYS,
        now: Optional[datetime] = None,
    ) -> UserFatigueAnalytics:
        now = now or datetime.now()
        if period == AnalyticsPeriod.ALL_TIME:
            current_records = self.repository.get_user_history(user_id)
            current = self.calculate_stats(current_records, None, now)
            previous = None
        else:
            days = period.value
            current_start = now - timedelta(days=days)
            previous_start = current_start - timedelta(days=days)
            current_records = self.repository.get_user_history(user_id, current_start, now)
            previous_records = self.repository.get_user_history(
                user_id, previous_start, current_start
            )
            current = self.calculate_stats(current_records, current_start, now)
            previous = self.calculate_stats(
                previous_records, previous_start, current_start
            )

        changes = self.compare_periods(current, previous) if previous else {}
        trend = self.determine_trend(current, previous, changes)
        insights = self._insights(current, previous, changes, trend)
        return UserFatigueAnalytics(
            user_id=user_id, period=period, current_period=current,
            previous_period=previous, changes=changes, trend=trend,
            available_data={
                "sessions": current.session_count,
                "comparable_sessions": current.comparable_session_count,
                "previous_comparable_sessions": (
                    previous.comparable_session_count if previous else 0
                ),
            },
            insights=insights, daily=self.group_by_day(current_records),
        )

    def calculate_stats(
        self,
        records: Iterable[HistoricalFatigueSession],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> PeriodFatigueStats:
        records = list(records)
        comparable = [
            item for item in records
            if item.summary.duration_seconds
            >= self.config.minimum_comparable_duration_seconds
        ]
        level_records = [item for item in comparable if item.summary.max_level is not None]

        return PeriodFatigueStats(
            start=start, end=end, session_count=len(records),
            comparable_session_count=len(comparable),
            total_monitored_seconds=sum(item.summary.duration_seconds for item in records),
            average_session_duration_seconds=self._mean(
                item.summary.duration_seconds for item in records
            ),
            average_score=self._mean(
                item.summary.average_score for item in comparable
            ),
            average_max_score=self._mean(
                item.summary.max_score for item in comparable
            ),
            moderate_session_percentage=self._level_percentage(
                level_records, FatigueLevel.MODERATE
            ),
            high_session_percentage=self._level_percentage(
                level_records, FatigueLevel.HIGH
            ),
            average_time_to_mild_seconds=self._mean(
                item.summary.time_to_mild_seconds for item in comparable
            ),
            average_time_to_moderate_seconds=self._mean(
                item.summary.time_to_moderate_seconds for item in comparable
            ),
            average_time_to_high_seconds=self._mean(
                item.summary.time_to_high_seconds for item in comparable
            ),
            average_perclos=self._mean(
                item.summary.average_perclos for item in comparable
            ),
            average_prolonged_closures=self._mean(
                item.summary.prolonged_closures for item in comparable
            ),
            average_yawns=self._mean(item.summary.yawns for item in comparable),
        )

    def compare_periods(
        self, current: PeriodFatigueStats, previous: PeriodFatigueStats
    ) -> Dict[str, AnalyticsChange]:
        changes = {}
        for name in self.METRICS_TO_COMPARE:
            current_value = getattr(current, name)
            previous_value = getattr(previous, name)
            if current_value is None or previous_value is None:
                absolute = percentage = None
            else:
                absolute = current_value - previous_value
                percentage = (
                    absolute / previous_value * 100.0
                    if previous_value != 0 else None
                )
            changes[name] = AnalyticsChange(
                previous=previous_value, current=current_value,
                absolute=absolute, percentage=percentage,
            )
        return changes

    def determine_trend(
        self,
        current: PeriodFatigueStats,
        previous: Optional[PeriodFatigueStats],
        changes: Dict[str, AnalyticsChange],
    ) -> FatigueTrend:
        if (previous is None
                or current.comparable_session_count < self.config.minimum_sessions_for_trend
                or previous.comparable_session_count < self.config.minimum_sessions_for_trend):
            return FatigueTrend.INSUFFICIENT_DATA

        votes = []
        moderate = changes.get("average_time_to_moderate_seconds")
        if moderate and moderate.percentage is not None:
            votes.append(self._direction(moderate.percentage, higher_is_better=True))
        score = changes.get("average_score")
        if score and score.percentage is not None:
            votes.append(self._direction(score.percentage, higher_is_better=False))
        high = changes.get("high_session_percentage")
        if high and high.absolute is not None:
            threshold = self.config.stable_high_percentage_points
            votes.append(-1 if high.absolute > threshold else 1 if high.absolute < -threshold else 0)

        if len(votes) < 2:
            return FatigueTrend.INSUFFICIENT_DATA
        mean_vote = sum(votes) / len(votes)
        if mean_vote >= 0.34:
            return FatigueTrend.IMPROVING
        if mean_vote <= -0.34:
            return FatigueTrend.WORSENING
        return FatigueTrend.STABLE

    def group_by_day(
        self, records: Iterable[HistoricalFatigueSession]
    ) -> List[DailyFatigueStats]:
        groups = {}
        for record in records:
            groups.setdefault(record.started_at.date(), []).append(record)
        daily = []
        for day in sorted(groups):
            records_for_day = groups[day]
            comparable = [
                item for item in records_for_day
                if item.summary.duration_seconds
                >= self.config.minimum_comparable_duration_seconds
            ]
            daily.append(DailyFatigueStats(
                day=day, session_count=len(records_for_day),
                comparable_session_count=len(comparable),
                total_monitored_seconds=sum(
                    item.summary.duration_seconds for item in records_for_day
                ),
                average_score=self._mean(
                    item.summary.average_score for item in comparable
                ),
                average_time_to_moderate_seconds=self._mean(
                    item.summary.time_to_moderate_seconds for item in comparable
                ),
            ))
        return daily

    def _insights(self, current, previous, changes, trend) -> List[str]:
        if trend == FatigueTrend.INSUFFICIENT_DATA:
            return ["No existen suficientes sesiones comparables para determinar una tendencia."]
        insights = []
        moderate = changes.get("average_time_to_moderate_seconds")
        if moderate and moderate.absolute is not None:
            minutes = abs(moderate.absolute) / 60.0
            verb = "aumentó" if moderate.absolute > 0 else "disminuyó"
            insights.append(
                f"El tiempo promedio hasta fatiga moderada {verb} "
                f"{minutes:.0f} minutos respecto al período anterior."
            )
        score = changes.get("average_score")
        if score and score.absolute is not None:
            verb = "aumentó" if score.absolute > 0 else "disminuyó"
            insights.append(
                f"El Fatigue Score promedio {verb} {abs(score.absolute):.1f} puntos."
            )
        if not insights:
            insights.append("Las métricas disponibles se mantuvieron estables.")
        return insights

    def _direction(self, percentage: float, higher_is_better: bool) -> int:
        threshold = self.config.stable_relative_change * 100.0
        if abs(percentage) <= threshold:
            return 0
        direction = 1 if percentage > 0 else -1
        return direction if higher_is_better else -direction

    @staticmethod
    def _mean(values) -> Optional[float]:
        valid = [value for value in values if value is not None]
        return sum(valid) / len(valid) if valid else None

    @staticmethod
    def _level_percentage(records, threshold: FatigueLevel) -> Optional[float]:
        if not records:
            return None
        reached = sum(
            _LEVEL_RANK[item.summary.max_level] >= _LEVEL_RANK[threshold]
            for item in records
        )
        return reached / len(records) * 100.0
