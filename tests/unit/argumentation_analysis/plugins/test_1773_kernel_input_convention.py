"""#1773 — le canal formel ne peut pas rendre un verdict sans calcul.

Constats 1, 2 et 4 du dispatch (msg-20260816T095211-52twvk, amendé R819) :
les tests ci-dessous portent sur le VERDICT rendu, jamais sur le nom d'une
fonction. Ils sont rouges sur main d'aujourd'hui :

- constat 1 : la sonde JVM du plugin avalait l'AttributeError d'une sonde
  cassée (``bridge.is_jvm_ready``) via un ``except Exception`` nu —
  une sonde cassée doit lever, pas rendre « indisponible » ;
- constat 2 : la branche « pas de JVM » rendait ``True`` (« skipped
  validation ») — un verdict positif sans aucun calcul ;
- constat 4 : toute entrée non-objet-JSON levait AttributeError (liste,
  int) ou rendait une erreur mensongère sans nommer les clés (clé absente).
"""

import asyncio
import json

import pytest

import argumentation_analysis.plugins.kb_to_tweety_plugin as kb_plugin
from argumentation_analysis.plugins.kb_to_tweety_plugin import KBToTweetyPlugin


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _parsed(result: str):
    assert isinstance(result, str), "kernel_function must return a JSON string"
    return json.loads(result)


# ---------------------------------------------------------------------------
# Constat 1 — la sonde JVM : un probe cassé lève, seul l'indisponible rend False
# ---------------------------------------------------------------------------


class TestJvmProbeBrokenVsUnavailable:
    def test_broken_probe_raises(self, monkeypatch):
        """Une sonde cassée (AttributeError) doit PROPAGER, pas rendre False."""
        from argumentation_analysis.agents.core.logic import tweety_bridge as tb_mod

        class _BrokenBridge:
            @property
            def initializer(self):
                raise AttributeError("is_jvm_ready' has no attribute")

        monkeypatch.setattr(
            tb_mod.TweetyBridge,
            "get_instance",
            classmethod(lambda cls: _BrokenBridge()),
        )
        with pytest.raises(AttributeError):
            kb_plugin._jvm_available()

    def test_genuine_unavailability_returns_false(self, monkeypatch):
        from argumentation_analysis.agents.core.logic import tweety_bridge as tb_mod

        class _UninitializedBridge:
            @property
            def initializer(self):
                raise RuntimeError("JVM not started")

        monkeypatch.setattr(
            tb_mod.TweetyBridge,
            "get_instance",
            classmethod(lambda cls: _UninitializedBridge()),
        )
        assert kb_plugin._jvm_available() is False

    def test_ready_bridge_returns_true(self, monkeypatch):
        from argumentation_analysis.agents.core.logic import tweety_bridge as tb_mod

        class _ReadyInitializer:
            @staticmethod
            def is_jvm_ready():
                return True

        class _ReadyBridge:
            initializer = _ReadyInitializer()

        monkeypatch.setattr(
            tb_mod.TweetyBridge, "get_instance", classmethod(lambda cls: _ReadyBridge())
        )
        assert kb_plugin._jvm_available() is True


# ---------------------------------------------------------------------------
# Constat 2 — pas de JVM => pas de verdict positif
# ---------------------------------------------------------------------------


class TestNoJvmNoPositiveVerdict:
    @pytest.mark.parametrize(
        "validator",
        [
            kb_plugin._validate_pl,
            lambda f: kb_plugin._validate_fol(f),
            lambda f: kb_plugin._validate_modal(f),
        ],
        ids=["pl", "fol", "modal"],
    )
    def test_unavailable_jvm_renders_invalid(self, validator, monkeypatch):
        monkeypatch.setattr(kb_plugin, "_jvm_available", lambda: False)
        valid, msg = validator("p => q")
        assert valid is False, (
            "sans JVM le validateur doit rendre un verdict NEGATIF, "
            f"pas un verdict fabrique: ({valid}, {msg})"
        )
        assert "not performed" in msg

    def test_unavailable_jvm_renders_invalid_retry_loop(self, monkeypatch):
        """Le verdict remonte jusqu'a la reponse du plugin : is_valid False."""
        monkeypatch.setattr(kb_plugin, "_jvm_available", lambda: False)
        result = _parsed(
            _run(
                KBToTweetyPlugin().translate_to_tweety(
                    json.dumps({"text": "the butler did it", "logic_type": "pl"})
                )
            )
        )
        assert (
            result.get("is_valid") is False
        ), f"le canal formel a rendu un verdict positif sans JVM: {result}"


# ---------------------------------------------------------------------------
# Constat 4 — surface d'entree : erreur structuree qui nomme les cles
# (tests du helper lui-meme : tests/unit/argumentation_analysis/plugins/
#  test_kernel_input.py — fichier separe pour ne pas casser la collection
#  du present fichier lors du controle rouge sur main)
# ---------------------------------------------------------------------------


class TestEntryPointsStructuredErrors:
    """Les 5 @kernel_function : jamais d'exception, toujours une erreur nommee."""

    def test_translate_to_tweety_array_input(self):
        result = _parsed(_run(KBToTweetyPlugin().translate_to_tweety("[1, 2, 3]")))
        assert "error" in result
        assert result.get("received_type") == "list"

    def test_translate_to_tweety_int_input(self):
        result = _parsed(_run(KBToTweetyPlugin().translate_to_tweety(42)))
        assert "error" in result
        assert result.get("received_type") == "int"

    def test_translate_to_tweety_missing_text_names_keys(self):
        result = _parsed(
            _run(KBToTweetyPlugin().translate_to_tweety('{"logic_type": "pl"}'))
        )
        assert "error" in result
        assert "text" in result["error"]
        assert result.get("received_keys") == ["logic_type"]
        assert "text" in result.get("expected_keys", [])

    def test_translate_batch_missing_beliefs_names_keys(self):
        result = _parsed(
            _run(KBToTweetyPlugin().translate_batch_to_tweety('{"logic_type": "pl"}'))
        )
        assert "error" in result
        assert "beliefs" in result["error"]
        assert result.get("received_keys") == ["logic_type"]

    def test_translate_dung_array_input(self):
        result = _parsed(_run(KBToTweetyPlugin().translate_dung('["a", "b"]')))
        assert "error" in result
        assert result.get("received_type") == "list"

    def test_translate_aspic_bad_json(self):
        result = _parsed(_run(KBToTweetyPlugin().translate_aspic("{{{")))
        assert "error" in result

    def test_write_tweety_to_state_missing_formulas(self):
        state = None
        result = KBToTweetyPlugin().write_tweety_to_state('{"other": 1}', state=state)
        # state None est traite avant le parsing : erreur dediee, pas d'exception
        assert "error" in json.loads(result)

    def test_write_tweety_to_state_names_keys(self):
        class _State:
            def add_belief_set(self, logic_type, formula):
                return "bs1"

        result = KBToTweetyPlugin().write_tweety_to_state(
            '{"other": 1}', state=_State()
        )
        parsed = json.loads(result)
        assert "error" in parsed
        assert "formulas" in parsed["error"]
        assert parsed.get("received_keys") == ["other"]
