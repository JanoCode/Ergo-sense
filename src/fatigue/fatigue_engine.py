import math
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from fatigue.baseline import BaselineState, MetricBaseline, UserBaseline
from fatigue.models import FatigueAssessment, FatigueLevel, FatigueMetrics


@dataclass(frozen=True)
class FatigueEngineConfig:
    """Configuración central de pesos, niveles y reglas deterministas."""

    evaluation_interval_seconds: float = 30.0
    ema_alpha: float = 0.35
    minimum_observation_seconds: float = 120.0

    ocular_weight: float = 0.35
    yawn_weight: float = 0.05
    posture_weight: float = 0.25
    temporal_weight: float = 0.15
    convergence_weight: float = 0.20

    level_thresholds: Tuple[Tuple[float, FatigueLevel], ...] = (
        (80.0, FatigueLevel.VERY_HIGH),
        (60.0, FatigueLevel.HIGH),
        (40.0, FatigueLevel.MODERATE),
        (20.0, FatigueLevel.MILD),
        (0.0, FatigueLevel.NORMAL),
    )

    perclos_range: Tuple[float, float] = (0.10, 0.40)
    blink_duration_range: Tuple[float, float] = (0.20, 0.60)
    blink_rate_normal_range: Tuple[float, float] = (8.0, 25.0)
    prolonged_closure_range: Tuple[float, float] = (0.0, 4.0)
    yawns_per_hour_range: Tuple[float, float] = (1.0, 8.0)
    yawn_duration_range: Tuple[float, float] = (2.0, 8.0)
    pitch_deviation_range: Tuple[float, float] = (10.0, 35.0)
    session_duration_range: Tuple[float, float] = (3600.0, 14400.0)
    baseline_ratio_range: Tuple[float, float] = (1.20, 3.0)
    blink_rate_change_range: Tuple[float, float] = (0.20, 0.80)
    active_signal_threshold: float = 0.25

    def __post_init__(self):
        weights = (
            self.ocular_weight, self.yawn_weight, self.posture_weight,
            self.temporal_weight, self.convergence_weight,
        )
        if any(weight < 0 for weight in weights) or not math.isclose(sum(weights), 1.0):
            raise ValueError("Los pesos del Fatigue Score deben ser no negativos y sumar 1")
        if not 0.0 < self.ema_alpha <= 1.0:
            raise ValueError("ema_alpha debe estar en el intervalo (0, 1]")


@dataclass
class _Signal:
    name: str
    category: str
    severity: float
    reason: str
    baseline_used: bool = False


