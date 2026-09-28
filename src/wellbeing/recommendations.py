from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app import config


class RecommendationCategory(Enum):
    VISUAL = "VISUAL"
    HANDS = "HANDS"
    SHOULDERS = "SHOULDERS"
    POSTURE = "POSTURE"
    MOVEMENT = "MOVEMENT"


@dataclass(frozen=True)
class WellbeingRecommendation:
    key: str
    category: RecommendationCategory
    text: str


@dataclass(frozen=True)
class RecommendationContext:
    continuous_usage_seconds: int = 0
    break_active: bool = False
    break_duration_seconds: int = 0
    completed_breaks: int = 0
    postponed_breaks: int = 0


RECOMMENDATIONS = (
    WellbeingRecommendation(
        "look_far", RecommendationCategory.VISUAL,
        "Mira a un punto lejano durante unos segundos.",
    ),
    WellbeingRecommendation(
        "rest_eyes", RecommendationCategory.VISUAL,
        "Aparta la vista de la pantalla y deja descansar los ojos.",
    ),
    WellbeingRecommendation(
        "relax_hands", RecommendationCategory.HANDS,
        "Relaja las manos y abre y cierra los dedos suavemente.",
    ),
    WellbeingRecommendation(
        "move_wrists", RecommendationCategory.HANDS,
        "Mueve suavemente las muñecas.",
    ),
    WellbeingRecommendation(
        "move_shoulders", RecommendationCategory.SHOULDERS,
        "Mueve los hombros con suavidad.",
    ),
    WellbeingRecommendation(
        "neck_shoulders", RecommendationCategory.SHOULDERS,
        "Haz un estiramiento suave de cuello y hombros.",
    ),
    WellbeingRecommendation(
        "change_posture", RecommendationCategory.POSTURE,
        "Cambia de postura y acomódate antes de continuar.",
    ),
    WellbeingRecommendation(
        "stand_up", RecommendationCategory.MOVEMENT,
        "Levántate un momento si te resulta posible.",
    ),
    WellbeingRecommendation(
        "short_walk", RecommendationCategory.MOVEMENT,
        "Camina brevemente para cambiar de posición.",
    ),
)


class WellbeingRecommendationService:
    """Selects brief self-care ideas using only time-based wellbeing context."""

    def __init__(self):
        self._last_keys: tuple[str, ...] = ()

    def select(
        self,
        context: Optional[RecommendationContext] = None,
        limit: int = 1,
    ) -> list[WellbeingRecommendation]:
        context = context or RecommendationContext()
        limit = max(1, min(limit, 2))
        candidates = self._prioritized_candidates(context)

        alternatives = [
            item for item in candidates if item.key not in self._last_keys
        ]
        if len(alternatives) >= limit:
            candidates = alternatives

        selected = candidates[:limit]
        self._last_keys = tuple(item.key for item in selected)
        return selected

    @staticmethod
    def _prioritized_candidates(
        context: RecommendationContext,
    ) -> list[WellbeingRecommendation]:
        long_usage = (
            context.continuous_usage_seconds
            >= config.RECOMMENDED_BREAK_INTERVAL_MINUTES * 60
        )
        postponed_often = context.postponed_breaks > context.completed_breaks

        if long_usage or postponed_often:
            priority = (
                RecommendationCategory.MOVEMENT,
                RecommendationCategory.VISUAL,
                RecommendationCategory.POSTURE,
                RecommendationCategory.SHOULDERS,
                RecommendationCategory.HANDS,
            )
        elif context.break_active and context.break_duration_seconds <= 5 * 60:
            priority = (
                RecommendationCategory.VISUAL,
                RecommendationCategory.HANDS,
                RecommendationCategory.SHOULDERS,
                RecommendationCategory.POSTURE,
                RecommendationCategory.MOVEMENT,
            )
        else:
            priority = tuple(RecommendationCategory)

        rank = {category: index for index, category in enumerate(priority)}
        return sorted(RECOMMENDATIONS, key=lambda item: rank[item.category])
