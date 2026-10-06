"""#2088 item 5 — add the missing parent<->child README links, mechanically.

The set guard lives in
``tests/unit/docs/test_argumentation_readmes_cover_dirs_2088.py``
(``TestParentChildReadmeLinksBothWays``): every README whose immediate
parent/child directory also carries a tracked README must link it BOTH ways.
That guard reddened on main ``25299812e`` with 50 parent->child and 36
child->parent omissions; this producer closes them without editorial input
and stays idempotent — a second run adds nothing.

Conventions (matching ``orchestration/hierarchical/``, the pilot lot):

- child README: a ``Parent :`` line right under the H1 title;
- parent README: a trailing ``## Enfants documentés`` bullet list.

Idempotent, BOM-tolerant (utf-8-sig read, utf-8 no-BOM write), line-ending
preserving (CRLF files stay CRLF). Run from the repo root:

    python scripts/docs/link_readme_tree_2088.py [--check]
"""

from __future__ import annotations

import argparse
import posixpath
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SUBTREE = "argumentation_analysis"
VENDORED_ROOTS = ("libs", "portable_jdk")

_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "--", SUBTREE],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in out.stdout.splitlines() if line]


def _md_link_targets(readme: str) -> set[str]:
    raw_text = (REPO / readme).read_text(encoding="utf-8-sig")
    targets = set()
    for raw in _LINK_RE.findall(raw_text):
        if raw.startswith(("http://", "https://", "mailto:")):
            continue
        target = raw.split("#")[0].strip()
        if target.endswith(".md"):
            targets.add(target)
    return targets


def _edges(files: list[str]) -> list[tuple[str, str]]:
    """(parent_dir, child_dir) with both READMEs tracked; '' = subtree root."""
    tree = {
        f[len(SUBTREE) + 1 : -len("/README.md")]
        for f in files
        if f.endswith("/README.md")
        and f != f"{SUBTREE}/README.md"
        and f.split("/")[1] not in VENDORED_ROOTS
    }
    edges = []
    for child in sorted(tree):
        parent = child.rsplit("/", 1)[0] if "/" in child else ""
        if parent == "" or parent in tree:
            edges.append((parent, child))
    return edges


def _read(readme: str) -> tuple[str, bool]:
    """(text-without-BOM, file-uses-CRLF)."""
    raw = (REPO / readme).read_bytes().decode("utf-8-sig")
    return raw, "\r\n" in raw


def _write(readme: str, text: str, crlf: bool) -> None:
    if crlf:
        text = text.replace("\r\n", "\n").replace("\n", "\r\n")
    else:
        text = text.replace("\r\n", "\n")
    (REPO / readme).write_bytes(text.encode("utf-8"))


def _add_back_link(text: str, nl: str, parent_display: str) -> str:
    """Insert the `Parent :` line under the H1 (or at the top)."""
    lines = text.split(nl)
    insert_at = 0
    if lines and lines[0].startswith("# "):
        insert_at = 1
    line = f"Parent : [`{parent_display}/README.md`](../README.md).{nl}"
    lines.insert(insert_at, line)
    # keep exactly one blank line between title/parent and the body
    out = nl.join(lines)
    return re.sub(r"(Parent :[^\n]*\n)\n{2,}", r"\1\n", out, count=1)


def _add_child_list(text: str, nl: str, children: list[str]) -> str:
    section = nl + nl.join(
        ["## Enfants documentés", ""]
        + [f"- [`{c}/`](./{c}/README.md)" for c in children]
    )
    if not text.endswith(nl):
        text += nl
    return text + section + nl


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report what would change, modify nothing",
    )
    args = parser.parse_args()

    files = _tracked_files()
    edges = _edges(files)

    # parent -> missing child links ; child -> missing back-link
    parent_gaps: dict[str, list[str]] = defaultdict(list)
    back_gaps: list[str] = []
    for parent, child in edges:
        parent_readme = (
            f"{SUBTREE}/{parent}/README.md" if parent else f"{SUBTREE}/README.md"
        )
        child_readme = f"{SUBTREE}/{child}/README.md"
        targets = {
            posixpath.normpath(
                (f"{SUBTREE}/{parent}/" if parent else f"{SUBTREE}/") + t
            )
            for t in _md_link_targets(parent_readme)
        }
        if f"{SUBTREE}/{child}/README.md" not in targets:
            parent_gaps[parent_readme].append(child.rsplit("/", 1)[-1])
        child_targets = {
            posixpath.normpath(f"{SUBTREE}/{child}/" + t)
            for t in _md_link_targets(child_readme)
        }
        parent_abs = (
            f"{SUBTREE}/{parent}/README.md" if parent else f"{SUBTREE}/README.md"
        )
        if parent_abs not in child_targets:
            back_gaps.append(child_readme)

    total = sum(len(v) for v in parent_gaps.values()) + len(back_gaps)
    print(
        f"edges: {len(edges)} ; missing parent->child: "
        f"{sum(len(v) for v in parent_gaps.values())} ; "
        f"missing child->parent: {len(back_gaps)}"
    )
    if total == 0:
        print("tree already links both ways everywhere — nothing to do")
        return 0

    for readme, children in sorted(parent_gaps.items()):
        print(f"  {readme}: +{len(children)} child link(s)")
        if args.check:
            continue
        text, crlf = _read(readme)
        nl = "\r\n" if crlf else "\n"
        _write(readme, _add_child_list(text, nl, children), crlf)

    for readme in sorted(back_gaps):
        rel = readme[len(SUBTREE) + 1 : -len("/README.md")]
        parent = rel.rsplit("/", 1)[0] if "/" in rel else SUBTREE
        print(f"  {readme}: +Parent line -> {parent}")
        if args.check:
            continue
        text, crlf = _read(readme)
        nl = "\r\n" if crlf else "\n"
        _write(readme, _add_back_link(text, nl, parent), crlf)

    if args.check:
        print(f"--check: {total} edit(s) would be made, none applied")
    else:
        print(f"applied: {total} edit(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
