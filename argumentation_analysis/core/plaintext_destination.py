"""Where corpus-derived plaintext may be written (#2738).

The dataset is tracked only in encrypted form. Several writers put its
plaintext, or text excerpts derived from it, at a path their caller chooses:
definition exports, unencrypted saves and their fallbacks, analysis traces.
A path inside a git work tree that is not ignored makes that plaintext one
``git add`` away from the history. This module is the single check those
writers call before they open the file.
"""

import subprocess
from pathlib import Path
from typing import Optional, Union

# A file name that the repository ignores wherever it is created
# (``*_unencrypted*`` in .gitignore). Default for interactive exports.
DEFAULT_PLAINTEXT_EXPORT_PATH = "./extract_definitions_unencrypted.json"


class PlaintextDestinationError(ValueError):
    """The destination could put plaintext into a git work tree."""


def _enclosing_work_tree(start: Path) -> Optional[Path]:
    """Nearest directory at or above *start* that holds a ``.git`` entry.

    ``.git`` is a directory in a main clone and a file in a linked worktree
    or a submodule; both count.
    """
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def check_plaintext_destination(path: Union[str, Path]) -> Path:
    """Return *path* resolved, or raise if plaintext written there is stageable.

    A destination outside every git work tree is accepted. Inside one, it is
    accepted only when ``git check-ignore`` says the path is ignored; a tracked
    file is never ignored, so overwriting one with plaintext is refused too.
    When git cannot answer, the write is refused: an unverified destination is
    treated as an unsafe one.
    """
    target = Path(path).resolve()
    root = _enclosing_work_tree(target.parent)
    if root is None:
        return target
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "-q", str(target)],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise PlaintextDestinationError(
            f"Refusing to write plaintext to {target}: it is inside the git "
            f"work tree {root} and git could not say whether it is ignored "
            f"({exc})."
        ) from exc
    if proc.returncode == 0:
        return target
    if proc.returncode == 1:
        raise PlaintextDestinationError(
            f"Refusing to write plaintext to {target}: it is inside the git "
            f"work tree {root} and is not ignored, so it could be committed. "
            f"Write it outside the repository, or under an ignored name or "
            f"directory (for example '*_unencrypted*' or "
            f"'argumentation_analysis/evaluation/results/')."
        )
    raise PlaintextDestinationError(
        f"Refusing to write plaintext to {target}: 'git check-ignore' failed "
        f"in {root} (exit {proc.returncode}: {proc.stderr.strip()})."
    )
