"""#2852: the clingo binary Tweety receives is chosen by version, not by PATH.

Measured on the fleet (census #2851):
- ai-01, conda env on PATH: ``shutil.which("clingo")`` finds the conda 5.8.0;
  Tweety's ClingoSolver mis-parses its banner, the JVM path refuses and the
  phase falls back to clingo_python. Direct launch (no env on PATH): the
  ``ext_tools`` 5.4.0 is registered and clingo_jvm decides. Two PATHs, two
  different solvers — the machine's environment decided, not the code.
- po-2025: the conda clingo is MUTE (``--version`` prints nothing, rc 0) and
  ``ext_tools/clingo`` carries a leftover Linux ELF next to ``clingo.exe``
  (the JVM runs ``<dir>/clingo`` verbatim → CreateProcess error=193).

The fix (coordinator option a): every candidate is probed with ``--version``,
the binary whose version equals ``settings.jvm.clingo_version`` — the version
Tweety's output parser handles — is registered whatever the PATH order, a
missing one is provisioned via ``download_clingo``, and an incompatible-only
situation is SAID (a named rejection in the registry and the phase output),
never silently registered. Anti-pendulum: Tweety's parser is NOT patched and
the conda-forge clingo stays installed — a PATH binary of the right version
remains eligible.

The fakes below are real executables printing real banners (a .bat on
Windows, a shell script elsewhere): the production probe runs them for real.
"""

import asyncio
import os
import shutil
import stat
import sys
from pathlib import Path

import pytest

from argumentation_analysis.core import jvm_setup

SATISFIABLE_PROGRAM = "a.\nb :- a."


def _fake_clingo(directory: Path, version: str) -> Path:
    """A probe-able clingo: a real executable printing a real version banner."""
    directory.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        script = directory / "clingo.bat"
        script.write_text(f"@echo clingo version {version}\n", encoding="utf-8")
    else:
        script = directory / "clingo"
        script.write_text(
            f'#!/bin/sh\necho "clingo version {version}"\n', encoding="utf-8"
        )
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def _mute_clingo(directory: Path) -> Path:
    """Exit 0 printing nothing — the po-2025 conda binary class: it decides
    nothing while appearing present."""
    directory.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        script = directory / "clingo.bat"
        script.write_text("@echo off\nexit /b 0\n", encoding="utf-8")
    else:
        script = directory / "clingo"
        script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


# ── Selection layer: the version decides, not the candidate order ──────────


def test_selection_is_by_version_not_candidate_order(tmp_path):
    """The #2852 witness: two PATHs that expose the two binaries in the two
    orders must yield the SAME solver — the version-matched one. On main the
    selection function does not exist (PATH order decided)."""
    bad = _fake_clingo(tmp_path / "path_a", "5.8.0")
    good = _fake_clingo(tmp_path / "path_b", "5.4.0")

    for candidates in ([bad, good], [good, bad]):
        sel = jvm_setup.select_clingo_binary(
            candidates=candidates, wanted="5.4.0", provision=False
        )
        assert sel.binary == good.resolve(), (candidates, sel)
        assert sel.version == "5.4.0", sel


def test_incompatible_and_mute_binaries_are_rejected_with_reasons(tmp_path):
    """Both measured refusal classes are named: a wrong version AND a binary
    that prints no banner at all."""
    mute = _mute_clingo(tmp_path / "mute")
    bad = _fake_clingo(tmp_path / "wrong_version", "5.8.0")

    sel = jvm_setup.select_clingo_binary(
        candidates=[mute, bad], wanted="5.4.0", provision=False
    )

    assert sel.binary is None, sel
    reasons = " | ".join(sel.rejections)
    assert "5.8.0" in reasons, sel.rejections
    assert "no version banner" in reasons, sel.rejections


@pytest.mark.skipif(
    not (
        jvm_setup.EXT_TOOLS_DIR
        / "clingo"
        / ("clingo.exe" if os.name == "nt" else "clingo")
    ).exists(),
    reason="no provisioned ext_tools clingo on this seat",
)
def test_real_provisioned_binary_wins_over_env_path(monkeypatch):
    """On a seat holding the provisioned binary, the selection returns it
    even when a PATH clingo (the conda env's, under ``conda run``) is probed
    first or second — and reports its real version."""
    monkeypatch.setattr(jvm_setup, "download_clingo", lambda *a, **k: False)
    exe = (
        jvm_setup.EXT_TOOLS_DIR
        / "clingo"
        / ("clingo.exe" if os.name == "nt" else "clingo")
    )

    sel = jvm_setup.select_clingo_binary(provision=False)

    assert sel.binary == exe.resolve(), sel
    assert sel.version == jvm_setup.CLINGO_VERSION, sel


# ── Registry layer: the production entry registers the verdict ─────────────


def _jvm_or_skip():
    if not jvm_setup.is_jvm_started():
        pytest.skip("the JVM is not started: _configure_external_tools returns")


@pytest.fixture
def isolated_registry(monkeypatch, tmp_path):
    """Re-run the production configuration against a stubbed ext_tools, a
    controlled PATH and a stubbed downloader; restore the registry after."""
    _jvm_or_skip()
    ext = tmp_path / "ext_tools"
    (ext / "clingo").mkdir(parents=True)
    monkeypatch.setattr(jvm_setup, "EXT_TOOLS_DIR", ext)
    monkeypatch.setattr(jvm_setup, "download_clingo", lambda *a, **k: False)
    monkeypatch.setattr(
        jvm_setup, "EXTERNAL_TOOL_PATHS", dict(jvm_setup.EXTERNAL_TOOL_PATHS)
    )
    yield ext


