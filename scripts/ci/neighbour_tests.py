#!/usr/bin/env python
"""The neighbours of a change: the tests to run before trusting a targeted green.

A green run of the tests that name what you touched says nothing about the
tests beside them. Four gate reds came from that gap after green targeted
runs, two of them on the same guard (`docs/guides/MEASUREMENT_DISCIPLINE.md`,
§3.2). The rule was written down each time; this script derives the set, so
the rule no longer depends on being remembered.

From the files a change touches it builds three groups of test files:

``touched``
    the test files in the change, and every test under a touched ``conftest.py``.
``mentions``
    the test files whose source names a touched module or file: a ``.py``
    file by its module name, any other file by its file name. A name that
    more than ``GENERIC_THRESHOLD`` test files carry is narrowed to its
    qualified forms (``parent.name``, ``parent/name``), and the output says
    so.
``population``
    the test files that walk the tree instead of importing one module (they
    call ``git ls-files``, ``rglob``, ``os.walk``, ``glob``, ``iterdir`` or
    ``ast.parse``). Their verdict depends on files they never name, so they
    are neighbours of every change. This is a reading of the test's source,
    not a proof: a guard that walks the tree through a helper defined
    elsewhere is not seen. ``KNOWN_POPULATION_GUARDS`` in the test file pins
    the ones a red has already been paid for.

Only the files under the paths the gate runs are kept (the positional paths
of the one pytest call of ``.github/workflows/ci.yml`` that carries the
gate's marker filter); the others are counted and listed, not run.

    python scripts/ci/neighbour_tests.py              # the set, and the command
    python scripts/ci/neighbour_tests.py --run -n 4   # run it, gate's filter on
    python scripts/ci/neighbour_tests.py --paths      # one path per line
    python scripts/ci/neighbour_tests.py --files a.py docs/b.md

The change is ``<base>...HEAD`` (default base ``origin/main``) plus what the
working tree holds that is not committed: staged, unstaged and untracked.

No model, no network. The run keeps the gate's marker filter, but the filter
is not an egress guard: read the ``LLM egress (#1787)`` line of the run before
its pass count. On a linked git worktree the JVM tests and the key-gated tests
skip in silence — read ``-rs`` (§3.3 of the same page).

Exit code: 0, or pytest's with ``--run``; 2 when git cannot answer.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"

# The two marks of the gate's pytest call, the same ones
# tests/unit/test_band_argv_matches_gate_1867.py reads it by.
PYTEST_CALL = "--no-capture-output pytest "
GATE_FILTER = "not slow and not requires_api"

# A name carried by more test files than this is not a neighbour relation,
# it is vocabulary (`utils`, `README.md`): it is narrowed to qualified forms.
GENERIC_THRESHOLD = 150

# What a test that walks the tree calls. Read in the test's source.
POPULATION = re.compile(
    r"ls-files|\.rglob\(|os\.walk\(|\.glob\(|\.iterdir\(|ast\.parse\("
)

# Windows refuses a command line near 32 767 characters; pytest reads the
# rest from an @file.
MAX_COMMAND_CHARS = 24_000

EXIT_OK = 0
EXIT_GIT = 2


class GitError(RuntimeError):
    """git did not answer: there is no change to derive neighbours from."""


def is_test_file(path: str) -> bool:
    """A file pytest collects: ``test_*.py`` or ``*_test.py`` under ``tests/``."""
    pure = PurePosixPath(path)
    if not pure.parts or pure.parts[0] != "tests" or pure.suffix != ".py":
        return False
    return pure.name.startswith("test_") or pure.stem.endswith("_test")


def is_population_guard(source: str) -> bool:
    """The test's source calls something that walks the tree."""
    return POPULATION.search(source) is not None


def under(path: str, roots: Iterable[str]) -> bool:
    """``path`` is one of ``roots`` or sits below one of them."""
    for root in roots:
        clean = root.rstrip("/")
        if path == clean or path.startswith(clean + "/"):
            return True
    return False


def gate_paths(ci_text: str) -> List[str]:
    """Positional paths of the gate's pytest call, up to its first option.

    Exactly one line of the workflow carries both marks; anything else means
    the workflow changed shape and the instrument must say so, not guess.
    """
    calls = [
        line
        for line in ci_text.splitlines()
        if PYTEST_CALL in line and GATE_FILTER in line
    ]
    if len(calls) != 1:
        raise ValueError(f"expected 1 gate pytest call in ci.yml, found {len(calls)}")
    paths: List[str] = []
    for arg in calls[0].split(PYTEST_CALL, 1)[1].split():
        if arg.startswith("-"):
            break
        paths.append(arg)
    return paths


@dataclass(frozen=True)
class Token:
    """What a touched file is called in a test's source."""

    path: str
    name: str
    qualified: Tuple[str, ...]
    word: bool  # a module name is matched as a word, a file name as written


