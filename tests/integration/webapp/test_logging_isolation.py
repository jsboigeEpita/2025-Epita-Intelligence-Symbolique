"""Logging isolation — each orchestrator instance writes to ITS configured file.

#2336: ``_setup_logging`` resolves its logger by module name — identical for
every instance — and attaches a FileHandler only ``if not logger.handlers``.
The FIRST instance of the process therefore fixes the log file, and any later
instance's ``logging.file`` is silently ignored: its file is never created,
its lines land in the first instance's file. Nothing raises, nothing warns —
the absence of a log file later reads as "the component never ran".

The repair routes by DESTINATION: the logger identity is derived from the
resolved log path, so two instances configured with two distinct files each
get their own logger and handler, while two instances sharing a path share
one logger — the original no-duplicate-handlers guard keeps its intent and
becomes correct.

Both halves verified from a Windows seat, no skips.
"""

import sys

sys.path.insert(0, ".")

from argumentation_analysis.webapp.orchestrator import UnifiedWebOrchestrator


def _build(webapp_config, test_config_path, tmp_path, log_file, log_level="INFO"):
    """Construct the orchestrator with ``logging.file`` pinned to ``log_file``
    and return (orchestrator, text of that file)."""
    import logging

    import yaml

    webapp_config["logging"] = {"file": str(log_file), "level": log_level}
    with open(test_config_path, "w") as f:
        yaml.dump(webapp_config, f)
    import argparse

    args = argparse.Namespace(
        config=str(test_config_path),
        log_level=log_level,
        headless=True,
        visible=False,
        timeout=5,
        no_trace=True,
    )
    UnifiedWebOrchestrator(args=args)
    return log_file.read_text(encoding="utf-8") if log_file.exists() else ""


class TestDistinctFilesEachReceiveTheirOwnLines:
    def test_second_instance_writes_to_its_own_file(
        self, webapp_config, test_config_path, tmp_path
    ):
        """Born-red on the defect (#2336 DoD 1): with the module-name logger,
        the second construction's file is NEVER created — its lines silently
        land in the first instance's file."""
        file1 = tmp_path / "orch1.log"
        file2 = tmp_path / "orch2.log"

        log1 = _build(
            webapp_config, test_config_path, tmp_path, file1, log_level="INFO"
        )
        log2 = _build(
            webapp_config, test_config_path, tmp_path, file2, log_level="DEBUG"
        )

        # The level marker (logged at the end of _setup_logging, line "Niveau
        # de log ... configuré sur : LEVEL") discriminates the two instances.
        assert "DEBUG" in log2 and "configuré sur" in log2, (
            "the second instance must write its own lines to ITS configured "
            f"file — file exists: {file2.exists()}"
        )
        assert "INFO" in log1, "the first instance's file keeps its own lines"
        assert (
            "configuré sur : DEBUG" not in log1
        ), "the second instance's lines must NOT leak into the first file"


class TestSharedPathNoDuplication:
    def test_two_constructions_same_path_do_not_double_lines(
        self, webapp_config, test_config_path, tmp_path
    ):
        """Anti-pendulum control (#2336 DoD 2): the original guard existed to
        prevent duplicate handlers; after the repair, two instances sharing a
        path share one logger — each construction logs its marker exactly once."""
        import logging

        shared = tmp_path / "shared.log"
        # Baseline hygiene: this control measures DUPLICATION, which needs a
        # clean logger — handlers left by an earlier test (on the module-name
        # logger, pre-fix) would route this test's lines to THAT test's file
        # and measure the wrong thing. Detach the module logger only.
        module_logger = logging.getLogger("argumentation_analysis.webapp.orchestrator")
        for handler in list(module_logger.handlers):
            module_logger.removeHandler(handler)

        _build(webapp_config, test_config_path, tmp_path, shared, log_level="INFO")
        _build(webapp_config, test_config_path, tmp_path, shared, log_level="INFO")

        text = shared.read_text(encoding="utf-8")
        assert text.count("configuré sur") == 2, (
            "two constructions on the same path must produce exactly one "
            f"marker line each, got {text.count('configuré sur')}"
        )
