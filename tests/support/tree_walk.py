# -*- coding: utf-8 -*-
"""#2607: how a test walks the tests tree when it walks it itself.

``Path.rglob`` does not apply ``norecursedirs``: a guard that walks
``(ROOT / "tests").rglob("*.py")`` enters every ``_``-prefixed directory,
whereas collection skips them (``pytest.ini``). Measured 2026-09-26 on a tree
holding ``_probe_x/p.py`` and ``a/t1.py``: ``rglob`` returns both.

That alone is only untidy. It becomes a race through the probes of
``tests/nested_pytest.py``: ``run_probe`` creates
``tests/_probe_<label>_<uuid>/``, runs a session inside it (about 20 s), then
deletes it. A walk that has already listed the directory and tries to enter it
after the deletion raises ``FileNotFoundError``. Replayed on a loop (248
creations against 400 walks): **97** of the walks raised. So a test that walks
``tests/`` on one xdist worker fails intermittently while a probe runs on
another — the failure #2607 closed, first seen on
``test_ci_guard_signature_contract_1873.py``.

The probes cannot simply move out of ``tests/``: they live there so that
``tests/conftest.py`` applies to them, which is what
``test_worker_nested_session_jvm_2530.py`` measures (its probe uses the
``jvm_session`` fixture). The exclusion therefore belongs to the walk, and it
is written once here rather than in each caller.

Two rules, and the second is the one that keeps every caller's coverage:

- ``iter_files`` skips the probe directories, named by ``PROBE_PREFIX``. It
  does **not** skip every ``_``-prefixed directory: ``tests/_archived/`` is
  stable, and a guard that walks ``tests/`` on purpose may need it — the real
  name sweep of ``test_person_sweep_2004.py`` is one. Skipping ``_*`` would
  quietly shrink such a guard's coverage to remove a race it can be spared.
- A directory that disappears mid-walk is an ordinary event, not an error, so
  a walk survives whatever else removes directories under ``tests/`` while it
  runs. This is the rule that removes the raise; the probe prefix is what
  keeps a transient probe's content out of a verdict.
"""

import configparser
from pathlib import Path

# The directory prefix ``tests/nested_pytest.py`` gives its probes. They are
# the only directories under ``tests/`` created and deleted while the suite
# runs, so they are the only ones a walk has to be spared.
PROBE_PREFIX = "_probe_"


def iter_files(root, pattern="*.py", skip_prefixes=(PROBE_PREFIX,)):
    """The files under ``root`` matching ``pattern``, as ``Path`` objects.

    ``root`` may be a ``str`` or a ``Path``. ``pattern`` is a shell pattern
    matched against the name, as ``Path.glob`` reads it. A **directory** whose
    name starts with one of ``skip_prefixes`` is not entered; a **file** is
    matched whatever its name starts with (``rglob`` returns ``__init__.py``,
    and so does this). A directory that cannot be listed — deleted since its
    parent was read, or unreadable — is passed over. Symbolic links to
    directories are not followed, as ``rglob`` does not follow them either.
    """
    stack = [Path(root)]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir())
        except OSError:
            # Deleted between the parent's listing and this call, or
            # unreadable. A walk reports files, not the directories it could
            # not read.
            continue
        for entry in entries:
            try:
                is_dir = entry.is_dir() and not entry.is_symlink()
            except OSError:
                continue
            if is_dir:
                if entry.name.startswith(tuple(skip_prefixes)):
                    continue
                stack.append(entry)
            elif entry.match(pattern):
                yield entry


def prefix_is_skipped_by_collection(pytest_ini, prefix=PROBE_PREFIX):
    """Whether ``pytest.ini``'s ``norecursedirs`` keeps collection out of a
    directory named ``prefix``, so a guard can assert that the prefix a walk
    skips is one collection skips too — read back from the file rather than
    restated, since a restated convention is the one that drifts.

    Returns ``(verdict, entries)``: the ``norecursedirs`` entries it read
    (``[".", "_"]`` for the repository's ``.*`` and ``_*``), so a failure
    names what was actually there. ``verdict`` is ``False`` when the file has
    no such section, which is a failure worth seeing, not an exemption.
    """
    parser = configparser.ConfigParser()
    try:
        with open(pytest_ini, encoding="utf-8") as handle:
            parser.read_file(handle)
    except (OSError, configparser.Error):
        return False, []
    entries = parser.get("pytest", "norecursedirs", fallback="").split()
    return (
        any(entry.endswith("*") and prefix.startswith(entry[:-1]) for entry in entries),
        entries,
    )
