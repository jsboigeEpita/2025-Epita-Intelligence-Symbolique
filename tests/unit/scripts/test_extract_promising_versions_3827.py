"""roo-extensions#3827 — the code-recovery extractor restores every file, not the last block.

`scripts/maintenance/tools/extract_promising_versions.py` scans a conversation
log for a pytest summary whose pass count is "promising", and writes the code
that led there into a snapshot. On ``main`` ``938621b20`` it kept only **the
last code block** before the result, so a snapshot held one file out of the
several the conversation had touched. It also wrote that block's path as given,
so a ``../`` path landed outside the snapshot.

The port comes from a stash anchor (``10-2025-06-25``) that rebuilt each
file's state. Two of its defects are not ported: an ``apply_diff`` replaced the
file's content with the diff text, and the pass range was hard-coded.
"""

import importlib.util
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]

LOG = textwrap.dedent("""\
    Début de la conversation.
    <read_file><path>pkg/d.py</path></read_file>
    <write_to_file><path>pkg/a.py</path><content>
    A = 1
    </content></write_to_file>
    <read_file><args><file><path>pkg/b.py</path></file></args></read_file>
    [read_file for 'pkg/b.py'] Result:
    <files><file><path>pkg/b.py</path>
    <content lines="1-2">
    1 | B = 2
    2 | C = 3
    </content>
    </file></files>
    <apply_diff><path>pkg/b.py</path><diff>
    <<<<<<< SEARCH
    C = 3
    =======
    C = 4
    >>>>>>> REPLACE
    </diff></apply_diff>
    <apply_diff><path>pkg/c.py</path><diff>
    D = 5
    </diff></apply_diff>
    <write_to_file><path>../escape.py</path><content>
    E = 6
    </content></write_to_file>
    Lancement des tests.
    ===== short test summary info =====
    FAILED tests/test_x.py::test_y
    ===== 1 failed, 6 passed in 0.50s =====
    Suite.
    ===== short test summary info =====
    ===== 20 passed in 1.00s =====
    """)
FIRST_SUMMARY_LINE = LOG.splitlines().index("===== short test summary info =====") + 1


def _load_script():
    path = ROOT / "scripts" / "maintenance" / "tools" / "extract_promising_versions.py"
    spec = importlib.util.spec_from_file_location("extract_promising_versions", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script():
    return _load_script()


def _run(script, tmp_path, **kwargs):
    tmp_path.mkdir(parents=True, exist_ok=True)
    log = tmp_path / "conversation.md"
    log.write_text(LOG, encoding="utf-8")
    out = tmp_path / "out"
    script.PromisingVersionExtractor(
        output_base_dir=str(out), **kwargs
    ).extract_from_logs([str(log)])
    return out, sorted(p for p in out.iterdir() if p.is_dir())


def test_every_file_touched_before_the_result_is_restored(script, tmp_path):
    _, snapshots = _run(script, tmp_path)
    assert len(snapshots) == 1
    snap = snapshots[0]

    assert (snap / "pkg" / "a.py").read_text(encoding="utf-8") == "A = 1"
    # read_file result, line-number prefixes stripped; the later diff is kept
    # beside it, never written over it.
    assert (snap / "pkg" / "b.py").read_text(encoding="utf-8") == "B = 2\nC = 3"
    b_diff = (snap / "pkg" / "b.py.diff").read_text(encoding="utf-8")
    assert "C = 4" in b_diff and "Base: le contenu restauré" in b_diff
    # A file with only a diff gets the diff, and no invented content.
    assert not (snap / "pkg" / "c.py").exists()
    assert "Base: aucun contenu complet trouvé" in (
        snap / "pkg" / "c.py.diff"
    ).read_text(encoding="utf-8")
    # A read_file with no result does not borrow the next file's result.
    assert not (snap / "pkg" / "d.py").exists()


def test_a_path_leaving_the_snapshot_is_not_written(script, tmp_path):
    out, snapshots = _run(script, tmp_path)
    assert not (out / "escape.py").exists()
    written = [p for p in out.rglob("*") if p.is_file()]
    assert written and all(snapshots[0] in p.parents for p in written)


def test_the_snapshot_records_its_line_and_its_context(script, tmp_path):
    _, snapshots = _run(script, tmp_path)
    snap = snapshots[0]
    assert snap.name == f"conv1_snapshot1_L{FIRST_SUMMARY_LINE}_passed6"
    context = (snap / "_CONVERSATION_CONTEXT.md").read_text(encoding="utf-8")
    assert "Lancement des tests." in context
    assert "1 failed, 6 passed" in context


def test_the_promising_range_is_a_parameter(script, tmp_path):
    _, default = _run(script, tmp_path / "default")
    _, wide = _run(script, tmp_path / "wide", max_passed=24)
    _, narrow = _run(script, tmp_path / "narrow", max_passed=5)
    assert [s.name.rsplit("_", 1)[-1] for s in default] == ["passed6"]
    assert sorted(s.name.rsplit("_", 1)[-1] for s in wide) == ["passed20", "passed6"]
    assert narrow == []
