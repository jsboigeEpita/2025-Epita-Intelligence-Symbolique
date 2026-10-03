"""#2912 — witnesses: the seven off-pipeline unbounded reads are bounded.

The #2908 census entered seven whole-document reads as named debt "OFF the
pipeline path"; #2912's reachability table (issue comment) showed five of
them sit on ACTIVE entry points — the API's ``POST /workflow/custom``
reaches the conversational and hierarchical modes with arbitrary-length
text (``CustomWorkflowRequest.text`` has no length constraint), the Tkinter
UI and a script reach ``AnalysisRunnerV2``, and the demos plus the
hierarchical path reach the concrete informal agent. The pre-fix failure
shape, measured offline (fake services, 500k-char prose): SILENCE — the
whole text rides the prompt/payload, no error, no warning, nothing in
state.

Every site now interpolates a ``selected_text(...)`` call (#1737 shared
selector) at an existing bound — the wide-net's 8000, or the self-hosted
tier's file-local 3000 (its sibling LLM tier of the same file already read
3000). Witnesses are BEHAVIORAL (captured prompt size), per the
coordinator's measured point that the name-reading census cannot see an
alias: each test captures what the fake service/agent/kernel actually
receives and asserts the text part is exactly the bound for an over-bound
input — and byte-identical to the legacy unbounded construction at or
under the bound (the replay-band safety property).

Offline by construction: fake services and stub agents; no network, no key.
"""

import asyncio
import unittest.mock as um
from types import SimpleNamespace

from semantic_kernel.contents import ChatHistory

BOUND = 8000  # the wide-net's own window (fallacy_workflow_plugin line 617)
SELF_HOSTED_BOUND = 3000  # the same file's sibling LLM tier bound (line ~1391)

# Punctuated French prose: ~4 sub-clause marks per 100 chars — far above the
# #1737 selector's threshold, so every stride segment passes and the
# selection stays at offset 0 (the non-regression geometry).
_SENTENCE = (
    "Selon le rapport, il est clair que, malgré les efforts, la décision "
    "reste, en réalité, contestable: le débat continue. "
)


def _prose(length: int) -> str:
    text = ""
    while len(text) < length:
        text += _SENTENCE
    return text[:length]


# ─── row 1: SelfHostedLLMFallacyDetector.detect_async (httpx payload) ─────


class _FakeHttpxResp:
    def raise_for_status(self):
        pass

    def json(self):
        return {"fallacies": []}


