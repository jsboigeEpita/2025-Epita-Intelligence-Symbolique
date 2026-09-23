"""#2345 — each testing guide under `docs/guides/testing/` exists in one copy.

The #334 consolidation ("8 guides moved to docs/guides/testing/") copied the
guides out of `tests/` without removing the originals. Nine full copies stayed
behind: seven byte-identical, two already drifting (their relative links had
been fixed on one side only), and #2418 had to correct one pair twice. The
`tests/` files are now one-paragraph pointers to the guide.

Two guards:

* no tracked Markdown file repeats a guide's content (line endings and BOM
  normalised, so a CRLF copy is still a copy);
* every pointer from `tests/*.md` into `docs/guides/testing/` resolves.

The population is read from git (`ls-files --cached --others
--exclude-standard`), not from the working tree: a walk would see local
worktrees and virtualenvs, which carry full checkouts (see
`test_report_anchors_2258.py` for the measurement).
"""

import re
import subprocess
from functools import lru_cache
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
GUIDES = REPO_ROOT / "docs" / "guides" / "testing"
POINTER = re.compile(r"\]\((\.\./docs/guides/testing/[^)#\s]+\.md)\)")


def _normalised(path: Path) -> bytes:
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return data.replace(b"\r\n", b"\n").strip()


@lru_cache(maxsize=1)
def _tracked_markdown() -> tuple:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return tuple(REPO_ROOT / line for line in out.splitlines() if line.strip())


@lru_cache(maxsize=1)
def _paths_by_content() -> dict:
    index = {}
    for path in _tracked_markdown():
        if path.is_file():
            index.setdefault(_normalised(path), []).append(path)
    return index


def _guides() -> list:
    return sorted(GUIDES.glob("*.md"))


def test_population_is_not_empty():
    assert len(_guides()) >= 9
    assert len(_tracked_markdown()) > len(_guides())


@pytest.mark.parametrize("guide", _guides(), ids=lambda p: p.name)
def test_guide_content_has_one_copy(guide):
    copies = [
        p.relative_to(REPO_ROOT).as_posix()
        for p in _paths_by_content().get(_normalised(guide), [])
        if p.resolve() != guide.resolve()
    ]
    assert copies == []


def test_every_pointer_into_the_guides_resolves():
    pointers = []
    for path in sorted((REPO_ROOT / "tests").glob("*.md")):
        for target in POINTER.findall(path.read_text(encoding="utf-8-sig")):
            pointers.append((path.name, target, (path.parent / target).is_file()))
    assert pointers, "no pointer from tests/*.md into docs/guides/testing/"
    assert [p for p in pointers if not p[2]] == []
