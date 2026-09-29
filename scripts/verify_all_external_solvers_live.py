"""Firsthand, NO-MOCKS sweep of EVERY external solver path (#2851).

For each tool the script prints the RESOLVED PATH, the VERSION, and the
verdict on a known SAT/UNSAT (or inconsistent/consistent) pair, through the
production code. A tool that does not decide — wrong verdict, honest None,
or a raise — fails the run: the process EXITS NON-ZERO naming the failures
(#2851 DoD-1: an import or a file on disk is not "operational").

Covers: JVM/Tweety version, JPype, EProver (FOL default), Prover9 (FOL alt),
Tweety FOL fallback, PySAT (PL, EVERY backend including cryptominisat5 —
provisioned via pycryptosat in environment.yml), the SAT handler
(``_invoke_sat``), MaxSAT (RC2), MUS/MARCO (Z3), modal consistency (default
SimpleMlReasoner AND the SPASS adapter when a vendored binary answers),
clingo JVM (ASP) and clingo Python. A lock-drift section closes the run:
what the interpreter's env carries versus ``conda-lock.yml`` (win-64), so "a
tool proven on this seat" states which env proved it.

Synthetic atoms only — no corpus. Zero LLM calls.
"""

import asyncio
import importlib.metadata as metadata
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from argumentation_analysis.core.jvm_setup import (
    initialize_jvm,
    EXTERNAL_TOOL_PATHS,
    EXTERNAL_TOOL_REJECTIONS,
    EXTERNAL_TOOL_VERSIONS,
    CLINGO_VERSION,
)  # noqa: E402
from argumentation_analysis.core.config import settings, SolverChoice  # noqa: E402
from argumentation_analysis.agents.core.logic.tweety_bridge import (
    TweetyBridge,
)  # noqa: E402

FOL_INC = "Mortal = {socrate}\ntype(Human(Mortal))\nHuman(socrate)\n!Human(socrate)"
FOL_CON = "Mortal = {socrate}\ntype(Human(Mortal))\nHuman(socrate)"
MODAL_INC = "type(Rain)\n\nRain\n!Rain\n"
MODAL_CON = "type(Rain)\ntype(Wet)\n\n[](Rain => Wet)\nRain\n"

FAILURES: "list[str]" = []


def line(label, verdict, detail=""):
    print(f"  {label:<40} verdict={verdict!r:>7}  | {detail[:80]}")


def require(label, ok, detail=""):
    """Record the verdict; a non-deciding tool fails the run."""
    mark = "DECIDES" if ok else "FAILS"
    print(f"  {label:<40} {mark}  | {detail[:80]}")
    if not ok:
        FAILURES.append(f"{label}: {detail[:120]}")


def tool_version(binary, flag="--version"):
    """Best-effort version banner of an external binary."""
    path = Path(binary) if binary else None
    if path is None:
        return "no path"
    if path.is_dir():
        return f"dir entry ({path})"  # clingo JVM path: the exe lives inside
    try:
        out = subprocess.run(
            [str(path), flag], capture_output=True, text=True, timeout=30
        )
        first = (out.stdout or out.stderr).strip().splitlines()
        return first[0][:70] if first else f"no banner (rc={out.returncode})"
    except (OSError, subprocess.SubprocessError) as exc:
        return f"{type(exc).__name__}"


def pkg_version(name):
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "ABSENT"


# ── FOL / PL through the production bridge ─────────────────────────────


def fol_under(bridge, solver_choice):
    prev = settings.solver
    settings.solver = solver_choice
    try:
        vi, _mi = bridge.check_consistency(FOL_INC, "first_order")
        vc, _mc = bridge.check_consistency(FOL_CON, "first_order")
        line(f"FOL[{solver_choice.value}] INCONSISTENT", vi)
        line(f"FOL[{solver_choice.value}] CONSISTENT", vc)
        # The contract: the contradiction must NOT come back consistent.
        require(
            f"FOL[{solver_choice.value}] decides",
            vi is False and vc is True,
            f"inc={vi!r} con={vc!r}",
        )
    except Exception as e:  # noqa: BLE001
        require(
            f"FOL[{solver_choice.value}] decides",
            False,
            f"raised {type(e).__name__}: {e}",
        )
    finally:
        settings.solver = prev


