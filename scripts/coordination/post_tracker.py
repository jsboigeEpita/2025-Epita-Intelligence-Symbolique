"""Scanned posting helper (#3551): no text reaches GitHub unscanned.

Ports the coordinator seat's scratch helper (``post_tracker.sh``, 13/11)
into a tracked module, with the two corrections of the 18/11 dispatch:

- the writing account's token is injected per command (``GH_TOKEN`` in the
  environment of that ONE call, resolved through ``gh auth token``), never
  through a global ``gh auth switch``, and never printed;
- the bare 8-hex refusal is per TOKEN: a longer hex run (a quoted commit
  sha) on the same line does not excuse a document id beside it.

The repository scanner's rules are NOT redefined here — this module calls
``scripts/security/scan_indexed_surfaces.py`` and adds one net on top (the
document-id shape that scanner does not know). The ``gh`` call sits behind
``_gh`` so tests can replace it; the helper never merges and never pushes.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:  # direct CLI execution: script dir is sys.path[0]
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.security.scan_indexed_surfaces import scan_text  # noqa: E402

_HEX_RUN = re.compile(r"[0-9a-f]+")
_DEFAULT_NUMBERS = _REPO_ROOT / ".tmp" / "post_tracker_numbers.tsv"


def _hex_token_refusals(text: str) -> list[int]:
    """Line numbers (1-based) carrying a bare 8-hex token, letters AND digits.

    Per token, never per line: an 8-hex document id is refused even when a
    longer hex run (a quoted commit sha) sits on the same line — the token
    is the shape that identifies one encrypted document. An all-digit run
    (a date) and an all-letter run are not that shape.
    """
    refused: list[int] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for run in _HEX_RUN.findall(line):
            if (
                len(run) == 8
                and any(c in "0123456789" for c in run)
                and any(c in "abcdef" for c in run)
            ):
                refused.append(lineno)
                break
    return refused


def scan_string(text: str) -> list[str]:
    """Refusals for a text: the repository scanner first, the 8-hex net second."""
    refusals: list[str] = []
    hits = scan_text(text)
    if hits:
        refusals.append(f"repository scanner: {hits} hit(s)")
    lines = _hex_token_refusals(text)
    if lines:
        refusals.append(f"bare 8-hex token (letter and digit) on lines {lines}")
    return refusals


def _token_for(user: str) -> subprocess.CompletedProcess[str]:
    """Resolve one account's token without displaying it (#3551).

    Returns the raw ``gh auth token`` result; the caller extracts stdout —
    the token never transits argv, an error message or a log line.
    """
    return subprocess.run(
        ["gh", "auth", "token", "--user", user],
        capture_output=True,
        text=True,
        check=True,
    )


def _gh(
    args: list[str], *, env: dict[str, str] | None = None, input: str | None = None
) -> subprocess.CompletedProcess[str]:
    """The single gh seam: tests replace this function."""
    return subprocess.run(
        ["gh", *args], capture_output=True, text=True, env=env, input=input
    )


def _run_gh(
    args: list[str], *, repo: str | None, user: str | None, input: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run one gh command against ``repo``; the account rides GH_TOKEN (#3551).

    ``-R`` rides at the tail: the seam's first argument stays the gh verb,
    which is what the tests pin.

    The default repository is resolved HERE, not in main(): every posting
    command scans before reaching this point, so a refused draft never
    costs a gh call — the 19/11 review of #3635.
    """
    repo = _resolve_repo(repo)
    env = dict(os.environ)
    if user is not None:
        env["GH_TOKEN"] = _token_for(user).stdout.strip()
    return _gh([*args, "-R", repo], env=env, input=input)


def _fail(refusals: list[str], what: str) -> int:
    print(f"REFUSED — {what} not posted:", file=sys.stderr)
    for r in refusals:
        print(f"  {r}", file=sys.stderr)
    return 3


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _resolve_repo(repo: str | None) -> str:
    if repo:
        return repo
    proc = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def cmd_scan(paths: list[Path]) -> int:
    rc = 0
    for path in paths:
        refusals = scan_string(_read(path))
        if refusals:
            rc = 1
            _fail(refusals, str(path))
    if rc == 0:
        print(f"all clean ({len(paths)} files)")
    return rc


