import pytest

from research.config import InvalidSettingError, MissingKeyError, get_settings

KEYS = {"MISTRAL_API_KEY": "m-key", "TAVILY_API_KEY": "t-key"}


def test_defaults_applied_when_only_keys_set():
    s = get_settings(KEYS)
    assert s.mistral_api_key == "m-key"
    assert s.tavily_api_key == "t-key"
    assert s.database_url is None
    assert s.writer_model == "mistral-medium-3-5"
    assert s.critic_model == "mistral-large-latest"
    assert (s.pass_score, s.max_revisions, s.time_budget_s) == (7, 2, 220)


@pytest.mark.parametrize("missing", ["MISTRAL_API_KEY", "TAVILY_API_KEY"])
def test_missing_key_error_names_the_variable(missing):
    env = {k: v for k, v in KEYS.items() if k != missing}
    with pytest.raises(MissingKeyError, match=missing) as exc:
        get_settings(env)
    assert exc.value.name == missing


def test_blank_key_counts_as_missing():
    with pytest.raises(MissingKeyError, match="TAVILY_API_KEY"):
        get_settings({**KEYS, "TAVILY_API_KEY": "   "})


def test_env_overrides_defaults():
    s = get_settings(
        {
            **KEYS,
            "PASS_SCORE": "9",
            "MAX_REVISIONS": "1",
            "TIME_BUDGET_S": "120",
            "WRITER_MODEL": "w",
            "CRITIC_MODEL": "c",
            "CLIENT_HASH_SALT": "pepper",
            "DATABASE_URL": "postgresql://x",
        }
    )
    assert (s.pass_score, s.max_revisions, s.time_budget_s) == (9, 1, 120)
    assert (s.writer_model, s.critic_model) == ("w", "c")
    assert s.client_hash_salt == "pepper"
    assert s.database_url == "postgresql://x"


def test_non_integer_score_is_rejected():
    with pytest.raises(InvalidSettingError, match="PASS_SCORE"):
        get_settings({**KEYS, "PASS_SCORE": "seven"})


def test_reads_process_env_by_default(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "from-env")
    monkeypatch.setenv("TAVILY_API_KEY", "from-env")
    monkeypatch.setenv("PASS_SCORE", "8")
    s = get_settings()
    assert s.mistral_api_key == "from-env"
    assert s.pass_score == 8
