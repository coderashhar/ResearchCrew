from datetime import date

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable, RunnableLambda

from research.agents import build_chains, build_llms
from research.config import Settings
from research.schemas import Critique, SearchPlan, Source

SETTINGS = Settings(
    mistral_api_key="m", tavily_api_key="t", writer_model="w-model", critic_model="c-model"
)
PLAN = SearchPlan(queries=[{"query": "q", "topic": "general"}])
CRITIQUE = Critique(accuracy=8, coverage=8, citation_quality=8, clarity=8, recency=8, overall=8)


class FakeLLM(Runnable):
    """Chat model stand-in that records prompts and replays canned answers.

    A response that is an exception is raised, so retry behaviour is testable.
    """

    def __init__(self, *responses):
        self.responses = list(responses)
        self.prompts: list[str] = []

    def _next(self, prompt_value):
        self.prompts.append(prompt_value.to_string())
        answer = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(answer, Exception):
            raise answer
        return answer

    def invoke(self, input, config=None, **kwargs):
        return AIMessage(content=self._next(input))

    def with_structured_output(self, schema, **kwargs):
        return RunnableLambda(self._next)


def sources_block():
    return "[1] Title 1 (https://a.com)\nsource body"


def source(i=1):
    return Source(id=i, url="https://a.com", title="T", domain="a.com", content="body")


# --- planner --------------------------------------------------------------


def test_planner_prompt_carries_topic_and_today():
    llm = FakeLLM(PLAN)
    plan = build_chains(SETTINGS, writer_llm=llm, critic_llm=FakeLLM(CRITIQUE)).planner.invoke(
        {"topic": "mRNA vaccines"}
    )
    assert plan == PLAN
    prompt = llm.prompts[0]
    assert "mRNA vaccines" in prompt
    assert date.today().isoformat() in prompt
    assert "topic='general'" in prompt


# --- writer ---------------------------------------------------------------


def writer_prompt(**inputs):
    llm = FakeLLM("report [1]")
    chains = build_chains(SETTINGS, writer_llm=llm, critic_llm=FakeLLM(CRITIQUE))
    report = chains.writer.invoke({"topic": "T", "sources_block": sources_block(), **inputs})
    return report, llm.prompts[0]


def test_writer_gets_sources_and_citation_rules():
    report, prompt = writer_prompt()
    assert report == "report [1]"
    assert sources_block() in prompt
    assert "square brackets" in prompt
    assert "Do not write a Sources or References section" in prompt
    assert "untrusted data" in prompt


def test_first_draft_prompt_has_no_revision_block():
    _, prompt = writer_prompt()
    assert "PREVIOUS DRAFT" not in prompt
    assert "This is a revision" not in prompt


def test_revision_prompt_includes_previous_draft_and_critique():
    _, prompt = writer_prompt(previous_draft="draft one", critique_notes="- missing dates")
    assert "This is a revision" in prompt
    assert "draft one" in prompt
    assert "- missing dates" in prompt


# --- critic ---------------------------------------------------------------


def test_critic_sees_report_and_sources_and_returns_structured_scores():
    writer, critic = FakeLLM("unused"), FakeLLM(CRITIQUE)
    chains = build_chains(SETTINGS, writer_llm=writer, critic_llm=critic)
    result = chains.critic.invoke({"report": "the report [1]", "sources_block": sources_block()})
    assert result == CRITIQUE
    assert "the report [1]" in critic.prompts[0]
    assert sources_block() in critic.prompts[0]
    assert writer.prompts == [], "critic must not run on the writer model"


# --- retry and model wiring ----------------------------------------------


def test_transient_failure_is_retried():
    llm = FakeLLM(RuntimeError("503"), "report [1]")
    chains = build_chains(SETTINGS, writer_llm=llm, critic_llm=FakeLLM(CRITIQUE))
    assert chains.writer.invoke({"topic": "T", "sources_block": sources_block()}) == "report [1]"
    assert len(llm.prompts) == 2


def test_persistent_failure_gives_up_after_three_attempts():
    llm = FakeLLM(RuntimeError("503"))
    chains = build_chains(SETTINGS, writer_llm=llm, critic_llm=FakeLLM(CRITIQUE))
    with pytest.raises(RuntimeError):
        chains.writer.invoke({"topic": "T", "sources_block": sources_block()})
    assert len(llm.prompts) == 3


def test_build_llms_uses_configured_model_names():
    writer, critic = build_llms(SETTINGS)
    assert (writer.model, critic.model) == ("w-model", "c-model")
    assert writer.temperature == 0


def test_build_chains_defaults_to_configured_models():
    chains = build_chains(SETTINGS)
    assert chains.planner is not None and chains.critic is not None
