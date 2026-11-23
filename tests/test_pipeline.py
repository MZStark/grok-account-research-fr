"""Offline tests: the Grok API is replaced by fakes, no network, no key."""

import json

import pytest

from agents.outreach import count_words, write_outreach
from agents.use_cases import derive_use_cases
from core.config import ConfigError, Settings
from core.llm import GrokAPIError, GrokClient, LLMResult
from agents.research import research
from core.pipeline import dedupe_citations, run

SETTINGS = Settings(xai_api_key="test", model="grok-test", max_retries=3)

CASES = {
    "cas_usage": [
        {"titre": f"Cas {i}", "equipe": "Support", "probleme": "p", "benefice": "b", "signal": "s"}
        for i in range(1, 4)
    ]
}


class FakeLLM:
    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = []

    def complete(self, system, user, *, web_search=False):
        self.calls.append({"user": user, "web_search": web_search})
        return LLMResult(text=self.answers.pop(0), sources=["https://example.com/a"] if web_search else [])


def test_full_pipeline_produces_the_three_sections():
    llm = FakeLLM(["## Fiche compte : Qonto\n**Activité** : banque pro.", json.dumps(CASES), "Objet : Bonjour\n\nCourt message ?"])
    report = run("Qonto", SETTINGS, llm=llm)
    assert "## Fiche compte : Qonto" in report
    assert report.count("### ") == 3
    assert "## Premier message de prospection" in report
    assert "https://example.com/a" in report
    assert llm.calls[0]["web_search"] is True  # step 1 uses Grok's web_search tool


def test_research_strips_narration_before_brief_heading():
    llm = FakeLLM(["Je vais chercher des sources.Je vérifie.## Fiche compte : Alan\n**Activité** : assurance."])
    brief = research("Alan", llm, SETTINGS)
    assert brief.markdown.startswith("## Fiche compte : Alan")


def test_research_keeps_text_when_heading_is_missing():
    llm = FakeLLM(["Pas de titre ici."])
    assert research("Alan", llm, SETTINGS).markdown == "Pas de titre ici."


def test_duplicate_adjacent_citations_are_collapsed():
    text = "Paris. [[1]](https://a.fr) [[1]](https://a.fr) [[7]](https://b.fr) [[1]](https://a.fr)"
    assert dedupe_citations(text) == "Paris. [[1]](https://a.fr) [[7]](https://b.fr) [[1]](https://a.fr)"


def test_use_cases_retry_on_invalid_json():
    llm = FakeLLM(["pas du json", json.dumps(CASES)])
    assert len(derive_use_cases("fiche", llm)) == 3
    assert len(llm.calls) == 2


def test_use_cases_fail_cleanly_when_still_invalid():
    with pytest.raises(GrokAPIError):
        derive_use_cases("fiche", FakeLLM(['{"cas_usage": []}', '{"cas_usage": []}']))


def test_outreach_is_shortened_when_too_long():
    long_msg = "mot " * 150
    llm = FakeLLM([long_msg, "Objet : Court\n\nBonjour, un échange de 20 minutes ?"])
    message = write_outreach("fiche", "cas", llm)
    assert count_words(message) < 120


def test_missing_key_gives_a_clear_error(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        Settings.from_env()


class Timeout(Exception):
    pass


Timeout.__name__ = "APITimeoutError"


class FlakyResponses:
    def __init__(self, failures):
        self.failures = failures
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls <= self.failures:
            raise Timeout("timeout")
        return type("R", (), {"output_text": "ok", "output": [], "citations": ["https://s.fr"]})()


class FakeOpenAI:
    def __init__(self, failures):
        self.responses = FlakyResponses(failures)


def test_client_retries_transient_errors():
    fake = FakeOpenAI(failures=2)
    out = GrokClient(SETTINGS, client=fake, sleep=lambda s: None).complete("s", "u", web_search=True)
    assert out.text == "ok" and out.sources == ["https://s.fr"]
    assert fake.responses.calls == 3


def test_client_gives_up_with_french_message():
    fake = FakeOpenAI(failures=10)
    with pytest.raises(GrokAPIError, match="ne répond pas"):
        GrokClient(SETTINGS, client=fake, sleep=lambda s: None).complete("s", "u")