def cmd_new(
    draft: Path, *, labels: str, repo: str | None, user: str | None, numbers: Path
) -> int:
    text = _read(draft)
    first, _, rest = text.partition("\n")
    title = first.removeprefix("TITLE:").strip()
    if not title:
        print(f"no TITLE in {draft}", file=sys.stderr)
        return 2
    body = rest.lstrip("\n")
    for what, candidate in ((str(draft) + " (title)", title), (str(draft), body)):
        refusals = scan_string(candidate)
        if refusals:
            return _fail(refusals, what)
    args = ["issue", "create", "--title", title, "--body-file", "-"]
    if labels:
        args += ["--label", labels]
    proc = _run_gh(args, repo=repo, user=user, input=body)
    if proc.returncode != 0:
        print(proc.stderr.strip(), file=sys.stderr)
        return 5
    number = proc.stdout.strip().rsplit("/", 1)[-1]
    numbers.parent.mkdir(parents=True, exist_ok=True)
    with open(numbers, "a", encoding="utf-8") as fh:
        fh.write(f"{draft.stem}\t{number}\n")
    print(f"{draft.stem} -> #{number}")
    return 0


def cmd_comment(number: int, path: Path, *, repo: str | None, user: str | None) -> int:
    return _post_text(
        ["issue", "comment", str(number), "--body-file", "-"],
        path,
        repo=repo,
        user=user,
    )


def cmd_title(number: int, title: str, *, repo: str | None, user: str | None) -> int:
    refusals = scan_string(title)
    if refusals:
        return _fail(refusals, f"title of #{number}")
    proc = _run_gh(
        ["issue", "edit", str(number), "--title", title], repo=repo, user=user
    )
    return _report(proc)


def cmd_body(number: int, path: Path, *, repo: str | None, user: str | None) -> int:
    return _post_text(
        ["issue", "edit", str(number), "--body-file", "-"], path, repo=repo, user=user
    )


def cmd_close(
    number: int, path: Path, *, reason: str, repo: str | None, user: str | None
) -> int:
    comment = _read(path)
    refusals = scan_string(comment)
    if refusals:
        return _fail(refusals, str(path))
    proc = _run_gh(
        ["issue", "close", str(number), "--reason", reason, "--comment", comment],
        repo=repo,
        user=user,
    )
    return _report(proc)


def _post_text(
    args: list[str], path: Path, *, repo: str | None, user: str | None
) -> int:
    text = _read(path)
    refusals = scan_string(text)
    if refusals:
        return _fail(refusals, str(path))
    proc = _run_gh(args, repo=repo, user=user, input=text)
    return _report(proc)


def _report(proc: subprocess.CompletedProcess[str]) -> int:
    if proc.returncode != 0:
        print(proc.stderr.strip(), file=sys.stderr)
        return 5
    out = proc.stdout.strip().splitlines()
    if out:
        print(out[-1])
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repo", help="owner/repo; default: gh repo view")
    parser.add_argument("--user", help="writing account; its token rides GH_TOKEN")
    parser.add_argument(
        "--numbers",
        type=Path,
        default=_DEFAULT_NUMBERS,
        help="tsv of draft-name to created-issue-number",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="scan files; exit 1 on any refusal")
    p_scan.add_argument("paths", nargs="+", type=Path)

    p_new = sub.add_parser("new", help="create an issue from TITLE: + body")
    p_new.add_argument("draft", type=Path)
    p_new.add_argument("labels", nargs="?", default="")

    p_comment = sub.add_parser("comment", help="comment on an issue")
    p_comment.add_argument("number", type=int)
    p_comment.add_argument("path", type=Path)

    p_title = sub.add_parser("title", help="edit an issue title")
    p_title.add_argument("number", type=int)
    p_title.add_argument("title")

    p_body = sub.add_parser("body", help="edit an issue body")
    p_body.add_argument("number", type=int)
    p_body.add_argument("path", type=Path)

    p_close = sub.add_parser("close", help="close with a scanned comment")
    p_close.add_argument("number", type=int)
    p_close.add_argument("path", type=Path)
    p_close.add_argument(
        "reason", nargs="?", default="completed", choices=["completed", "not planned"]
    )

    ns = parser.parse_args(argv)
    if ns.cmd == "scan":
        return cmd_scan(ns.paths)
    if ns.cmd == "new":
        return cmd_new(
            ns.draft, labels=ns.labels, repo=ns.repo, user=ns.user, numbers=ns.numbers
        )
    if ns.cmd == "comment":
        return cmd_comment(ns.number, ns.path, repo=ns.repo, user=ns.user)
    if ns.cmd == "title":
        return cmd_title(ns.number, ns.title, repo=ns.repo, user=ns.user)
    if ns.cmd == "body":
        return cmd_body(ns.number, ns.path, repo=ns.repo, user=ns.user)
    return cmd_close(ns.number, ns.path, reason=ns.reason, repo=ns.repo, user=ns.user)


if __name__ == "__main__":
    sys.exit(main())
