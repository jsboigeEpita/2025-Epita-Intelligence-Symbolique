"""#2993 — every call to ``is_modal_kb_consistent`` receives a LEGALISED KB.

The defect (R1075): the external modal lane sent the translated formulas
RAW to SPASS / Tweety. ``MlParser`` reads the OPENING lines of a belief base
as its signature section — a raw ``"\n".join(formulas)`` makes the first
formula parse as a sort declaration, and the whole KB fails to parse
(``Illegal characters in sort definition``). The lane returned ``None``
(degraded) on every NL-translated base — ``valid`` never materialised.

The fix substitutes :func:`build_modal_kb` (the one legaliser, #2471) for
the raw join. These witnesses capture what reaches
``ModalHandler.is_modal_kb_consistent`` and assert the KB starts with
``type(...)`` declarations and carries the legalised formulas.
"""

import asyncio
import json
from unittest import mock

import argumentation_analysis.core.jvm_setup as jvm_setup
from argumentation_analysis.orchestration import invoke_callables
from argumentation_analysis.plugins import tweety_logic_plugin as tlp


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _patch_jvm_available(monkeypatch):
    """The plugin's ``_check_jvm`` probe asks jpype directly — sidestep
    it for the witness by patching the module-level flag through the
    helper itself."""
    monkeypatch.setattr(tlp, "_check_jvm", lambda: True)


def _register_stub_spass(monkeypatch, tmp_path):
    """Make SPASS available the way production detects it (#2971)."""
    stub = tmp_path / "SPASS.exe"
    stub.write_bytes(b"")
    monkeypatch.setitem(jvm_setup.EXTERNAL_TOOL_PATHS, "spass", str(stub))


# ---------------------------------------------------------------------------
# _invoke_external_modal_solver — SPASS path
# ---------------------------------------------------------------------------


class TestExternalModalSolverSpassLegalises:
    """The SPASS branch feeds ``build_modal_kb(formulas)`` to MlParser."""

    def test_spass_path_receives_declarations_first(self, monkeypatch, tmp_path):
        _register_stub_spass(monkeypatch, tmp_path)

        captured = {}

        def _spy(kb):
            captured["kb"] = kb
            return (True, "ok")

        fake_initializer = mock.MagicMock()
        fake_handler = mock.MagicMock()
        fake_handler.is_modal_kb_consistent = _spy
        fake_handler_mod = mock.MagicMock(return_value=fake_handler)

        with mock.patch(
            "argumentation_analysis.agents.core.logic.tweety_initializer.ready_initializer",
            return_value=fake_initializer,
        ), mock.patch(
            "argumentation_analysis.agents.core.logic.modal_handler.ModalHandler",
            fake_handler_mod,
        ):
            result = _run(
                invoke_callables._invoke_external_modal_solver(
                    "ignored input text",
                    {
                        "phase_modal_output": {
                            "formulas": ["heavy_rain", "[](rain => wet)"]
                        }
                    },
                )
            )

        assert result["solver"] == "spass"
        kb = captured["kb"]
        # #2993 — declarations first (the legalisation gate).
        first_line = kb.splitlines()[0]
        assert first_line.startswith(
            "type("
        ), f"SPASS path received unlegalised KB: first line = {first_line!r}"
        # #2471 — the illegal identifier ``heavy_rain`` is renamed (no
        # underscores) so it can declare itself.
        assert "type(HeavyRain)" in kb
        # Declarations precede formulas.
        decl_idx = next(
            i for i, line in enumerate(kb.splitlines()) if line.startswith("type(")
        )
        formula_idx = next(
            i
            for i, line in enumerate(kb.splitlines())
            if "HeavyRain" in line and not line.startswith("type(")
        )
        assert decl_idx < formula_idx


# ---------------------------------------------------------------------------
# _invoke_external_modal_solver — Tweety fallback path
# ---------------------------------------------------------------------------