def token_for(path: str) -> Optional[Token]:
    """The name tests use for ``path``, or ``None`` for a test file.

    A module is named by its stem (``reading_window``), a package's
    ``__init__`` by the package, any other file by its file name
    (``ci.yml``). The qualified forms are what is left when the name alone is
    vocabulary.
    """
    pure = PurePosixPath(path)
    if is_test_file(path) or not pure.name:
        return None
    parent = pure.parent.name
    if pure.suffix == ".py":
        if pure.stem == "__init__":
            if not parent:
                return None
            grand = pure.parent.parent.name
            qualified = (f"{grand}.{parent}", f"{grand}/{parent}") if grand else ()
            return Token(path, parent, qualified, True)
        qualified = (f"{parent}.{pure.stem}", f"{parent}/{pure.stem}") if parent else ()
        return Token(path, pure.stem, qualified, True)
    qualified = (f"{parent}/{pure.name}",) if parent else ()
    return Token(path, pure.name, qualified, False)


def _mentions(token: Token, sources: Mapping[str, str]) -> List[str]:
    if token.word:
        # A module is named bare (`import x`, `from pkg import x`), at the end
        # of a dotted path or inside a patched string: always as a word.
        pattern = re.compile(r"\b" + re.escape(token.name) + r"\b")
        return sorted(path for path, text in sources.items() if pattern.search(text))
    return sorted(path for path, text in sources.items() if token.name in text)


def _qualified_mentions(token: Token, sources: Mapping[str, str]) -> List[str]:
    return sorted(
        path
        for path, text in sources.items()
        if any(form in text for form in token.qualified)
    )


@dataclass
class Neighbours:
    """The three groups, and what was left out and why."""

    touched: List[str] = field(default_factory=list)
    mentions: Dict[str, List[str]] = field(default_factory=dict)
    population: List[str] = field(default_factory=list)
    narrowed: Dict[str, int] = field(default_factory=dict)
    outside_gate: List[str] = field(default_factory=list)
    conftest_roots: List[str] = field(default_factory=list)

    def run_paths(self) -> List[str]:
        """Every path to hand to pytest, each once, directories first."""
        files = set(self.touched) | set(self.population)
        for found in self.mentions.values():
            files.update(found)
        files = {path for path in files if not under(path, self.conftest_roots)}
        return sorted(self.conftest_roots) + sorted(files)


def select(
    touched: Sequence[str],
    sources: Mapping[str, str],
    gate: Sequence[str],
    threshold: int = GENERIC_THRESHOLD,
) -> Neighbours:
    """The neighbours of ``touched`` among the test files of ``sources``.

    ``sources`` maps every test file's path to its text; ``gate`` is the list
    of paths the gate runs. Pure: no git, no disk.
    """
    result = Neighbours()
    in_gate = {path: text for path, text in sources.items() if under(path, gate)}
    outside = set()

    def keep(paths: Iterable[str]) -> List[str]:
        kept = []
        for path in paths:
            if path in in_gate:
                kept.append(path)
            elif path in sources:
                outside.add(path)
        return kept

    for path in sorted(set(touched)):
        pure = PurePosixPath(path)
        if is_test_file(path):
            result.touched.extend(keep([path]))
            continue
        if pure.name == "conftest.py" and pure.parts and pure.parts[0] == "tests":
            # A conftest reaches every test below it, whatever they mention:
            # the neighbour is its directory, as far as the gate runs it. A
            # conftest above the gate's paths (tests/conftest.py) makes the
            # neighbour set the gate's own paths, never `tests/` whole.
            root = pure.parent.as_posix()
            if under(root, gate):
                result.conftest_roots.append(root)
            else:
                result.conftest_roots.extend(
                    g.rstrip("/") for g in gate if under(g.rstrip("/"), [root])
                )
            continue
        token = token_for(path)
        if token is None:
            continue
        found = _mentions(token, sources)
        if len(found) > threshold and token.qualified:
            result.narrowed[path] = len(found)
            found = _qualified_mentions(token, sources)
        result.mentions[path] = keep(found)

    result.population = keep(
        path for path, text in sorted(sources.items()) if is_population_guard(text)
    )
    result.touched = sorted(set(result.touched))
    result.outside_gate = sorted(outside)
    return result


# --------------------------------------------------------------------------
# git and disk
# --------------------------------------------------------------------------