class FatigueEngine:
    """Combina métricas calculadas en un score determinista y explicable."""

    SIGNAL_NAMES = (
        "perclos", "prolonged_closures", "blink_duration", "blink_rate",
        "yawn_frequency", "yawn_duration", "pitch_deviation", "head_drop",
        "session_duration",
    )

    def __init__(self, config: Optional[FatigueEngineConfig] = None):
        self.config = config or FatigueEngineConfig()
        self._smoothed_score: Optional[float] = None
        self._last_evaluation_timestamp: Optional[float] = None

    def reset(self, timestamp: Optional[float] = None):
        self._smoothed_score = None
        self._last_evaluation_timestamp = timestamp

    def is_due(self, timestamp: Optional[float] = None) -> bool:
        now = time.time() if timestamp is None else timestamp
        return (self._last_evaluation_timestamp is None
                or now - self._last_evaluation_timestamp >= self.config.evaluation_interval_seconds)

    def evaluate_if_due(
        self,
        metrics: FatigueMetrics,
        baseline: Optional[UserBaseline] = None,
        timestamp: Optional[float] = None,
    ) -> Optional[FatigueAssessment]:
        now = time.time() if timestamp is None else timestamp
        if not self.is_due(now):
            return None
        return self.assess(metrics, baseline, now)

    def assess(
        self,
        metrics: FatigueMetrics,
        baseline: Optional[UserBaseline] = None,
        timestamp: Optional[float] = None,
    ) -> FatigueAssessment:
        now = time.time() if timestamp is None else timestamp
        signals, unavailable = self._build_signals(metrics, baseline)
        raw_score = self._calculate_score(signals) * 100.0
        if self._smoothed_score is None:
            smoothed = raw_score
        else:
            alpha = self.config.ema_alpha
            smoothed = alpha * raw_score + (1.0 - alpha) * self._smoothed_score
        self._smoothed_score = self._clamp(smoothed, 0.0, 100.0)
        score = round(self._smoothed_score, 2)
        self._last_evaluation_timestamp = now

        active = [signal for signal in signals if signal.severity >= self.config.active_signal_threshold]
        confidence = self._confidence(signals, unavailable, metrics, baseline)
        return FatigueAssessment(
            timestamp=now,
            score=score,
            level=self.level_for_score(score),
            confidence=round(confidence, 3),
            active_signals=[signal.name for signal in active],
            unavailable_signals=unavailable,
            reasons=[signal.reason for signal in active],
        )

    def level_for_score(self, score: float) -> FatigueLevel:
        score = self._clamp(score, 0.0, 100.0)
        for threshold, level in self.config.level_thresholds:
            if score >= threshold:
                return level
        return FatigueLevel.NORMAL

    def _calculate_score(self, signals: List[_Signal]) -> float:
        category_weights = {
            "ocular": self.config.ocular_weight,
            "yawn": self.config.yawn_weight,
            "posture": self.config.posture_weight,
            "temporal": self.config.temporal_weight,
        }
        by_category: Dict[str, List[float]] = {}
        for signal in signals:
            by_category.setdefault(signal.category, []).append(signal.severity)

        available_weight = sum(category_weights[name] for name in by_category)
        primary_budget = 1.0 - self.config.convergence_weight
        if available_weight:
            weighted = sum(
                (sum(values) / len(values)) * category_weights[name]
                for name, values in by_category.items()
            )
            primary = weighted / available_weight * primary_budget
        else:
            primary = 0.0

        active_categories = [
            max(values) for values in by_category.values()
            if max(values) >= self.config.active_signal_threshold
        ]
        convergence = 0.0
        if len(active_categories) >= 2:
            independence = min((len(active_categories) - 1) / 3.0, 1.0)
            convergence = (
                sum(active_categories) / len(active_categories)
                * independence * self.config.convergence_weight
            )
        return self._clamp(primary + convergence, 0.0, 1.0)

    def _build_signals(
        self, metrics: FatigueMetrics, baseline: Optional[UserBaseline]
    ) -> Tuple[List[_Signal], List[str]]:
        signals: List[_Signal] = []
        unavailable: List[str] = []
        ready_baseline = baseline if baseline and baseline.state == BaselineState.READY else None

        self._add_relative_signal(
            signals, unavailable, "perclos", "ocular", metrics.perclos,
            ready_baseline.perclos if ready_baseline else None,
            self.config.perclos_range,
            "PERCLOS elevado respecto al baseline", "PERCLOS elevado",
        )
        self._add_general_signal(
            signals, unavailable, "prolonged_closures", "ocular",
            metrics.prolonged_closures, self.config.prolonged_closure_range,
            lambda value: f"{int(value)} cierres prolongados en la ventana reciente",
        )
        self._add_relative_signal(
            signals, unavailable, "blink_duration", "ocular",
            metrics.average_blink_duration,
            ready_baseline.blink_duration if ready_baseline else None,
            self.config.blink_duration_range,
            "Duración de parpadeo elevada respecto al baseline",
            "Duración de parpadeo elevada",
        )
        self._add_blink_rate(signals, unavailable, metrics.blink_rate, ready_baseline)
        self._add_general_signal(
            signals, unavailable, "yawn_frequency", "yawn", metrics.yawns_per_hour,
            self.config.yawns_per_hour_range,
            lambda value: f"Frecuencia de bostezos elevada ({value:.1f} por hora)",
        )
        self._add_general_signal(
            signals, unavailable, "yawn_duration", "yawn", metrics.average_yawn_duration,
            self.config.yawn_duration_range,
            lambda value: f"Duración media de bostezos elevada ({value:.1f}s)",
        )
        self._add_posture(signals, unavailable, metrics, ready_baseline)
        self._add_general_signal(
            signals, unavailable, "session_duration", "temporal",
            metrics.session_duration_seconds, self.config.session_duration_range,
            lambda value: f"Sesión continua prolongada ({value / 3600.0:.1f}h)",
        )
        return signals, unavailable

    def _add_relative_signal(
        self, signals, unavailable, name, category, value,
        metric_baseline: Optional[MetricBaseline], general_range,
        baseline_reason, fallback_reason,
    ):
        if not self._valid_number(value):
            unavailable.append(name)
            return
        baseline_used = bool(metric_baseline and metric_baseline.mean is not None and metric_baseline.mean > 0)
        if baseline_used:
            ratio = value / metric_baseline.mean
            severity = self._ramp(ratio, *self.config.baseline_ratio_range)
            reason = baseline_reason
        else:
            severity = self._ramp(value, *general_range)
            reason = fallback_reason
        signals.append(_Signal(name, category, severity, reason, baseline_used))

    def _add_general_signal(self, signals, unavailable, name, category, value, value_range, reason_factory):
        if not self._valid_number(value):
            unavailable.append(name)
            return
        signals.append(_Signal(name, category, self._ramp(value, *value_range), reason_factory(value)))

    def _add_blink_rate(self, signals, unavailable, value, baseline):
        if not self._valid_number(value):
            unavailable.append("blink_rate")
            return
        metric_baseline = baseline.blink_rate if baseline else None
        if metric_baseline and metric_baseline.mean is not None and metric_baseline.mean > 0:
            change = abs(value - metric_baseline.mean) / metric_baseline.mean
            severity = self._ramp(change, *self.config.blink_rate_change_range)
            reason = "Frecuencia de parpadeos cambió respecto al baseline"
            baseline_used = True
        else:
            low, high = self.config.blink_rate_normal_range
            distance = low - value if value < low else value - high if value > high else 0.0
            severity = self._ramp(distance, 0.0, 20.0)
            reason = "Frecuencia de parpadeos fuera del rango general"
            baseline_used = False
        signals.append(_Signal("blink_rate", "ocular", severity, reason, baseline_used))

    def _add_posture(self, signals, unavailable, metrics, baseline):
        deviation = metrics.pitch_deviation_degrees
        baseline_used = False
        reason = "Desviación sostenida de pitch"
        if (self._valid_number(metrics.current_pitch_degrees) and baseline
                and baseline.pitch and baseline.pitch.mean is not None):
            deviation = max(baseline.pitch.mean - metrics.current_pitch_degrees, 0.0)
            baseline_used = True
            reason = "Pitch sostenido por debajo de la postura habitual"
        if self._valid_number(deviation):
            severity = self._ramp(abs(deviation), *self.config.pitch_deviation_range)
            if metrics.sustained_pitch_deviation is True:
                severity = max(severity, 0.8)
            elif metrics.sustained_pitch_deviation is False:
                severity = 0.0
            signals.append(_Signal("pitch_deviation", "posture", severity, reason, baseline_used))
        elif metrics.sustained_pitch_deviation is not None:
            severity = 0.8 if metrics.sustained_pitch_deviation else 0.0
            signals.append(_Signal("pitch_deviation", "posture", severity, reason, baseline_used))
        else:
            unavailable.append("pitch_deviation")

        if metrics.sustained_head_drop is None:
            unavailable.append("head_drop")
        else:
            severity = 1.0 if metrics.sustained_head_drop else 0.0
            signals.append(_Signal(
                "head_drop", "posture", severity,
                "Head drop sostenido respecto a la postura habitual", baseline_used,
            ))

    def _confidence(self, signals, unavailable, metrics, baseline):
        coverage = len(signals) / len(self.SIGNAL_NAMES)
        baseline_candidates = [signal for signal in signals if signal.name in {
            "perclos", "blink_duration", "blink_rate", "pitch_deviation"
        }]
        baseline_coverage = (
            sum(signal.baseline_used for signal in baseline_candidates) / len(baseline_candidates)
            if baseline_candidates else 0.0
        )
        observation = metrics.observation_duration_seconds
        observation_factor = (
            self._clamp(observation / self.config.minimum_observation_seconds, 0.0, 1.0)
            if self._valid_number(observation) else 0.0
        )
        return self._clamp(0.50 * coverage + 0.25 * baseline_coverage + 0.25 * observation_factor, 0.0, 1.0)

    @staticmethod
    def _valid_number(value) -> bool:
        return (not isinstance(value, bool) and isinstance(value, (int, float))
                and math.isfinite(value))

    @classmethod
    def _ramp(cls, value: float, low: float, high: float) -> float:
        if high <= low:
            return 0.0
        return cls._clamp((float(value) - low) / (high - low), 0.0, 1.0)

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))
