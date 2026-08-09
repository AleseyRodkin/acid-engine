import pytest
from examples.information_aggregator.pipeline import AggregatorPipeline
from examples.information_aggregator.profiles.sports.sports_profile import create_sports_profile


def test_aggregator_with_sports_profile():
    profile = create_sports_profile()
    agg = AggregatorPipeline(profile)
    result = agg.run()
    assert result["status"] == "completed"
    assert len(result["steps"]) == 5   # источники, нормализация, сохранение, наблюдение, анализ