class TestExternalModalSolverTweetyFallbackLegalises:
    """The Tweety fallback (no SPASS registered) feeds ``build_modal_kb`` too."""

    def test_tweety_fallback_receives_declarations_first(self, monkeypatch):
        # Make sure SPASS is NOT registered so the function falls through to
        # the TweetyBridge path.
        monkeypatch.setitem(jvm_setup.EXTERNAL_TOOL_PATHS, "spass", "")

        captured = {}

        def _spy(queries, belief_set, logic_type="K"):
            captured["belief_set"] = belief_set
            captured["logic_type"] = logic_type
            return (True, "ok")

        with mock.patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge"
        ) as fake_bridge_cls:
            fake_bridge_cls.return_value.execute_modal_query = _spy
            result = _run(
                invoke_callables._invoke_external_modal_solver(
                    "ignored input text",
                    {
                        "phase_modal_output": {
                            "formulas": ["heavy_rain", "[](rain => wet)"]
                        }
                    },
                )
            )

        assert result["solver"] == "tweety"
        kb = captured["belief_set"]
        first_line = kb.splitlines()[0]
        # #2993 — Tweety fallback also legalises its KB before sending to
        # the bridge. Without build_modal_kb the first line is the raw
        # formula and MlParser rejects the sort definition.
        assert first_line.startswith(
            "type("
        ), f"Tweety fallback received unlegalised KB: first line = {first_line!r}"
        assert "type(HeavyRain)" in kb


# ---------------------------------------------------------------------------
# _invoke_external_modal_solver — no-translation guard
# ---------------------------------------------------------------------------


class TestExternalModalSolverNoTranslation:
    """When the modal phase produced no formulas the lane sends nothing."""

    def test_empty_formulas_returns_unavailable_no_translation(self):
        result = _run(
            invoke_callables._invoke_external_modal_solver(
                "raw prose — not a KB",
                {"phase_modal_output": {"formulas": []}},
            )
        )
        assert result["valid"] is None
        assert result["modal_status"] == "unavailable:no-translation"
        assert result["degraded"] is True
        assert "raw input text" in (result.get("message") or "")

    def test_no_formulas_never_reaches_a_solver(self, monkeypatch, tmp_path):
        """The pre-#2993 code fed ``[input_text]`` to the handler when the
        translation produced nothing — prose reached MlParser and the
        "unavailable" verdict was fabricated by a parse error instead of
        stated. The handler must never see a call."""
        _register_stub_spass(monkeypatch, tmp_path)

        fake_handler = mock.MagicMock()
        with mock.patch(
            "argumentation_analysis.agents.core.logic.tweety_initializer.ready_initializer",
            return_value=mock.MagicMock(),
        ), mock.patch(
            "argumentation_analysis.agents.core.logic.modal_handler.ModalHandler",
            return_value=fake_handler,
        ):
            result = _run(
                invoke_callables._invoke_external_modal_solver(
                    "raw prose — not a KB",
                    {"phase_modal_output": {"formulas": []}},
                )
            )

        assert result["modal_status"] == "unavailable:no-translation"
        fake_handler.is_modal_kb_consistent.assert_not_called()


# ---------------------------------------------------------------------------
# tweety_logic_plugin single-formula wrapper
# ---------------------------------------------------------------------------


class TestTweetyLogicPluginSingleFormulaLegalises:
    """The single-formula wrapper feeds ``build_modal_kb([formula])``."""

    def test_single_formula_receives_declarations(self, monkeypatch):
        _patch_jvm_available(monkeypatch)
        captured = {}

        def _spy(kb):
            captured["kb"] = kb
            return (True, "ok")

        fake_handler = mock.MagicMock()
        fake_handler.is_modal_kb_consistent = _spy
        fake_handler._resolve_active_solver_choice.return_value = mock.MagicMock(
            value="tweety"
        )
        fake_initializer = mock.MagicMock()

        with mock.patch(
            "argumentation_analysis.agents.core.logic.modal_handler.ModalHandler",
            return_value=fake_handler,
        ), mock.patch(
            "argumentation_analysis.plugins.tweety_logic_plugin._ready_initializer",
            return_value=fake_initializer,
        ):
            payload = json.dumps({"formula": "heavy_rain", "logic_type": "modal"})
            # The kernel function is sync — the previous test wrapped it in
            # ``_run`` (asyncio) and tripped "An asyncio.Future, a coroutine
            # or an awaitable is required". The plugin returns JSON text
            # directly.
            tlp.TweetyLogicPlugin().check_modal_satisfiability(payload)

        kb = captured["kb"]
        first_line = kb.splitlines()[0]
        # #2993 — single-formula KB is also legalised (declarations first).
        assert first_line.startswith(
            "type("
        ), f"single-formula plugin sent unlegalised KB: first line = {first_line!r}"
        assert "type(HeavyRain)" in kb


