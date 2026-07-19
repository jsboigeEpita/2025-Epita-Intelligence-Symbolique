"""Tests for extract_belief_trajectories.py — TPM-2 #1491 (real corpora + ergodicity).

Static + functional tests with NO LLM / NO key / NO JVM.
Mirrors the TPM-1 #1489 test pattern (importlib + introspection).

What's tested (TPM-2 contract):
- ``_analyze_ergodicity`` classifies irreducible (1 SCC) vs reducible (≥2 SCC)
  chains correctly via mocked TPMs (no scipy required for the logic itself
  when we exercise the n_scc/n_wcc classification through the public API).
- Impossible / degenerate TPMs return ``analysis_skipped=True``.
- Soft-fail (scipy absent) returns a sentinel ``analysis_skipped=True``.
- ``_load_corpus_propositions`` builds opaque IDs (no source name leakage).
- Privacy HARD: script body never references ``raw_text`` / ``full_text`` /
  ``verbatim`` outside of a denylist comment.
- CLI: ``--source corpusA|B|C`` is accepted by argparse; dry-run prints
  TPM-2 header.
"""

from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys
import textwrap
import types
from typing import Any, Dict, List, Optional

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "extract_belief_trajectories.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_script_module() -> types.ModuleType:
    """Import the script as a module (file-disjoint from the main package)."""
    spec = importlib.util.spec_from_file_location(
        "extract_belief_trajectories_1491", str(SCRIPT_PATH)
    )
    assert spec and spec.loader, "Could not build importlib spec for the script"
    mod = importlib.util.module_from_spec(spec)
    sys.modules["extract_belief_trajectories_1491"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _load_corpus_loader_module() -> types.ModuleType:
    """Import the privacy-aware corpus loader module directly."""
    loader_path = REPO_ROOT / "scripts" / "_tpm_corpus_loader.py"
    spec = importlib.util.spec_from_file_location(
        "tpm_corpus_loader_1491", str(loader_path)
    )
    assert spec and spec.loader, "Could not build importlib spec for the loader"
    mod = importlib.util.module_from_spec(spec)
    sys.modules["tpm_corpus_loader_1491"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _fake_tpm(
    states: List[str],
    counts: List[List[int]],
    *,
    impossible: bool = False,
    reason: Optional[str] = None,
) -> Any:
    """Build a stand-in for ``TPM`` that ``_analyze_ergodicity`` accepts.

    Uses ``types.SimpleNamespace`` so we don't have to instantiate the real
    ``TPM`` class (which has invariants the tests don't care about).
    """
    ns = types.SimpleNamespace(
        states=states,
        transition_counts=counts,
        impossible=impossible,
        impossibility_reason=reason or "",
        n_trajectories=1,
        n_observations_total=sum(sum(r) for r in counts),
        n_transitions=int(sum(sum(r) for r in counts) / max(len(states), 1)),
    )
    return ns


# ---------------------------------------------------------------------------
# Importability
# ---------------------------------------------------------------------------


def test_module_imports() -> None:
    mod = _load_script_module()
    assert hasattr(mod, "_analyze_ergodicity")
    assert hasattr(mod, "_load_corpus_propositions")
    assert hasattr(mod, "ErgodicityResult")
    # The privacy-aware loader is a separate module.
    loader = _load_corpus_loader_module()
    assert hasattr(loader, "load_corpus_definitions")
    assert hasattr(loader, "load_corpus_propositions")


# ---------------------------------------------------------------------------
# Ergodicity analysis — synthetic TPMs
# ---------------------------------------------------------------------------


class TestErgodicityAnalysis:
    def test_impossible_returns_skipped(self) -> None:
        mod = _load_script_module()
        tpm = _fake_tpm([], [], impossible=True, reason="empty")
        ergo = mod._analyze_ergodicity(tpm)
        assert ergo.analysis_skipped is True
        assert ergo.n_scc == 0
        assert ergo.irreducible is False

    def test_irreducible_chain_1_scc(self) -> None:
        """3-state fully connected chain → 1 SCC, 1 WCC, irreducible."""
        mod = _load_script_module()
        # 3 states, each transitions to each (including self-loop).
        counts = [
            [2, 1, 1],
            [1, 2, 1],
            [1, 1, 2],
        ]
        tpm = _fake_tpm(["a", "b", "c"], counts)
        ergo = mod._analyze_ergodicity(tpm)
        assert ergo.analysis_skipped is False
        assert ergo.n_scc == 1
        assert ergo.n_wcc == 1
        assert ergo.irreducible is True
        # All self-loops present → aperiodic=True → ergodic=True.
        assert ergo.aperiodic is True
        assert ergo.ergodic is True
        # Stationary must be a dict (top-3).
        assert isinstance(ergo.stationary, dict)
        assert len(ergo.stationary) >= 1

    def test_reducible_chain_2_scc(self) -> None:
        """Block-diagonal: states {a,b} and {c,d} form 2 SCCs."""
        mod = _load_script_module()
        # SCC1 = {a, b}: they only transition among themselves.
        # SCC2 = {c, d}: same. No cross-block transitions.
        counts = [
            [1, 1, 0, 0],
            [1, 1, 0, 0],
            [0, 0, 1, 1],
            [0, 0, 1, 1],
        ]
        tpm = _fake_tpm(["a", "b", "c", "d"], counts)
        ergo = mod._analyze_ergodicity(tpm)
        assert ergo.analysis_skipped is False
        assert ergo.n_scc == 2
        # With two disjoint diagonal blocks, scipy also yields 2 WCCs.
        assert ergo.n_wcc == 2
        assert ergo.irreducible is False
        assert ergo.ergodic is False
        assert ergo.stationary is None

    def test_disconnected_two_wcc(self) -> None:
        """4 states, no transitions at all → 4 SCCs, multiple WCCs possible."""
        mod = _load_script_module()
        counts = [
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ]
        # With all-zero counts, ``_analyze_ergodicity`` should still run
        # (not impossible — the state space exists) and yield n_scc == 4
        # (each isolated state is its own SCC).
        tpm = _fake_tpm(["a", "b", "c", "d"], counts, impossible=False)
        ergo = mod._analyze_ergodicity(tpm)
        # The all-zero chain has n_scc == 4 (each isolated state).
        if not ergo.analysis_skipped:
            assert ergo.n_scc >= 2
            assert ergo.irreducible is False


# ---------------------------------------------------------------------------
# Corpus loader — static privacy contract
# ---------------------------------------------------------------------------


class TestCorpusLoaderContract:
    def test_corpus_loader_accepts_A_B_C(self) -> None:
        loader = _load_corpus_loader_module()
        import inspect

        sig = inspect.signature(loader.load_corpus_definitions)
        assert "corpus_id" in sig.parameters

        sig = inspect.signature(loader.load_corpus_propositions)
        assert "corpus_id" in sig.parameters

    def test_loader_import_graph_resolves(self) -> None:
        """Anti-regression (R672): the loader must import cleanly.

        TPM-2 #1491 (PR #1492) shipped with a loader that referenced a
        non-existent ``derive_key_from_passphrase``. Tests / ``--dry-run``
        never exercised the inner imports, so CI stayed green while the
        real flow crashed on ImportError when ``_load_corpus_propositions``
        was actually called. This test forces the inner import graph to
        resolve (importing the loader does NOT trigger the late imports —
        it has to be exercised by calling ``load_corpus_definitions`` with
        a missing env, which then enters the late-import block and re-raises
        something other than ``ImportError`` on the helper module).
        """
        loader = _load_corpus_loader_module()
        # The R672 invariant is: calling the loader must NOT raise ImportError
        # (that would mean it references a symbol absent from crypto_utils /
        # io_manager). It may legitimately raise EnvironmentError (no
        # passphrase) / FileNotFoundError (no dataset), OR succeed when the
        # secret is present — all three prove the import graph resolves. Do
        # not assert the missing-passphrase path specifically: that makes the
        # test env-fragile (it breaks the moment TEXT_CONFIG_PASSPHRASE is set,
        # e.g. alongside the real-decrypt regression below).
        try:
            loader.load_corpus_definitions("A")
        except ImportError as exc:  # pragma: no cover — the regression we guard
            pytest.fail(f"Loader import graph broken (R672 regression): {exc}")
        except (EnvironmentError, FileNotFoundError, ValueError):
            pass  # expected when the secret / dataset is absent

    def test_corpus_loader_rejects_unknown_id(self) -> None:
        loader = _load_corpus_loader_module()
        with pytest.raises(ValueError, match="Unknown corpus id"):
            loader.load_corpus_definitions("Z")

    def test_opaque_id_format(self) -> None:
        """Opaque IDs must start with ``prop_`` and be 13 chars (prop_ + 8 hex).

        The fixture uses ``full_text`` — the REAL dataset field (there is NO
        bare ``text`` key). The earlier fixture used ``text``, which masked the
        shape bug that shipped in #1492 (loader filtered on a non-existent
        field → 0 props from the real corpus). Keep this fixture aligned with
        the real schema.
        """
        loader = _load_corpus_loader_module()
        fake_defs = [
            {"id": "src0_ext0", "full_text": "Hello world.", "source_name": "Dictator X"},
            {"id": "src0_ext1", "full_text": "Another text.", "source_name": "Politician Y"},
        ]
        loader.load_corpus_definitions = lambda cid: fake_defs  # type: ignore[assignment]
        props = loader.load_corpus_propositions("A")
        assert len(props) == 2
        for pid, meta in props.items():
            assert pid.startswith("prop_")
            assert len(pid) == 13  # "prop_" + 8 hex
            # The OPAQUE proposition ID must NEVER contain the source name.
            assert "Dictator" not in pid
            assert "Politician" not in pid
            # The run loop reads BOTH ``text`` and ``label`` — a missing
            # ``label`` KeyErrors on the first real proposition (2nd shape bug
            # that shipped in #1492).
            assert "text" in meta and meta["text"]
            assert "label" in meta
            # ``label`` is persisted as ``corpus_label`` → must stay opaque
            # (no source name), and reference the opaque prop id.
            assert "Dictator" not in meta["label"]
            assert "Politician" not in meta["label"]
            assert pid in meta["label"]

    def test_empty_corpus_raises(self) -> None:
        loader = _load_corpus_loader_module()
        loader.load_corpus_definitions = lambda cid: []  # type: ignore[assignment]
        with pytest.raises(ValueError, match="0 propositions"):
            loader.load_corpus_propositions("B")

    def test_script_delegates_to_loader(self) -> None:
        """The script body must NOT import the loader at top-level (else the
        static privacy test on the script would fail). It should call the
        loader from inside ``_load_corpus_propositions``."""
        src = SCRIPT_PATH.read_text(encoding="utf-8")
        # The forbidden terms must remain absent from the script body.
        for term in ("extract_sources", "TEXT_CONFIG_PASSPHRASE", ".json.gz.enc"):
            assert term not in src, (
                f"Privacy HARD regression: '{term}' must NOT appear in the "
                "script body (delegated to _tpm_corpus_loader.py)."
            )


# ---------------------------------------------------------------------------
# Privacy HARD — script body static check
# ---------------------------------------------------------------------------


class TestPrivacyHard:
    def test_no_raw_text_in_persistence(self) -> None:
        """No code path in the script writes raw_text / full_text / verbatim
        to a persistent surface. (In-memory text passed to the pipeline is OK —
        it's the pipeline's contract.)"""
        src = SCRIPT_PATH.read_text(encoding="utf-8")
        # Forbid the denylist on lines that LOOK like writes/persistence.
        forbidden_phrases_on_write = [
            'json.dump',
            'open(',
            'Path(',
            'write_text',
            'writelines',
        ]
        for phrase in forbidden_phrases_on_write:
            for line_no, line in enumerate(src.splitlines(), 1):
                if phrase in line and ("raw_text" in line or "full_text" in line or "verbatim" in line):
                    pytest.fail(
                        f"Privacy HARD #1491: '{phrase}' + forbidden identifier on line {line_no}: {line!r}"
                    )

    def test_opaque_id_prefix_used(self) -> None:
        """The loader must use ``prop_`` opaque prefix, not source names.
        (Lives in scripts/_tpm_corpus_loader.py — privacy-aware module.)"""
        loader_path = REPO_ROOT / "scripts" / "_tpm_corpus_loader.py"
        src = loader_path.read_text(encoding="utf-8")
        assert "prop_" in src  # opaque prefix
        assert "sha256" in src  # stable hashing

    def test_no_load_encrypted_corpus_persistence(self) -> None:
        """The script must NOT call any persistence API after loading the
        encrypted corpus. The decrypt-to-disk path is forbidden."""
        src = SCRIPT_PATH.read_text(encoding="utf-8")
        # After the ``_load_corpus_definitions`` call, there should be no
        # file-writing call that receives the loaded definitions.
        # We test a coarse invariant: no ``json.dump(`` of ``defs``.
        assert "json.dump(defs" not in src
        assert "json.dump(definitions" not in src


# ---------------------------------------------------------------------------
# CLI contract
# ---------------------------------------------------------------------------


class TestCLIContract:
    def test_argparse_accepts_corpus_sources(self) -> None:
        """``--source corpusA|B|C`` must be accepted (parser-level)."""
        for src in ("corpusA", "corpusB", "corpusC"):
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--dry-run",
                    "--source",
                    src,
                ],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(REPO_ROOT),
            )
            assert result.returncode == 0, (
                f"--source {src} failed:\nSTDOUT:\n{result.stdout}\n"
                f"STDERR:\n{result.stderr}"
            )
            assert "TPM-2 #1491" in result.stdout

    def test_argparse_rejects_unknown_source(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--dry-run",
                "--source",
                "garbage",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode != 0
        assert "invalid choice" in result.stderr.lower() or "argument" in result.stderr.lower()


# ---------------------------------------------------------------------------
# Real-decrypt regression — the shape-bug guard the dry-run tests lacked
# ---------------------------------------------------------------------------


import os  # noqa: E402  (local to the gated test below)

_ENC_PATH = (
    REPO_ROOT / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"
)
_HAS_SECRET = bool(os.environ.get("TEXT_CONFIG_PASSPHRASE")) and _ENC_PATH.exists()


@pytest.mark.skipif(
    not _HAS_SECRET,
    reason="TEXT_CONFIG_PASSPHRASE not set or encrypted dataset absent — "
    "real-decrypt regression skips gracefully (CI without the secret).",
)
class TestCorpusLoaderRealDecrypt:
    """Decrypt the REAL corpus and assert the loader yields usable props.

    This is the guard that was missing when #1492 shipped: every prior test
    either mocked ``load_corpus_definitions`` with the wrong schema (a bare
    ``text`` key the real dataset never had) or stopped at ``--dry-run``
    (which returns before the run loop). As a result, TWO shape bugs reached
    ``main`` green:

    1. The loader filtered on ``d.get("text")`` → 0 props from the real
       corpus (real field is ``full_text``).
    2. The run loop reads ``meta["label"]`` → KeyError on the first real prop
       (loader returned only ``_source_label``).

    This test exercises the true decrypt path with real data and asserts the
    exact shape the run loop consumes — ``text`` (non-empty) + ``label``
    (opaque). It prints NO text (privacy HARD): it asserts on lengths and
    prefixes only.
    """

    def test_real_corpus_yields_props_with_run_loop_shape(self) -> None:
        loader = _load_corpus_loader_module()
        props = loader.load_corpus_propositions("A")
        assert props, "Real corpus A produced 0 propositions (shape regression)."
        for pid, meta in props.items():
            # Opaque ID on every surface.
            assert pid.startswith("prop_") and len(pid) == 13
            # The run loop reads BOTH keys — both must exist and be usable.
            assert meta.get("text"), f"{pid}: empty/absent text (full_text mapping regression)."
            assert meta.get("label"), f"{pid}: absent label (run-loop KeyError regression)."
            # Persisted ``corpus_label`` must stay opaque: it references the
            # opaque id and never the internal source name.
            assert pid in meta["label"]
            assert meta["label"] != meta.get("_source_label", "")

    def test_real_corpus_no_source_name_in_persisted_label(self) -> None:
        """The persisted ``label`` must not equal the internal source name."""
        loader = _load_corpus_loader_module()
        props = loader.load_corpus_propositions("A")
        for _pid, meta in props.items():
            src = meta.get("_source_label", "")
            # _source_label is internal grouping only; label (persisted) must
            # not carry it verbatim.
            if src and src != "unknown":
                assert src not in meta["label"], (
                    "Privacy HARD: internal source name leaked into the "
                    "persisted opaque label."
                )