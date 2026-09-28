from wellbeing.recommendations import (
    RecommendationCategory,
    RecommendationContext,
    WellbeingRecommendationService,
)


def test_selects_recommendations_from_context():
    service = WellbeingRecommendationService()
    result = service.select(
        RecommendationContext(break_active=True, break_duration_seconds=300),
        limit=2,
    )
    assert len(result) == 2
    assert all(item.text for item in result)
    assert all(
        item.category
        in {
            RecommendationCategory.VISUAL,
            RecommendationCategory.HANDS,
        }
        for item in result
    )


def test_active_break_has_recommendations():
    service = WellbeingRecommendationService()
    result = service.select(RecommendationContext(break_active=True), limit=2)
    assert 1 <= len(result) <= 2


def test_does_not_repeat_immediately_when_alternatives_exist():
    service = WellbeingRecommendationService()
    context = RecommendationContext()
    first = service.select(context)[0]
    second = service.select(context)[0]
    assert second.key != first.key


def test_service_has_no_advanced_fatigue_dependency():
    service = WellbeingRecommendationService()
    context_fields = set(RecommendationContext.__dataclass_fields__)
    assert context_fields == {
        "continuous_usage_seconds",
        "break_active",
        "break_duration_seconds",
        "completed_breaks",
        "postponed_breaks",
    }
    assert service.select(RecommendationContext())


def test_long_continuous_usage_prioritizes_movement():
    service = WellbeingRecommendationService()
    result = service.select(
        RecommendationContext(continuous_usage_seconds=60 * 60), limit=2
    )
    assert all(
        item.category == RecommendationCategory.MOVEMENT for item in result
    )


def test_basic_context_returns_valid_recommendation():
    service = WellbeingRecommendationService()
    result = service.select(RecommendationContext())
    assert len(result) == 1
    assert isinstance(result[0].category, RecommendationCategory)
    assert result[0].text.endswith(".")


def test_missing_context_is_safe():
    service = WellbeingRecommendationService()
    assert service.select(None)
