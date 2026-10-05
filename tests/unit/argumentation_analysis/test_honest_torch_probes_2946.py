"""#2946: the four transformers availability probes degrade honestly.

In an env where transformers disabled its torch backend (the lock served
transformers 5.x with torch 2.2.2), ``from transformers import pipeline``
still succeeds — so every import-based probe reported the capability as
present, and the failure moved to the first model use. The probes now ask
the real question (``transformers.utils.is_torch_available()``); these
witnesses hold them to it, offline, by reporting torch absent and asserting
each site answers *unavailable* instead of deferring a crash.

- The two adapter tiers are lazy (``is_available()``): an in-process
  monkeypatch on the source module attribute is enough — the method binds
  ``is_torch_available`` at call time.
- The two plugin flags resolve on FIRST USE, not at import (#2867: the
  modules sit on the ``api.main`` import path, which must stay
  transformers-free). The monkeypatch must land before that first use, so
  each witness runs in a fresh subprocess that patches first, imports
  second, triggers the resolver third.
"""

import subprocess
import sys
from pathlib import Path

# The subprocess imports the probe module from the repo: its cwd must be
# the project root (a ``-c`` subprocess puts cwd on sys.path).
_PROJECT_ROOT = Path(__file__).resolve().parents[3]

_HONESTY_SUBPROCESS_TEMPLATE = """
import importlib
import sys

import transformers.utils
import transformers.utils.import_utils as iu

# Report torch absent BEFORE the probe resolves its backend: the flag under
# test is set on first use, so the patch must precede that use.
def _torch_absent():
    return False

iu.is_torch_available = _torch_absent
transformers.utils.is_torch_available = _torch_absent

# importlib, not ``import x as y``: the package's __init__ exports an
# attribute with the same name as the module (a singleton instance), which
# shadows the submodule on attribute access.
probe = importlib.import_module({module!r})

# Import alone must not resolve anything (the #2867 seam): the first use
# is what asks the question.
assert probe._backend_resolved is False, (
    "#2867: importing the module resolved the transformers backend — "
    "the resolution belongs to first use"
)

assert probe._resolve_transformers_backend() is False, (
    "#2946: the probe still reports available with torch absent"
)
assert probe.HAS_TRANSFORMERS is False, (
    "#2946: the probe still reports available with torch absent "
    f"(HAS_TRANSFORMERS={{probe.HAS_TRANSFORMERS}})"
)
assert probe.pipeline is None, (
    f"#2946: pipeline leaked into the degraded mode ({{probe.pipeline}})"
)
print("HONEST", probe.__name__)
"""


def _run_honesty_subprocess(module: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", _HONESTY_SUBPROCESS_TEMPLATE.format(module=module)],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(_PROJECT_ROOT),
    )


class TestNLITierReportsUnavailable:
    def test_torch_absent_means_unavailable_not_deferred(self, monkeypatch):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            NLIFallacyDetector,
        )

        monkeypatch.setattr("transformers.utils.is_torch_available", lambda: False)
        detector = NLIFallacyDetector()
        assert detector.is_available() is False, (
            "#2946: with torch reported absent the NLI tier must answer "
            "unavailable, not stay available and crash at first use"
        )
        # The degraded path returns no detection instead of deferring the
        # failure to _get_classifier.
        assert detector.detect("un argument quelconque") == []


class TestCamembertTierReportsUnavailable:
    def test_torch_absent_means_unavailable_not_deferred(self, monkeypatch):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            CamemBERTFallacyDetector,
        )

        monkeypatch.setattr("transformers.utils.is_torch_available", lambda: False)
        detector = CamemBERTFallacyDetector()
        assert detector.is_available() is False, (
            "#2946: with torch reported absent the CamemBERT tier must "
            "answer unavailable before looking for a model — importing the "
            "model classes succeeds even when torch is disabled"
        )
        assert detector.detect("un argument quelconque") == []


class TestNlpModelManagerFlagIsHonest:
    def test_torch_absent_sets_flag_false(self):
        proc = _run_honesty_subprocess(
            "argumentation_analysis.plugins.analysis_tools.logic.nlp_model_manager"
        )
        assert proc.returncode == 0, (
            "#2946: nlp_model_manager still reports available with torch "
            f"absent:\nstdout: {proc.stdout[-400:]}\nstderr: {proc.stderr[-800:]}"
        )
        assert "HONEST" in proc.stdout, proc.stdout


class TestContextualAnalyzerFlagIsHonest:
    def test_torch_absent_sets_flag_false(self):
        proc = _run_honesty_subprocess(
            "argumentation_analysis.plugins.analysis_tools.logic"
            ".contextual_fallacy_analyzer"
        )
        assert proc.returncode == 0, (
            "#2946: contextual_fallacy_analyzer still reports available "
            f"with torch absent:\nstdout: {proc.stdout[-400:]}\n"
            f"stderr: {proc.stderr[-800:]}"
        )
        assert "HONEST" in proc.stdout, proc.stdout
