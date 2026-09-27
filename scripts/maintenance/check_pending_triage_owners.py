"""Check that every PENDING_TRIAGE owner issue is still open (#2623).

The #2623 defect: six PENDING_TRIAGE entries in
``tests/unit/argumentation_analysis/orchestration/test_one_capability_surface_1842.py``
named #2137 as their owner, and #2137 was closed without clearing them — the
guard stayed green because it checks what an entry names (component,
capability), never whether the owner can still act. A hermetic test cannot
read GitHub issue state, so owner liveness has to be a coordinator-side
measurement, not an assumption.

This script is that measurement:

    python scripts/maintenance/check_pending_triage_owners.py

It parses the map from the source (AST, no import), asks ``gh`` for the
state of every owner it names, and exits non-zero when a CLOSED owner still
owns entries. Closing an owner issue therefore requires the map to stop
naming it first (``git grep '"#N"'`` on the guard file comes back empty) —
the rule this script enforces, so nobody has to remember it.

Exit codes: 0 all owners open (or map empty with --allow-empty), 1 a closed
owner still owns entries, 2 the map could not be read or ``gh`` failed.
"""

import argparse
import ast
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

GUARD_RELATIVE = Path(
    "tests/unit/argumentation_analysis/orchestration/"
    "test_one_capability_surface_1842.py"
)


def read_pending_triage(guard_path: Path) -> dict[str, list[tuple[str, str]]]:
    """Owner issue -> [(component, capability), ...], parsed by AST.

    Raises SystemExit(2) when the map is missing or malformed: a silent
    empty read here would be the same blind spot the script exists to close.
    """
    tree = ast.parse(guard_path.read_text(encoding="utf-8-sig"))
    assignment: ast.AnnAssign | None = None
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "PENDING_TRIAGE"
        ):
            assignment = node
            break
    if assignment is None or not isinstance(assignment.value, ast.Dict):
        print(f"FAIL: no PENDING_TRIAGE dict found in {guard_path}")
        raise SystemExit(2)

    entries: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for key, value in zip(assignment.value.keys, assignment.value.values):
        parts: list[str] = []
        if isinstance(key, ast.Tuple) and len(key.elts) == 2:
            for element in key.elts:
                if isinstance(element, ast.Constant) and isinstance(
                    element.value, str
                ):
                    parts.append(element.value)
        if len(parts) != 2 or not (
            isinstance(value, ast.Constant) and isinstance(value.value, str)
        ):
            print(
                f"FAIL: unreadable PENDING_TRIAGE entry near line "
                f"{getattr(key, 'lineno', '?')} in {guard_path}"
            )
            raise SystemExit(2)
        component, capability = parts
        entries[value.value].append((component, capability))
    return entries


def issue_state(owner: str, repo: str | None) -> tuple[str, str]:
    """(state, title) of an issue number like '#1604', via gh."""
    number = owner.lstrip("#")
    cmd = ["gh", "issue", "view", number, "--json", "state,title"]
    if repo:
        cmd.extend(["--repo", repo])
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=30
        )
    except FileNotFoundError:
        print("FAIL: gh not found on PATH — owner liveness cannot be measured")
        raise SystemExit(2)
    except subprocess.CalledProcessError as e:
        print(f"FAIL: gh could not read issue {owner}: {e.stderr.strip()}")
        raise SystemExit(2)
    payload = json.loads(out.stdout)
    return payload.get("state", "UNKNOWN"), payload.get("title", "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--guard",
        type=Path,
        default=None,
        help="path to the guard file (default: <repo root>/%s)" % GUARD_RELATIVE,
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="repo for gh (default: the repository of the cwd)",
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="succeed when PENDING_TRIAGE is empty (default: fail — an empty "
        "map is more likely a parse drift than finished triage)",
    )
    args = parser.parse_args()

    guard = args.guard or Path.cwd().joinpath(GUARD_RELATIVE)
    if not guard.is_file():
        print(f"FAIL: guard file not found: {guard}")
        return 2

    entries = read_pending_triage(guard)
    if not entries:
        print("PENDING_TRIAGE is empty — every declared capability has a demander.")
        return 0 if args.allow_empty else 2

    closed_owners = []
    for owner in sorted(entries):
        state, title = issue_state(owner, args.repo)
        count = len(entries[owner])
        marker = "OK  " if state == "OPEN" else "CLOSED"
        print(
            f"{marker} {owner:>8}  {count} entr{'y' if count == 1 else 'ies'}  "
            f"[{state}] {title}"
        )
        if state != "OPEN":
            closed_owners.append(owner)

    if closed_owners:
        print(
            "\nFAIL: closed owner(s) still owning PENDING_TRIAGE entries: "
            + ", ".join(closed_owners)
            + ". Re-own each entry to an OPEN issue that names it, or finish "
            "its triage — the guard map must never point at a closed issue "
            "(the #2623 defect)."
        )
        return 1
    print("\nAll PENDING_TRIAGE owners are open.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