class _FakeHttpxClient:
    def __init__(self, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        self.payload = json
        return _FakeHttpxResp()


def _self_hosted_payload(text: str) -> str:
    from argumentation_analysis.adapters.french_fallacy_adapter import (
        SelfHostedLLMFallacyDetector,
    )

    client = _FakeHttpxClient()
    with um.patch("httpx.AsyncClient", lambda **kw: client):
        det = SelfHostedLLMFallacyDetector(
            endpoint="http://fake", api_key="k", model="m"
        )
        asyncio.run(det.detect_async(text))
    return client.payload["messages"][1]["content"]


def _legacy_self_hosted_prompt(text: str) -> str:
    from argumentation_analysis.adapters.french_fallacy_adapter import (
        FALLACY_LABELS_FR,
    )

    return (
        "Tu es un expert en logique et argumentation. "
        "Analyse le texte suivant et identifie les sophismes.\n\n"
        "Pour chaque sophisme détecté, donne le type exact parmi:\n"
        + "\n".join(f"- {label}" for label in FALLACY_LABELS_FR[:15])
        + "\n\nRéponds UNIQUEMENT en JSON:\n"
        '{"fallacies": [{"type": "...", "confidence": 0.XX, "explanation": "..."}]}\n'
        'Si aucun sophisme: {"fallacies": []}\n\n'
        f"Texte à analyser:\n{text}"
    )


def test_row1_self_hosted_tier_payload_is_bounded_at_3000():
    payload = _self_hosted_payload(_prose(10_000))
    section = payload.split("Texte à analyser:\n", 1)[1]
    assert len(section) == SELF_HOSTED_BOUND
    assert section == _prose(10_000)[:SELF_HOSTED_BOUND]


def test_row1_self_hosted_payload_byte_identical_under_the_bound():
    text = _prose(2_500)
    assert _self_hosted_payload(text) == _legacy_self_hosted_prompt(text)


# ─── row 2: InformalFallacyAgent.invoke_single (kernel prompt) ────────────


def _invoke_single_prompt(text: str) -> str:
    from argumentation_analysis.agents.concrete_agents.informal_fallacy_agent import (
        InformalFallacyAgent,
    )

    cap = {}

    async def _fake_invoke_prompt(prompt=None, **kw):
        cap["prompt"] = prompt
        return "[]"

    stub = SimpleNamespace(
        system_prompt="SYS", kernel=SimpleNamespace(invoke_prompt=_fake_invoke_prompt)
    )
    asyncio.run(InformalFallacyAgent.invoke_single(stub, text_to_analyze=text))
    return cap["prompt"]


def test_row2_concrete_agent_prompt_is_bounded_at_8000():
    prompt = _invoke_single_prompt(_prose(10_000))
    section = prompt.split('Texte à analyser:\n"""\n', 1)[1].split('\n"""', 1)[0]
    assert len(section) == BOUND
    assert section == _prose(10_000)[:BOUND]


def test_row2_concrete_agent_prompt_byte_identical_under_the_bound():
    text = _prose(7_000)
    assert _invoke_single_prompt(text) == f'SYS\n\nTexte à analyser:\n"""\n{text}\n"""'


def test_row2_invoke_path_passes_a_chat_history_legacy_bytes_survive():
    # BaseAgent.invoke (agent_bases.py:227) forwards its ChatHistory argument
    # into invoke_single's text_to_analyze slot — the band's authentic tests
    # ride exactly that path (measured: run 37129976306). The legacy f-string
    # embedded str(history); the window must reproduce those bytes rather than
    # call .strip() on the object (the pre-fix AttributeError).
    history = ChatHistory()
    history.add_user_message("Analyse ce texte: les experts affirment, croyez-nous.")
    prompt = _invoke_single_prompt(history)
    assert prompt == f'SYS\n\nTexte à analyser:\n"""\n{str(history)}\n"""'


def test_row2_invoke_path_chat_history_is_bounded_at_8000():
    history = ChatHistory()
    history.add_user_message(_prose(10_000))
    prompt = _invoke_single_prompt(history)
    section = prompt.split('Texte à analyser:\n"""\n', 1)[1].split('\n"""', 1)[0]
    assert len(section) == BOUND
    assert section == str(history)[:BOUND]


# ─── rows 4+5: run_conversational_analysis extraction prompt (FR + DE) ────


def _extraction_prompts(text: str, lang: str):
    import argumentation_analysis.orchestration.conversational_orchestrator as co

    cap = []

    async def _cap_run_phase(agents, initial_prompt, **kw):
        cap.append(initial_prompt)
        return []

    class _FakeAgent:
        def __init__(self):
            self.name = "ProjectManager"

    with um.patch.object(
        co, "_build_conversational_kernel", lambda *a, **k: object()
    ), um.patch.object(
        co, "create_conversational_agents", lambda *a, **k: [_FakeAgent()]
    ), um.patch.object(
        co, "_detect_language", lambda t: lang
    ), um.patch.object(
        co, "_run_phase", _cap_run_phase
    ), um.patch.object(
        co,
        "_run_parent_harness_fallback",
        lambda *a, **k: asyncio.sleep(0, result=None),
    ), um.patch.object(
        co, "_resolve_phase_conflicts", lambda *a, **k: asyncio.sleep(0, result=[])
    ), um.patch.object(
        co, "_retract_fallacious_beliefs", lambda *a, **k: []
    ):
        asyncio.run(
            co.run_conversational_analysis(
                text=text,
                spectacular=False,
                max_total_turns=1,
                extraction_max_turns=1,
                agent_names=["ProjectManager"],
            )
        )
    return cap[0]


def _legacy_extraction_prompt(text: str, lang: str) -> str:
    base = (
        "Analysez ce texte argumentatif. Identifiez les arguments, "
        f"claims et sophismes.\n\nTexte:\n{text}"
    )
    if lang == "de":
        base = (
            "Analysez ce texte argumentatif. Identifiez les arguments, "
            "claims et sophismes.\n\n"
            "IMPORTANT : Le texte est en allemand. Pour la detection de sophismes "
            "(InformalAgent), traduisez mentalement les passages en anglais avant "
            "d'appliquer la taxonomie de sophismes. Pour les citations textuelles, "
            "conservez IMPERATIVEMENT le texte original allemand — ne traduisez "
            "jamais les citations. Les arguments doivent etre extraits en anglais "
            f"avec citations en allemand.\n\nTexte:\n{text}"
        )
    return base


def test_rows45_extraction_prompt_is_bounded_at_8000_both_variants():
    for lang in ("fr", "de"):
        prompt = _extraction_prompts(_prose(10_000), lang)
        section = prompt.split("Texte:\n", 1)[1]
        assert len(section) == BOUND, f"{lang}: extraction prompt text is unbounded"
        assert section == _prose(10_000)[:BOUND]


def test_rows45_extraction_prompt_byte_identical_under_the_bound():
    for lang in ("fr", "de"):
        text = _prose(7_000)
        assert _extraction_prompts(text, lang) == _legacy_extraction_prompt(
            text, lang
        ), f"{lang}: at/under the bound the prompt must be byte-identical"


# ─── row 3: AnalysisRunnerV2 Phase-1 PM prompt (chat history) ─────────────


def _phase1_prompt(text: str) -> str:
    import logging

    import argumentation_analysis.orchestration.analysis_runner_v2 as arv

    runner = arv.AnalysisRunnerV2.__new__(arv.AnalysisRunnerV2)
    runner.phase_counter = 0
    runner.chat_history = ChatHistory()
    runner.shared_state = SimpleNamespace(raw_text=text)
    runner.logger = logging.getLogger("probe2912")

    async def _cap_exec(*args, **kwargs):
        return []

    with um.patch.object(
        arv, "start_pm_orchestration_phase", lambda **kw: None
    ), um.patch.object(arv.AnalysisRunnerV2, "_execute_conversation_phase", _cap_exec):
        asyncio.run(runner._run_phase_1_informal_analysis())
    return str(runner.chat_history.messages[-1].content)


def test_row3_runner_v2_phase1_prompt_is_bounded_at_8000():
    prompt = _phase1_prompt(_prose(10_000))
    section = prompt.split("\n\n---\n", 1)[1].rsplit("\n---", 1)[0]
    assert len(section) == BOUND
    assert section == _prose(10_000)[:BOUND]


def test_row3_runner_v2_phase1_prompt_byte_identical_under_the_bound():
    text = _prose(7_000)
    assert _phase1_prompt(text) == (
        "Phase 1: Analyse informelle. PM, veuillez initier l'analyse du texte "
        f"suivant:\n\n---\n{text}\n---"
    )


# ─── row 6: InformalAgentAdapter.process_task (agent prompt) ──────────────


def _adapter_prompt(text: str) -> str:
    from argumentation_analysis.orchestration.hierarchical.operational.adapters.informal_agent_adapter import (
        InformalAgentAdapter,
    )

    cap = {}

    class _FakeResp:
        value = "analysis result"

    class _FakeAgent:
        name = "InformalAgent"

        async def invoke(self, prompt):
            cap["prompt"] = prompt
            yield _FakeResp()

    adapter = InformalAgentAdapter()
    adapter.agent = _FakeAgent()
    adapter.initialized = True
    asyncio.run(
        adapter.process_task(
            {
                "id": "t1",
                "required_capabilities": ["fallacy_detection"],
                "text_extracts": [
                    {"content": text[: len(text) // 2]},
                    {"content": text[len(text) // 2 :]},
                ],
            }
        )
    )
    return cap["prompt"]


def test_row6_hierarchical_adapter_prompt_is_bounded_at_8000():
    text = _prose(10_000)
    prompt = _adapter_prompt(text)
    section = prompt.rsplit("'", 1)[0].split("fallacies: '", 1)[1]
    assert len(section) == BOUND
    # The adapter joins the extracts with a single space — the window is a
    # prefix of THAT joined text, not of the original halves.
    joined = " ".join([text[: len(text) // 2], text[len(text) // 2 :]])
    assert section == joined[:BOUND]


def test_row6_hierarchical_adapter_prompt_byte_identical_under_the_bound():
    text = _prose(7_000)
    joined = " ".join([text[: len(text) // 2], text[len(text) // 2 :]])
    assert (
        _adapter_prompt(text) == f"Analyze the following text for fallacies: '{joined}'"
    )


# ─── row 7: verify_extracts_with_llm.evaluate_extract (agent prompt) ──────


def _evaluation_prompt(text: str) -> str:
    from argumentation_analysis.utils.extract_repair.verify_extracts_with_llm import (
        evaluate_extract,
    )

    cap = {}

    class _FakeEvalAgent:
        async def invoke(self, prompt):
            cap["prompt"] = prompt
            yield SimpleNamespace(
                content='{"valid": true, "coherence": 5, "relevance": 5, '
                '"integrity": 5, "comments": "x"}'
            )

    asyncio.run(
        evaluate_extract(
            _FakeEvalAgent(),
            {"source_name": "src0"},
            {"extract_name": "ext0", "extract_subject": "sujet"},
            text,
        )
    )
    return cap["prompt"]


def test_row7_extract_evaluation_prompt_is_bounded_at_8000():
    prompt = _evaluation_prompt(_prose(10_000))
    section = prompt.split("TEXTE EXTRAIT:\n    ", 1)[1].split(
        "\n    \n    Analysez", 1
    )[0]
    assert len(section) == BOUND
    assert section == _prose(10_000)[:BOUND]


def test_row7_extract_evaluation_prompt_byte_identical_under_the_bound():
    text = _prose(7_000)
    # The legacy template, rebuilt verbatim from the pre-#2912 source — the
    # blank template lines carry their four trailing spaces.
    legacy = (
        "\n"
        "    Évaluez la qualité de cet extrait de texte.\n"
        "    \n"
        "    SOURCE: src0\n"
        "    EXTRAIT: ext0\n"
        "    SUJET: sujet\n"
        "    \n"
        "    TEXTE EXTRAIT:\n"
        f"    {text}\n"
        "    \n"
        "    Analysez cet extrait selon les critères suivants:\n"
        "    1. Cohérence interne: l'extrait a-t-il un sens complet?\n"
        "    2. Pertinence: l'extrait correspond-il au sujet indiqué?\n"
        "    3. Intégrité: l'extrait est-il complet ou semble-t-il tronqué?\n"
        "    \n"
        "    Répondez au format JSON avec les champs:\n"
        "    - valid: true/false (l'extrait est-il valide?)\n"
        "    - coherence: 1-5 (niveau de cohérence interne)\n"
        "    - relevance: 1-5 (niveau de pertinence par rapport au sujet)\n"
        "    - integrity: 1-5 (niveau d'intégrité de l'extrait)\n"
        "    - comments: commentaires sur l'extrait\n"
        "    "
    )
    assert _evaluation_prompt(text) == legacy
