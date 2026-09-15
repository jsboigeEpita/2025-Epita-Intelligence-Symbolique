"""Né-rouge guards for #2117 — the webapp orchestrator homonym and the dead config path.

Measured on the pristine tree (base ``14fbe867``):

1. Two ``UnifiedWebOrchestrator`` classes with **incompatible constructors**
   (``argparse.Namespace`` in ``argumentation_analysis/webapp/orchestrator.py:630``
   vs ``config_path`` str in ``scripts/apps/webapp/unified_web_orchestrator.py:124``)
   — the homonym makes the import ambiguous and invites wiring the wrong twin.
   The measured consumers keep both alive: the canonical-tree twin feeds
   ``run_web_e2e_pipeline.py`` + 33 unit tests (CI), the scripts twin feeds
   ``run_api_validation.py`` + 3 e2e files. The canonical-tree twin keeps the
   name (repo policy: argumentation_analysis is the canonical tree); the
   scripts twin is renamed — the homonym dies, no consumer is migrated across
   twins.
2. ``run_web_e2e_pipeline.py:192`` pointed ``config`` at
   ``scripts/webapp/config/webapp_config.yml`` — nonexistent since #34 — and
   the orchestrator's ``_load_config`` silently fell back to defaults.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PIPELINE = (
    REPO_ROOT / "scripts" / "orchestration" / "pipelines" / "run_web_e2e_pipeline.py"
)


def test_homonym_is_gone_the_canonical_class_stays_2117():
    import argumentation_analysis.webapp.orchestrator as canonical
    import scripts.apps.webapp.unified_web_orchestrator as scripts_twin

    assert hasattr(canonical, "UnifiedWebOrchestrator"), (
        "the canonical-tree orchestrator keeps the name — it feeds the E2E "
        "pipeline and the 33-test guard suite"
    )
    assert not hasattr(scripts_twin, "UnifiedWebOrchestrator"), (
        "scripts/apps/webapp still exports a second UnifiedWebOrchestrator "
        "with an incompatible constructor — the #2117 homonym"
    )
    assert hasattr(
        scripts_twin, "WebAppValidationOrchestrator"
    ), "the scripts twin must stay importable under its renamed class"


def test_scripts_twin_default_config_is_anchored_and_real_2117():
    """The cwd-relative default (``config/webapp_config.yml``) resolved to the
    ROOT config from repo-root invocations and to nothing from elsewhere —
    the twin's own config copy was only reachable by cwd accident."""
    from scripts.apps.webapp.unified_web_orchestrator import DEFAULT_CONFIG_PATH

    assert DEFAULT_CONFIG_PATH.is_absolute()
    assert (
        DEFAULT_CONFIG_PATH.is_file()
    ), f"the anchored default config does not exist: {DEFAULT_CONFIG_PATH}"


def test_e2e_pipeline_config_path_exists_2117():
    source = PIPELINE.read_text(encoding="utf-8")
    flat = re.sub(r"\s+", " ", source)
    m = re.search(r'config_path = \(? ?project_root ?/ "scripts" ?/ "webapp"', flat)
    assert m is None, (
        "run_web_e2e_pipeline still points config at the pre-#34 root path "
        "scripts/webapp/config/ — the orchestrator silently falls back to "
        "default config (#2117)"
    )
    m = re.search(
        r'config_path = \(? ?project_root ?/ "argumentation_analysis" ?/ "webapp" ?/ "config" ?/ "webapp_config\.yml"',
        flat,
    )
    assert m is not None, (
        "run_web_e2e_pipeline must pass the canonical orchestrator's real "
        "config (argumentation_analysis/webapp/config/webapp_config.yml)"
    )
    assert (
        REPO_ROOT / "argumentation_analysis" / "webapp" / "config" / "webapp_config.yml"
    ).is_file()