def _git(args: Sequence[str], root: Path) -> List[str]:
    try:
        proc = subprocess.run(
            ["git", "-c", "core.quotepath=off", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        raise GitError(str(exc)) from exc
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {proc.stderr.strip()}")
    return [line for line in proc.stdout.splitlines() if line.strip()]


def changed_files(base: str, root: Path = REPO_ROOT) -> List[str]:
    """What ``base...HEAD`` touches, plus what the working tree has not committed."""
    committed = _git(["diff", "--name-only", f"{base}...HEAD"], root)
    uncommitted = _git(["diff", "--name-only", "HEAD"], root)
    untracked = _git(["ls-files", "--others", "--exclude-standard"], root)
    return sorted(set(committed) | set(uncommitted) | set(untracked))


def test_sources(root: Path = REPO_ROOT) -> Dict[str, str]:
    """Path -> text of every test file git knows or would add, present on disk."""
    listed = _git(["ls-files", "--", "tests"], root) + _git(
        ["ls-files", "--others", "--exclude-standard", "--", "tests"], root
    )
    sources: Dict[str, str] = {}
    for path in sorted(set(listed)):
        if not is_test_file(path):
            continue
        try:
            sources[path] = (root / path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue  # deleted in the working tree: nothing to run
    return sources


def pytest_command(paths: Sequence[str], workers: int = 0) -> List[str]:
    """The pytest call for ``paths``, the gate's marker filter on."""
    command = [sys.executable, "-m", "pytest", *paths, "-m", GATE_FILTER, "-q", "-rs"]
    if workers:
        command += ["-n", str(workers)]
    return command


def report(found: Neighbours, touched: Sequence[str], base: str) -> str:
    """What a reader needs before running: the groups, and what was left out."""
    paths = found.run_paths()
    mention_files = sorted({p for group in found.mentions.values() for p in group})
    lines = [
        f"change: {len(touched)} file(s) against {base} (committed, staged, "
        "unstaged, untracked)",
        f"touched tests: {len(found.touched)}",
        f"tests that name a touched file: {len(mention_files)}",
        f"population guards (walk the tree): {len(found.population)}",
    ]
    if found.conftest_roots:
        lines.append(
            f"conftest touched: every test the gate runs under "
            f"{len(found.conftest_roots)} path(s) is a neighbour — "
            + ", ".join(found.conftest_roots[:4])
            + (" …" if len(found.conftest_roots) > 4 else "")
        )
    for path, count in sorted(found.narrowed.items()):
        token = token_for(path)
        forms = " or ".join(token.qualified) if token else ""
        lines.append(
            f"narrowed: {count} test files name `{token.name if token else path}` "
            f"— kept only those naming {forms}"
        )
    silent = [path for path, group in sorted(found.mentions.items()) if not group]
    if silent:
        lines.append(
            f"no test names {len(silent)} touched file(s): "
            + ", ".join(silent[:8])
            + (" …" if len(silent) > 8 else "")
        )
    if found.outside_gate:
        lines.append(
            f"outside the gate's paths, not run: {len(found.outside_gate)} — "
            + ", ".join(found.outside_gate[:5])
            + (" …" if len(found.outside_gate) > 5 else "")
        )
    lines.append(f"neighbour set: {len(paths)} path(s)")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="The tests to run before trusting a targeted green run."
    )
    parser.add_argument("--base", default="origin/main", help="diff base")
    parser.add_argument(
        "--files", nargs="+", help="use this list instead of a git diff"
    )
    parser.add_argument("--run", action="store_true", help="run the set")
    parser.add_argument(
        "--paths", action="store_true", help="print the paths only, one per line"
    )
    parser.add_argument(
        "-n", dest="workers", type=int, default=0, help="xdist workers for --run"
    )
    args = parser.parse_args(argv)

    try:
        touched = (
            sorted({Path(name).as_posix() for name in args.files})
            if args.files
            else changed_files(args.base)
        )
        sources = test_sources()
    except GitError as exc:
        print(f"git did not answer: {exc}", file=sys.stderr)
        return EXIT_GIT
    gate = gate_paths(CI_YML.read_text(encoding="utf-8"))
    found = select(touched, sources, gate)
    paths = found.run_paths()

    if args.paths:
        print("\n".join(paths))
        return EXIT_OK
    print(report(found, touched, args.base))
    if not paths:
        return EXIT_OK

    command = pytest_command(paths, args.workers)
    if not args.run:
        print("run it: python scripts/ci/neighbour_tests.py --run -n 4")
        print(
            f'which is: python -m pytest <the {len(paths)} paths> -m "{GATE_FILTER}" '
            "-q -rs -n 4"
        )
        return EXIT_OK

    if sum(len(arg) + 1 for arg in command) > MAX_COMMAND_CHARS:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".args", delete=False, encoding="utf-8"
        ) as handle:
            handle.write("\n".join(paths))
        command = pytest_command([f"@{handle.name}"], args.workers)
    print("read the `LLM egress (#1787)` line before the pass count", flush=True)
    return subprocess.run(command, cwd=REPO_ROOT, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
