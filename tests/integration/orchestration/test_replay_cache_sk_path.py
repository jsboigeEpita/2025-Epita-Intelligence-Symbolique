"""BO-3 #1473 PR2 DoD: the SK-NATIVE path is deterministic and replayed from
cache — proven firsthand, not asserted.

PR1 wired the DIRECT path (``_get_openai_client`` → ``_guarded_chat_completion``
→ ``cached_raw_chat_completion``), which every ``democratech`` phase uses
(including ``adversarial_debate`` — it calls ``_get_openai_client``, not the SK
service; that is why PR1's pipeline test already showed identical per-phase
output). PR2 wires the SK-NATIVE path: ``create_llm_service`` wraps its returned
service with ``CachedChatCompletion``, so SK-native calls
(``ChatCompletionAgent.invoke`` / ``AgentGroupChat.invoke`` — the conversational
& cluedo orchestration modes) are replayed from the same disk cache.

This test proves the property END-TO-END through a real SK kernel call
(``kernel.invoke`` on a prompt function — the same ``service.get_chat_message_contents``
path the agents use, confirmed in SK 1.40: ``ChatCompletionAgent._invoke_internal``
→ ``chat_completion_service.get_chat_message_contents``):

  #1 (determinism firsthand): record a call → replay the SAME call → the live
     ``AsyncCompletions.create`` is invoked 0 times on replay and the response is
     IDENTICAL.
  #2 (fail-loud on miss): a replay call with an UNSEEN prompt raises and makes 0
     live call (never a silent live fallback — anti-théâtre #1019).

Privacy HARD: synthetic probe strings only — no corpus, no real names. Marked
``requires_api``+``slow``: the record leg needs a real LLM.
"""

import pytest


@pytest.fixture
def _counting_create(monkeypatch):
    """Patch ``AsyncCompletions.create`` at the class level to count live calls.

    SK's OpenAI handler calls ``self.client.chat.completions.create(...)`` (open_ai
    handler L88); patching the class intercepts every AsyncOpenAI instance in the
    process for the duration of the test (restored on teardown).
    """
    from openai.resources.chat.completions import AsyncCompletions

    live = {"n": 0}
    original = AsyncCompletions.create

    async def _counting(self, *args, **kwargs):
        live["n"] += 1
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(AsyncCompletions, "create", _counting)
    return live


@pytest.mark.requires_api
@pytest.mark.slow
class TestReplayCacheSKPath:
    """DoD: SK-native kernel call record → replay → 0 live call + identical."""

    @pytest.mark.asyncio
    async def test_sk_path_record_then_replay_zero_live_call(
        self, tmp_path, monkeypatch, _counting_create
    ):
        # Point the SK cache at a tmp dir. CachedChatCompletion reads the
        # module-global CACHE_DIR at construction, so patch it (create_llm_service
        # does not pass cache_dir explicitly).
        from argumentation_analysis.services import llm_cache as lc

        monkeypatch.setattr(lc, "CACHE_DIR", tmp_path / "sk_cache")
        monkeypatch.setenv("LLM_CACHE_MODE", "record")
        lc.reset_raw_cache()

        from semantic_kernel.functions import KernelArguments
        from semantic_kernel.kernel import Kernel

        from argumentation_analysis.core.llm_service import create_llm_service

        PROMPT = (
            "Respond with EXACTLY this token and nothing else: SK_PROBE_OK\n\n"
            "Context: {{$input}}"
        )
        INPUT = "deterministic-cache-probe"

        def _build_kernel():
            kernel = Kernel()
            svc = create_llm_service(service_id="sk_probe", force_authentic=True)
            kernel.add_service(svc)
            kernel.add_function(
                function_name="probe",
                plugin_name="probe",
                prompt=PROMPT,
            )
            return kernel

        def _invoke(kernel):
            return kernel.invoke(
                kernel.get_function("probe", "probe"),
                KernelArguments(input=INPUT),
            )

        # --- RECORD leg ---
        record_kernel = _build_kernel()
        record_result = await _invoke(record_kernel)
        record_text = str(record_result).strip()
        assert record_text, "record leg produced an empty response"
        assert _counting_create["n"] >= 1, (
            "record leg made 0 live API calls — the SK path did not reach the API"
        )
        record_live = _counting_create["n"]

        # --- REPLAY leg (same input → same cache key → 0 live call) ---
        monkeypatch.setenv("LLM_CACHE_MODE", "replay")
        _counting_create["n"] = 0
        replay_kernel = _build_kernel()
        replay_result = await _invoke(replay_kernel)
        replay_text = str(replay_result).strip()

        assert _counting_create["n"] == 0, (
            f"replay made {_counting_create['n']} live API call(s) — the cache "
            "did NOT intercept the SK-native path (anti-théâtre #1019: a silent "
            "live fallback is exactly the theater this test forbids)"
        )
        assert replay_text == record_text, (
            f"replay diverged from record (record={record_text!r}, "
            f"replay={replay_text!r}) — cache returned a different response"
        )
        # sanity: the record leg did hit the API (else the 0-on-replay is trivial)
        assert record_live >= 1

    @pytest.mark.asyncio
    async def test_sk_path_replay_miss_fails_loud(
        self, tmp_path, monkeypatch, _counting_create
    ):
        """DoD #2: an unseen prompt in replay raises and makes 0 live call."""
        from argumentation_analysis.services import llm_cache as lc

        monkeypatch.setattr(lc, "CACHE_DIR", tmp_path / "sk_cache_miss")
        monkeypatch.setenv("LLM_CACHE_MODE", "replay")
        lc.reset_raw_cache()

        from semantic_kernel.functions import KernelArguments
        from semantic_kernel.kernel import Kernel

        from argumentation_analysis.core.llm_service import create_llm_service

        kernel = Kernel()
        svc = create_llm_service(service_id="sk_probe", force_authentic=True)
        kernel.add_service(svc)
        kernel.add_function(
            function_name="probe",
            plugin_name="probe",
            prompt="Respond with EXACTLY this token: MISS_PROBE\n\nInput: {{$input}}",
        )

        _counting_create["n"] = 0
        # An unseen prompt in replay must NOT silently call the API.
        with pytest.raises(Exception):  # LLMCacheMiss, possibly SK-wrapped
            await kernel.invoke(
                kernel.get_function("probe", "probe"),
                KernelArguments(input="never-seen-before-miss-probe"),
            )
        assert _counting_create["n"] == 0, (
            "replay miss silently called the API — must fail-loud instead "
            "(anti-théâtre #1019)"
        )
