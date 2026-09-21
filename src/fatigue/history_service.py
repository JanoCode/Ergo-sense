from typing import Optional

from fatigue.models import (
    FatigueAssessment, FatigueEvent, FatigueEventType, FatigueLevel,
    FatigueMetrics, SessionFatigueSummary, SessionFinalMetrics,
    StoredFatigueAssessment,
)


_LEVEL_RANK = {
    FatigueLevel.NORMAL: 0,
    FatigueLevel.MILD: 1,
    FatigueLevel.MODERATE: 2,
    FatigueLevel.HIGH: 3,
    FatigueLevel.VERY_HIGH: 4,
}


class FatigueHistoryService:
    """Coordina el historial de fatiga de una sesión sin depender de la UI."""

    def __init__(self, repository):
        self.repository = repository

    def record_assessment(
        self,
        session_id: int,
        user_id: int,
        assessment: FatigueAssessment,
        metrics: FatigueMetrics,
    ) -> StoredFatigueAssessment:
        previous = self.repository.get_assessments(session_id)
        previous_rank = max((_LEVEL_RANK[item.level] for item in previous), default=0)
        stored = StoredFatigueAssessment(
            session_id=session_id, user_id=user_id,
            timestamp=assessment.timestamp, score=assessment.score,
            level=assessment.level, confidence=assessment.confidence,
            active_signals=list(assessment.active_signals),
            unavailable_signals=list(assessment.unavailable_signals),
            reasons=list(assessment.reasons), perclos=metrics.perclos,
            head_deviation_degrees=metrics.pitch_deviation_degrees,
        )
        stored, inserted = self.repository.save_assessment(stored)
        if not inserted:
            return stored

        self.record_metric_events(
            session_id, user_id, assessment.timestamp, metrics
        )

        current_rank = _LEVEL_RANK[assessment.level]
        level_events = (
            (2, FatigueEventType.ENTERED_MODERATE),
            (3, FatigueEventType.ENTERED_HIGH),
            (4, FatigueEventType.ENTERED_VERY_HIGH),
        )
        for rank, event_type in level_events:
            if previous_rank < rank <= current_rank:
                self._event(
                    session_id, user_id, event_type, assessment.timestamp,
                    {"score": assessment.score, "level": assessment.level.value},
                )
        return stored

    def record_metric_events(
        self, session_id: int, user_id: int, timestamp: float,
        metrics: FatigueMetrics,
    ):
        """Guarda eventos de una ventana, incluso si aún no genera assessment."""
        if metrics.prolonged_closures and metrics.prolonged_closures > 0:
            self._event(
                session_id, user_id, FatigueEventType.PROLONGED_EYE_CLOSURE,
                timestamp, {"count": metrics.prolonged_closures},
            )
        if metrics.yawns and metrics.yawns > 0:
            self._event(
                session_id, user_id, FatigueEventType.YAWN,
                timestamp, {"count": metrics.yawns},
            )
        if metrics.sustained_head_drop is True:
            self._event(
                session_id, user_id, FatigueEventType.HEAD_DROP,
                timestamp,
                {"pitch_deviation_degrees": metrics.pitch_deviation_degrees},
            )

    def get_assessments(self, session_id: int):
        return self.repository.get_assessments(session_id)

    def get_events(self, session_id: int, event_type=None):
        return self.repository.get_events(session_id, event_type)

    def finalize_session(
        self,
        session_id: int,
        user_id: int,
        session_started_timestamp: float,
        final_metrics: SessionFinalMetrics,
    ) -> SessionFatigueSummary:
        assessments = self.repository.get_assessments(session_id)
        perclos_values = [item.perclos for item in assessments if item.perclos is not None]
        head_values = [
            item.head_deviation_degrees for item in assessments
            if item.head_deviation_degrees is not None
        ]
        if final_metrics.max_head_deviation_degrees is not None:
            head_values.append(final_metrics.max_head_deviation_degrees)
        scores = [item.score for item in assessments]
        max_level = max(
            (item.level for item in assessments),
            key=lambda level: _LEVEL_RANK[level], default=None,
        )

        def first_time(level: FatigueLevel) -> Optional[float]:
            required_rank = _LEVEL_RANK[level]
            matches = [
                item.timestamp for item in assessments
                if _LEVEL_RANK[item.level] >= required_rank
            ]
            return max(min(matches) - session_started_timestamp, 0.0) if matches else None

        summary = SessionFatigueSummary(
            session_id=session_id, user_id=user_id,
            duration_seconds=final_metrics.duration_seconds,
            total_blinks=final_metrics.total_blinks,
            average_blink_rate=final_metrics.average_blink_rate,
            average_blink_duration=final_metrics.average_blink_duration,
            average_perclos=(sum(perclos_values) / len(perclos_values)) if perclos_values else None,
            max_perclos=max(perclos_values) if perclos_values else None,
            prolonged_closures=final_metrics.prolonged_closures,
            yawns=final_metrics.yawns,
            max_head_deviation_degrees=max(head_values) if head_values else None,
            average_score=(sum(scores) / len(scores)) if scores else None,
            max_score=max(scores) if scores else None,
            max_level=max_level,
            time_to_mild_seconds=first_time(FatigueLevel.MILD),
            time_to_moderate_seconds=first_time(FatigueLevel.MODERATE),
            time_to_high_seconds=first_time(FatigueLevel.HIGH),
        )
        return self.repository.save_summary(summary)

    def get_summary(self, session_id: int):
        return self.repository.get_summary(session_id)

    def _event(self, session_id, user_id, event_type, timestamp, data):
        return self.repository.save_event(FatigueEvent(
            session_id=session_id, user_id=user_id, event_type=event_type,
            timestamp=timestamp, data=data,
        ))
