"""#3095 — the run prices its own tokens, and never calls a provider 0 "free".

Born-red on main at issue-filing time: the usage line summed only the
provider-reported ``usage.cost``. On the BYOK route every call reports 0, so a
0.415 $ pass printed ``cost: $0.0000``; on a provider that reports no cost at
all, nothing was priced. The run's price must come from one dated table of
per-MTok prices applied to the tokens the run measured, with the
provider-reported figure kept apart and the BYOK zero labelled.

Synthetic fakes only: no network, no key, zero spend. Opaque ids only.
"""

import importlib.util
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from argumentation_analysis.services.model_prices import (
    PRICE_TABLE,
    PRICES_READ_ON,
    price_tokens,
)

_SCRIPT = (
    Path(__file__).resolve().parents[4] / "scripts" / "dataset" / "run_corpus_batch.py"
)


def _load_renderer():
    spec = importlib.util.spec_from_file_location("run_corpus_batch_3095", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_response(prompt_tokens, completion_tokens, cost=None):
    """Duck-typed OpenAI ChatCompletion; ``cost`` only when the provider sends one."""
    usage = types.SimpleNamespace(
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
    )
    if cost is not None:
        usage.cost = cost
    choice = types.SimpleNamespace(message=types.SimpleNamespace(content="réponse"))
    return types.SimpleNamespace(usage=usage, choices=[choice])


def _sync_client(response):
    client = types.SimpleNamespace()
    client.chat = types.SimpleNamespace(
        completions=types.SimpleNamespace(create=MagicMock(return_value=response))
    )
    return client


@pytest.fixture()
def usage_counter(monkeypatch):
    monkeypatch.setenv("LLM_CACHE_MODE", "off")
    from argumentation_analysis.services import llm_cache

    llm_cache._raw_cache = None
    llm_cache.reset_usage_stats()
    yield llm_cache.get_usage_stats
    llm_cache.reset_usage_stats()


def _run_sync_calls(model, calls, cost=None):
    """Drive N sync live calls through the raw accounting point."""
    from argumentation_analysis.services.llm_cache import (
        cached_raw_chat_completion_sync,
    )

    for prompt, completion in calls:
        cached_raw_chat_completion_sync(
            _sync_client(_fake_response(prompt, completion, cost=cost)),
            model=model,
            messages=[{"role": "user", "content": "q"}],
        )


class TestTokensArePricedFromTheTable:
    def test_a_haiku_run_is_priced_from_the_table(self, usage_counter):
        """The born-red shape: a synthetic N-call Haiku run with known tokens
        must print the table's price — main printed $0.0000 or nothing."""
        # 2 × (30k in, 1k out) = 60k in, 2k out → 60k×0.10 + 2k×0.50 = $0.0070.
        _run_sync_calls("claude-haiku-5-5", [(30_000, 1_000), (30_000, 1_000)])
        stats = usage_counter()
        assert stats["computed_cost_usd"] == pytest.approx(0.0070)
        line = _load_renderer().render_usage_line(stats)
        assert "$0.0070" in line, (
            "the run's cost must be computed from its own tokens — the R1101 "
            "defect printed $0.0000 for a 0.415 $ pass"
        )
        assert "price table" in line, "the line must name the table it priced with"
        assert "in 1 phase(s)" in line, (
            "the run-level cost fields are not phases — the phase count must "
            "not be inflated by the accounting's own metadata keys"
        )

    def test_the_long_prompt_tier_is_its_own_row(self, usage_counter):
        """Haiku 5.5 bills a >100k prompt at the long-context tier — a separate
        row, never an average: 150k in + 2k out = $0.0800 (the standard row
        would give $0.0160)."""
        _run_sync_calls("claude-haiku-5-5", [(150_000, 2_000)])
        stats = usage_counter()
        assert stats["computed_cost_usd"] == pytest.approx(0.0800)
        haiku_rows = [r for r in PRICE_TABLE if r.model_id == "claude-haiku-5-5"]
        assert (
            len(haiku_rows) == 2
        ), "the long-prompt tier is a separate row, not an average of the two"
        assert {r.prompt_threshold_tokens for r in haiku_rows} == {0, 100_000}

    def test_every_row_cites_a_source_and_a_date(self):
        """One dated table: no row may be added without the page it was read
        from and the day it was read."""
        assert PRICE_TABLE, "the run path needs a price table"
        for row in PRICE_TABLE:
            assert row.source.strip(), f"{row.model_id}: row without a source page"
            assert (
                row.read_on == PRICES_READ_ON
            ), f"{row.model_id}: row must carry the table's read date"
        assert len(PRICES_READ_ON) == 10 and PRICES_READ_ON[4] == "-"

    def test_an_unknown_model_suffix_does_not_borrow_a_price(self):
        assert price_tokens("claude-haiku-5-5-20990101", 1_000, 1_000) is None


class TestProviderReportedCostIsKeptApart:
    def test_byok_zero_is_labelled_and_is_not_the_run_cost(self, usage_counter):
        """The measured BYOK shape: every call reports cost 0. The line shows
        the computed price AND labels the reported 0 — never $0.0000 alone."""
        _run_sync_calls(
            "claude-haiku-5-5",
            [(30_000, 1_000), (30_000, 1_000)],
            cost=0.0,
        )
        stats = usage_counter()
        assert stats["cost_usd"] == 0.0, "the reported figure is kept as reported"
        assert stats["computed_cost_usd"] == pytest.approx(0.0070)
        line = _load_renderer().render_usage_line(stats)
        assert "$0.0070" in line
        assert "provider-reported: $0.0000" in line
        assert "BYOK" in line, (
            "a reported 0 must be named as the BYOK shape — showing it as the "
            "run's cost is the #3095 defect"
        )

    def test_an_unknown_model_is_not_priced_never_zero(self, usage_counter):
        """No table row → the line says 'not priced: <id>'; it never prints
        $0.0000, which is the lie the issue is about."""
        _run_sync_calls("mystery-model-9", [(10_000, 500)])
        stats = usage_counter()
        assert stats["computed_cost_usd"] is None
        line = _load_renderer().render_usage_line(stats)
        assert "not priced" in line
        assert "mystery-model-9" in line
        assert "$0.0000" not in line

    def test_a_missing_provider_cost_stays_unreported(self, usage_counter):
        """A provider that sends no cost field: the line says nothing was
        reported — the computed price still stands on its own."""
        _run_sync_calls("claude-haiku-5-5", [(30_000, 1_000)])
        line = _load_renderer().render_usage_line(usage_counter())
        assert "$0.0035" in line
        assert "provider-reported" not in line or "not reported" in line
