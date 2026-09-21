import pytest
from pydantic import ValidationError

from research.schemas import Critique, Draft, SearchPlan, SearchQuery, Source

RUBRIC = dict(accuracy=8, coverage=7, citation_quality=9, clarity=8, recency=6, overall=8)


def query(**kw):
    return {"query": "q", "topic": "general", **kw}


def test_critique_accepts_valid_scores_and_defaults_lists():
    c = Critique(**RUBRIC)
    assert c.overall == 8
    assert c.unsupported_claims == []
    assert c.needs_more_research is False


@pytest.mark.parametrize("bad", [0, 11])
@pytest.mark.parametrize("field", ["overall", "accuracy", "recency"])
def test_critique_rejects_scores_outside_1_to_10(field, bad):
    with pytest.raises(ValidationError):
        Critique(**{**RUBRIC, field: bad})


def test_critique_caps_followup_queries():
    with pytest.raises(ValidationError):
        Critique(**RUBRIC, followup_queries=["a", "b", "c", "d"])


@pytest.mark.parametrize("n", [0, 6])
def test_search_plan_rejects_zero_or_six_queries(n):
    with pytest.raises(ValidationError):
        SearchPlan(queries=[query()] * n)


def test_search_plan_accepts_one_to_five():
    assert len(SearchPlan(queries=[query()] * 5).queries) == 5


def test_topic_rejects_unknown_value():
    with pytest.raises(ValidationError):
        SearchQuery(**query(topic="sports"))


def test_days_optional_and_bounded():
    assert SearchQuery(**query()).days is None
    assert SearchQuery(**query(topic="news", days=30)).days == 30
    with pytest.raises(ValidationError):
        SearchQuery(**query(topic="news", days=0))


def test_source_id_starts_at_one():
    with pytest.raises(ValidationError):
        Source(id=0, url="u", title="t", domain="d", content="c")


def test_draft_round_trips_through_json():
    d = Draft(version=2, report="r [1]", critique=Critique(**RUBRIC))
    assert Draft.model_validate_json(d.model_dump_json()) == d