# ---------------------------------------------------------------------------
# ModalLogicAgent.validate_argument — the temporary KB {premises, ¬conclusion}
# ---------------------------------------------------------------------------


class TestValidateArgumentBuildsLegalKb:
    """``validate_argument`` builds its KB through ``build_modal_kb``.

    The pre-#2993 inline loop declared ``type(implies)`` for keyword
    connectives, missed uppercase-initial atoms (regex anchored ``[a-z_]``)
    and emitted illegal ``type(heavy_rain)`` identifiers — the KB only ever
    parsed through ModalHandler's parse-point normaliser, and a KB with an
    uppercase atom was never decided at all."""

    @staticmethod
    def _agent_with_spy(spy):
        from argumentation_analysis.agents.core.logic.modal_logic_agent import (
            ModalLogicAgent,
        )

        agent = ModalLogicAgent.__new__(ModalLogicAgent)
        fake_bridge = mock.MagicMock()
        fake_bridge.modal_handler.is_modal_kb_consistent = spy
        object.__setattr__(agent, "_tweety_bridge", fake_bridge)
        return agent

    def test_kb_declares_legalised_atoms_and_no_keywords(self):
        captured = {}

        def _spy(kb):
            captured["kb"] = kb
            # "inconsistent" → the argument IS valid (returns True).
            return (False, "inconsistent")

        agent = self._agent_with_spy(_spy)
        result = _run(
            agent.validate_argument(
                ["[](heavy_rain => wet_road)", "heavy_rain", "[]Wet"],
                "flood_risk",
            )
        )

        assert result is True  # not is_consistent — the #2447 contract
        kb = captured["kb"]
        # Legalised identifiers, not the illegal underscored originals.
        assert "type(HeavyRain)" in kb
        assert "type(WetRoad)" in kb
        assert "type(FloodRisk)" in kb
        assert "type(heavy_rain)" not in kb
        # Reserved connective words are never declared as atoms.
        assert "type(implies)" not in kb
        assert "type(and)" not in kb
        # The negated conclusion rides along.
        assert "!(FloodRisk)" in kb
        # Declarations precede the formulas.
        lines = kb.splitlines()
        decl_idx = max(i for i, line in enumerate(lines) if line.startswith("type("))
        assert all(
            not (line and not line.startswith("type("))
            for line in lines[: decl_idx + 1]
        ), f"formula line before declarations: {lines[: decl_idx + 1]}"

    def test_uppercase_atom_is_declared(self):
        """An uppercase-initial atom (missed by the old ``[a-z_]`` regex) is
        declared by the legaliser's atom pattern."""

        captured = {}

        def _spy(kb):
            captured["kb"] = kb
            return (True, "consistent")

        agent = self._agent_with_spy(_spy)
        result = _run(agent.validate_argument(["[]Wet"], "Dry"))
        assert result is False  # consistent {premises, ¬conclusion} → invalid
        assert "type(Wet)" in captured["kb"]
        assert "type(Dry)" in captured["kb"]

    def test_undecided_kb_raises(self):
        """#2447 regression guard: a ``None`` verdict raises instead of being
        coerced — true before and after #2993."""

        agent = self._agent_with_spy(lambda kb: (None, "no verdict"))
        import pytest

        with pytest.raises(RuntimeError, match="n'a pas décidé"):
            _run(agent.validate_argument(["p"], "q"))