def modal_under(bridge, label, prefer_spass):
    prev_prefer = getattr(settings, "modal_prefer_spass_when_available", None)
    prev_solver = getattr(settings, "modal_solver", None)
    try:
        if prev_prefer is not None:
            settings.modal_prefer_spass_when_available = prefer_spass
        vi, mi = bridge.check_consistency(MODAL_INC, "K")
        vc, mc = bridge.check_consistency(MODAL_CON, "K")
        line(f"{label} INCONSISTENT", vi)
        line(f"{label} CONSISTENT", vc)
        require(
            f"{label} decides",
            vi is False and vc is True,
            f"inc={vi!r} con={vc!r} | {mi}",
        )
    except Exception as e:  # noqa: BLE001
        require(f"{label} decides", False, f"raised {type(e).__name__}: {e}")
    finally:
        if prev_prefer is not None:
            settings.modal_prefer_spass_when_available = prev_prefer
        if prev_solver is not None:
            settings.modal_solver = prev_solver


def pysat_backends():
    print("\n=== PySAT — every backend on a SAT and an UNSAT pair ===")
    from pysat.solvers import Solver

    backends = [
        "cadical195",
        "glucose42",
        "minisat22",
        "maplechrono",
        "lingeling",
        "cryptominisat5",
    ]
    for name in backends:
        try:
            s = Solver(name=name, bootstrap_with=[[1], [-1]])
            unsat_ok = not s.solve()
            s.delete()
            t = Solver(name=name, bootstrap_with=[[1], [2]])
            sat_ok = t.solve() and t.get_model() is not None
            t.delete()
            require(
                f"PySAT[{name}] decides",
                unsat_ok and sat_ok,
                f"unsat-pair={'OK' if unsat_ok else 'WRONG'} sat-pair={'OK' if sat_ok else 'WRONG'}",
            )
        except Exception as e:  # noqa: BLE001
            require(f"PySAT[{name}] decides", False, f"raised {type(e).__name__}: {e}")


def maxsat_and_mus():
    print("\n=== MaxSAT (RC2) and MUS/MARCO (Z3) — production paths ===")
    from argumentation_analysis.agents.core.logic.sat_handler import SATHandler

    handler = SATHandler()
    try:
        model, cost = handler.solve_maxsat([[1]], [([2], 1), ([-2], 1)])
        require(
            "MaxSAT[RC2] decides",
            model is not None and cost == 1,
            f"model={'yes' if model else 'none'} cost={cost!r} (expected cost 1)",
        )
    except Exception as e:  # noqa: BLE001
        require("MaxSAT[RC2] decides", False, f"raised {type(e).__name__}: {e}")
    try:
        mus = handler.find_mus(["p", "!p"], max_mus=2)
        require(
            "MUS/MARCO[Z3] decides",
            bool(mus),
            f"MUS={mus!r} (expected a non-empty list over ['p', '!p'])",
        )
    except Exception as e:  # noqa: BLE001
        require("MUS/MARCO[Z3] decides", False, f"raised {type(e).__name__}: {e}")


def clingo_python():
    print("\n=== clingo — Python binding ===")
    try:
        import clingo

        ctl = clingo.Control()
        ctl.add("base", [], "a. b :- a.")
        ctl.ground([("base", [])])
        names: set = set()
        ctl.solve(
            on_model=lambda m: names.update(s.name for s in m.symbols(atoms=True))
        )
        require(
            "clingo[python] decides",
            {"a", "b"} <= names,
            f"stable-model atoms={sorted(names)} version={pkg_version('clingo')}",
        )
    except Exception as e:  # noqa: BLE001
        require("clingo[python] decides", False, f"raised {type(e).__name__}: {e}")


def spass_state() -> "Tuple[bool, str]":
    """``(runnable, reason)`` — the adapter path is not enough: the JVM
    reasoner must say installed, and WHY it does not is part of the verdict.

    A bare bool made the seat's answer unreadable: the section printed
    "not runnable — skipped" and the run still exited 0, which under #2851
    reads as "proved nothing" silently (coordinator point 5, 2026-09-29).
    """
    try:
        import jpype
    except ImportError as e:  # noqa: BLE001
        return False, f"jpype not importable ({type(e).__name__}: {e})"
    if not jpype.isJVMStarted():
        return False, "the JVM is not started"
    path = EXTERNAL_TOOL_PATHS.get("spass")
    if not path:
        return False, "EXTERNAL_TOOL_PATHS['spass'] is empty (no vendored path)"
    try:
        reasoner_cls = jpype.JClass(
            "org.tweetyproject.logics.ml.reasoner.SPASSMlReasoner"
        )
        JString = jpype.JClass("java.lang.String")
        installed = bool(reasoner_cls(JString(path)).isInstalled())
    except Exception as e:  # noqa: BLE001
        return False, (f"the JVM reasoner raised {type(e).__name__}: {e} (path={path})")
    if not installed:
        return False, f"SPASSMlReasoner.isInstalled() is False for {path}"
    return True, f"installed at {path}"