def _which_returning(path):
    # Capture the real which BEFORE monkeypatch replaces it — the fallback for
    # non-clingo names must not recurse into the fake itself.
    real_which = shutil.which

    def fake_which(name, *args, **kwargs):
        if name == "clingo" and path is not None:
            return str(path)
        return real_which(name, *args, **kwargs)

    return fake_which


def test_configure_registers_no_incompatible_path_clingo(
    isolated_registry, monkeypatch
):
    """BORN RED on main: a PATH clingo that reports the wrong version must
    NOT be registered (main registers the first existing PATH candidate
    without ever probing it)."""
    bad = _fake_clingo(isolated_registry.parent / "pathbin", "5.8.0")
    monkeypatch.setattr(shutil, "which", _which_returning(bad))

    jvm_setup._configure_external_tools()

    assert "clingo" not in jvm_setup.EXTERNAL_TOOL_PATHS, (
        jvm_setup.EXTERNAL_TOOL_PATHS.get("clingo"),
        "a version-incompatible clingo was registered",
    )
    notes = getattr(jvm_setup, "EXTERNAL_TOOL_REJECTIONS", {}).get("clingo", "")
    assert "5.8.0" in notes, notes


def test_configure_registers_a_version_matching_path_clingo(
    isolated_registry, monkeypatch
):
    """Anti-pendulum: the PATH is not banned — a PATH clingo of the wanted
    version is registered (green on main too: main takes the PATH first)."""
    good = _fake_clingo(isolated_registry.parent / "pathbin", "5.4.0")
    monkeypatch.setattr(shutil, "which", _which_returning(good))

    jvm_setup._configure_external_tools()

    assert jvm_setup.EXTERNAL_TOOL_PATHS.get("clingo") == str(
        good.parent.resolve()
    ), jvm_setup.EXTERNAL_TOOL_PATHS.get("clingo")


def test_say_so_when_only_incompatible_binaries_exist(
    isolated_registry, monkeypatch, caplog
):
    """The 'say so' half of option a: nothing registered AND the rejection
    named in a warning — not a silent absence."""
    mute = _mute_clingo(isolated_registry.parent / "mute_only")
    monkeypatch.setattr(shutil, "which", _which_returning(mute))

    with caplog.at_level("WARNING"):
        jvm_setup._configure_external_tools()

    assert "clingo" not in jvm_setup.EXTERNAL_TOOL_PATHS
    assert any("clingo" in r.message.lower() for r in caplog.records), caplog.text


# ── The leftover non-Windows sibling that broke the JVM run (error=193) ────


def test_nonpe_clingo_sibling_is_quarantined(tmp_path):
    """Measured on po-2025: a Linux ELF named ``clingo`` next to
    ``clingo.exe`` — the JVM executes ``<dir>/clingo`` verbatim and gets
    CreateProcess error=193. The fix renames it aside (reversible), never
    deletes it, and never touches ``clingo.exe``."""
    if os.name != "nt":
        pytest.skip("the leftover-ELF failure mode is Windows-only")
    (tmp_path / "clingo.exe").write_bytes(b"MZ" + b"\x00" * 64)
    elf = tmp_path / "clingo"
    elf.write_bytes(b"\x7fELF" + b"\x00" * 64)

    quarantined = jvm_setup.quarantine_nonpe_clingo_sibling(tmp_path)

    assert quarantined is not None
    assert not elf.exists(), "the non-PE sibling is still in the JVM's way"
    assert (
        tmp_path / "clingo.nonpe"
    ).is_file(), "the sibling was deleted, not quarantined"
    assert (tmp_path / "clingo.exe").is_file(), "the real binary was touched"
    # A second run is a no-op (already quarantined).
    assert jvm_setup.quarantine_nonpe_clingo_sibling(tmp_path) is None


def test_pe_clingo_sibling_is_left_alone(tmp_path):
    """A no-extension ``clingo`` that IS a Windows executable (someone's
    rename) must not be quarantined."""
    if os.name != "nt":
        pytest.skip("the leftover-ELF failure mode is Windows-only")
    (tmp_path / "clingo").write_bytes(b"MZ" + b"\x00" * 64)

    assert jvm_setup.quarantine_nonpe_clingo_sibling(tmp_path) is None
    assert (tmp_path / "clingo").is_file()


# ── The phase output counts the refusal (#2852 DoD) ─────────────────────────


def test_missing_compatible_binary_is_counted_in_phase_output(monkeypatch):
    """When no compatible clingo was registered, the ASP phase result carries
    the named refusal (``jvm_refused``) instead of silently switching to
    clingo_python — on main the refusal reason stays None and the key never
    appears."""
    registry = dict(jvm_setup.EXTERNAL_TOOL_PATHS)
    registry.pop("clingo", None)
    monkeypatch.setattr(jvm_setup, "EXTERNAL_TOOL_PATHS", registry)
    monkeypatch.setattr(
        jvm_setup,
        "EXTERNAL_TOOL_REJECTIONS",
        {"clingo": "wanted 5.4.0; X -> 5.8.0 (wanted 5.4.0)"},
    )

    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_asp_reasoning,
    )

    res = asyncio.new_event_loop().run_until_complete(
        _invoke_asp_reasoning(SATISFIABLE_PROGRAM, {})
    )

    assert res.get("jvm_refused", "").startswith("no compatible clingo"), res
    assert res["solver"] == "clingo_python", res
    assert {"a", "b"} in [set(m) for m in res["answer_sets"]], res