def lock_drift_section():
    """What THIS interpreter's env carries vs conda-lock.yml (win-64)."""
    print("\n=== Lock drift (env of this interpreter vs conda-lock.yml) ===")
    lock_path = ROOT / "conda-lock.yml"
    if not lock_path.is_file():
        print("  conda-lock.yml absent — drift section skipped")
        return
    try:
        import yaml
    except ImportError:
        print("  pyyaml absent — drift section skipped")
        return
    lock = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    want = {}
    for p in lock.get("package", []):
        if p.get("platform") != "win-64":
            continue
        want[re.sub(r"[-_.]+", "-", p["name"].lower())] = p["version"]
    env_name = sys.prefix
    listed = subprocess.run(
        ["conda", "list", "-p", env_name, "--json"],
        capture_output=True,
        text=True,
        shell=True,
    )
    if listed.returncode != 0:
        print(f"  conda list failed (rc={listed.returncode}) — drift section skipped")
        return
    have = {
        re.sub(r"[-_.]+", "-", d["name"].lower()): d["version"]
        for d in json.loads(listed.stdout)
    }
    # The interpreter's own site-packages is the truth for pip layers the
    # conda list may not attribute; user-site shadowing is measured too.
    missing = sorted(n for n in want if n not in have)
    drift = sorted(
        (n, want[n], have[n]) for n in want if n in have and have[n] != want[n]
    )
    print(
        f"  env={env_name}\n  lock_pkgs={len(want)} conda_listed={len(have)} "
        f"missing={len(missing)} version_drift={len(drift)}"
    )
    focus = (
        "clingo",
        "python-sat",
        "pycryptosat",
        "jpype1",
        "openjdk",
        "pytest",
        "z3-solver",
        "semantic-kernel",
        "openai",
    )
    for n, w, h in drift:
        if n in focus:
            print(f"    DRIFT {n}: lock {w} / conda-list {h}")
    for n in missing:
        if n in focus:
            print(f"    MISSING {n}: lock {want[n]}")
    print(
        "  NOTE: conda list measures the conda env; the interpreter resolves"
        " user-site FIRST when present (the #2851 po-2023 census) — the"
        " pkg_version lines above are the EFFECTIVE versions."
    )
    print(
        "  SEAT-LOCAL, not a lock defect (coordinator point 6, 2026-09-29):"
        " on po-2023 the env's site-packages is not writable without"
        " elevation, so pip installs into"
        " %APPDATA%\\Python\\Python310\\site-packages and jpype1/pycryptosat/"
        " clingo/pysat resolve from there; ai-01 measured the same lock env"
        " resolving jpype 1.7.1 from the ENV's own site-packages under"
        " PYTHONNOUSERSITE=1. A MISSING/DIVERGENT row above naming those"
        " packages therefore indicts the seat's shadowing, not the lock."
    )


def main():
    initialize_jvm()
    print("\n=== Tool inventory: resolved path + version ===")
    for k in ("eprover", "spass", "clingo"):
        p = EXTERNAL_TOOL_PATHS.get(k)
        print(f"  EXTERNAL_TOOL_PATHS[{k:8}] = {p}")
        if k == "clingo" and p:
            inner = Path(p) / "clingo.exe"
            print(f"    binary banner: {tool_version(inner)}")
        else:
            print(f"    binary banner: {tool_version(p)}")
    # #2852: the solver name readable in the gate log — which clingo VERSION
    # the JVM receives, and what was rejected on the way.
    print(
        f"  clingo selected version     = {EXTERNAL_TOOL_VERSIONS.get('clingo')} "
        f"(wanted {CLINGO_VERSION})"
    )
    if EXTERNAL_TOOL_REJECTIONS.get("clingo"):
        print(
            f"  clingo rejected             = {EXTERNAL_TOOL_REJECTIONS['clingo'][:200]}"
        )
    p9 = ROOT / "libs/prover9/bin/prover9.bat"
    print(f"  prover9.bat present       = {p9.is_file()}  ({p9})")
    for pkg in ("python-sat", "pycryptosat", "JPype1", "clingo", "z3-solver"):
        print(f"  package {pkg:<14} = {pkg_version(pkg)}")
    try:
        import jpype
    except ImportError:
        # A lock env that does not carry jpype must still get its REPORT, not a
        # traceback: every JVM-backed check below is fail-loud through
        # ``require`` (measured in the projet-is-lock env, #2851 DoD follow-up).
        jpype = None
        require(
            "JVM boot (jpype import)",
            False,
            "jpype is not importable in this env (absent from the lock) — "
            "JVM-backed checks (Tweety FOL, modal, SPASS, clingo JVM) cannot "
            "decide here",
        )
    if jpype is not None:
        print(f"  JVM path: {jpype.getDefaultJVMPath()}")
        if jpype.isJVMStarted():
            java_ver = str(jpype.JClass("java.lang.System").getProperty("java.version"))
            print(f"  JVM running: java.version={java_ver}")
    from argumentation_analysis.core import jvm_setup as _jvm_setup

    tweety = getattr(_jvm_setup, "TWEETY_VERSION", None)
    if tweety:
        print(f"  Tweety: monofatjar {tweety}")

    bridge = TweetyBridge()

    print("\n=== FOL — EProver (default) ===")
    fol_under(bridge, SolverChoice.EPROVER)
    print("\n=== FOL — Prover9 (alt solver choice) ===")
    fol_under(bridge, SolverChoice.PROVER9)
    print("\n=== FOL — Tweety fallback (the path both fall back to) ===")
    fol_under(bridge, SolverChoice.TWEETY)

    print("\n=== PL — PySAT (production path) ===")
    try:
        vi, mi = bridge.check_consistency("a\n!a", "propositional")
        vc, mc = bridge.check_consistency("a\nb", "propositional")
        line("PL INCONSISTENT", vi, mi)
        line("PL CONSISTENT", vc, mc)
        require(
            "PL[PySAT production] decides",
            vi is False and vc is True,
            f"inc={vi!r} con={vc!r}",
        )
    except Exception as e:  # noqa: BLE001
        require(
            "PL[PySAT production] decides", False, f"raised {type(e).__name__}: {e}"
        )

    pysat_backends()
    maxsat_and_mus()
    clingo_python()

    print("\n=== Modal — default SimpleMlReasoner (pure Java) ===")
    modal_under(bridge, "Modal[default]", prefer_spass=False)
    print("\n=== Modal — SPASS adapter ===")
    spass_ok, spass_reason = spass_state()
    if spass_ok:
        modal_under(bridge, "Modal[SPASS]", prefer_spass=True)
    else:
        # A skip is not a verdict (#2851): the default path above deciding
        # says nothing about SPASS. The run fails, naming the tool and the
        # reason the JVM reasoner gave.
        require(
            "Modal[SPASS] decides",
            False,
            f"SPASS does not run on this seat: {spass_reason}",
        )

    print("\n=== SAT — _invoke_sat (PySAT-backed) ===")
    try:
        from argumentation_analysis.orchestration.invoke_callables import _invoke_sat

        loop = asyncio.new_event_loop()
        res = loop.run_until_complete(_invoke_sat("a & !a", {}))
        sat_ok = isinstance(res, dict) and res.get("satisfiable") is False
        require("_invoke_sat decides", sat_ok, f"res={str(res)[:100]}")
    except Exception as e:  # noqa: BLE001
        require("_invoke_sat decides", False, f"raised {type(e).__name__}: {e}")

    print("\n=== ASP — clingo JVM (Tweety ClingoSolver) ===")
    try:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_asp_reasoning,
        )

        loop = asyncio.new_event_loop()
        res = loop.run_until_complete(_invoke_asp_reasoning("a.\nb :- a.", {}))
        sets = [set(m) for m in res.get("answer_sets", [])]
        # "Decides" must mean the JVM path decided (coordinator point 4,
        # 2026-09-29): _invoke_asp_reasoning falls back to the Python binding
        # when the JVM solver is refused (invoke_callables.py:6002) and
        # returns the same {a, b} — reading `sets` alone printed DECIDES on a
        # seat where the vendored binary is a leftover ELF (the po-2025 case
        # of #2851/#2852, error=193). The solver name is part of the verdict.
        require(
            "clingo[JVM] decides",
            res.get("solver") == "clingo_jvm" and {"a", "b"} in sets,
            f"solver={res.get('solver')!r} sets={sets}"
            + (
                ""
                if res.get("solver") == "clingo_jvm"
                else " — the PYTHON fallback answered, not the JVM path"
                f" (refusal: {res.get('jvm_refused', 'not reported')})"
            ),
        )
    except Exception as e:  # noqa: BLE001
        require("clingo[JVM] decides", False, f"raised {type(e).__name__}: {e}")

    lock_drift_section()

    print("\n=== DONE ===")
    if FAILURES:
        print(f"TOOLS THAT DID NOT DECIDE ({len(FAILURES)}):")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("Every tool decided on its known pair.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
