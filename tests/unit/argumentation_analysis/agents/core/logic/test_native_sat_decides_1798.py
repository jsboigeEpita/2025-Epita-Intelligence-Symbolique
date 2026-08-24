"""#1798 — the JNI SAT trio decides, and the vendored DLLs are the jar's own.

Why this file exists (the reading that cost three rounds):

FP-20 #1244 concluded "the native solvers never decide" after probing
``org.tweetyproject.sat.{minisat,lingeling,picosat}.*SatSolver``, whose
``Binding.init()`` raises ``UnsatisfiedLinkError`` no matter where the library
sits. That verdict is **correct for the class it tested** — and it always will
be: the shipped DLLs export no ``Java_org_tweetyproject_sat_*_Binding_*``
symbol at all. They export ``Java_org_tweetyproject_arg_adf_sat_solver_
Native*Solver_*``.

Two JNI APIs live in one jar under the same informal name "minisat". The trio
that *works* is the ``arg.adf`` one, and it decides as soon as its library is
reachable: ``Native*Solver`` locates it with ``getResource("/<name>.dll")`` and
hands the URL straight to ``System.load``. From inside the jar that URL reads
``jar:file:...!/minisat.dll`` and ``System.load`` refuses it ("Expecting an
absolute path of the library"). From ``libs/native`` — already first on the
classpath since #333 — it reads ``file:/.../libs/native/minisat.dll`` and loads.

So the fix is content, not wiring: the jar's own resources, materialized into
the directory the classpath already points at. These tests pin the three facts
that make that safe, and each is written to fail loudly rather than skip:

1. every solver **decides**, and discriminates SAT from UNSAT;
2. the ADF axis is consequently **live**, not degraded;
3. each vendored DLL is **byte-identical** to the jar resource it came from —
   this is what turns a Tweety version bump (#21) red instead of silent.

Privacy: synthetic atoms only (``a``, ``b``) — no corpus content.
"""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import jpype
import pytest

from argumentation_analysis.agents.core.logic.adf_handler import ADFHandler
from argumentation_analysis.config.settings import settings
from argumentation_analysis.core.jvm_setup import PROJ_ROOT, initialize_jvm

pytestmark = [pytest.mark.jpype, pytest.mark.tweety]

SOLVERS = ("NativeMinisatSolver", "NativeLingelingSolver", "NativePicosatSolver")
LIBS = ("minisat", "lingeling", "picosat")


@pytest.fixture(scope="module", autouse=True)
def _jvm():
    """Idempotent: the session conftest normally started it already."""
    initialize_jvm()


def _native_dir() -> Path:
    return PROJ_ROOT / settings.jvm.native_libs_dir


def _jar_carrying(resource: str) -> Path:
    """The jar that actually holds ``resource``, whichever layout is on disk.

    Selecting by name (``"full" in j.name``) was wrong in both directions once
    #1874 made the Maven assembly a real layout. The thin aggregator
    ``org.tweetyproject.tweety-full-<v>.jar`` matches that predicate and carries
    no resource at all, and it sorts *after* ``...-with-dependencies.jar``
    (``-`` < ``.``), so ``[-1]`` picked precisely the empty one -- measured: the
    three parametrisations failed with ``KeyError: minisat.dll`` on CI run
    32768195554 while passing on the pre-assembly baseline 32672127427. In an
    assembly the natives live in ``org.tweetyproject.sat`` and
    ``org.tweetyproject.arg.adf``; no jar has "full" in its name at all.

    Asking *which jar contains the entry* is the one predicate true of every
    layout, and it does not weaken the guard: if nothing carries the resource
    that is itself a finding, and this raises instead of skipping.
    """
    libs = PROJ_ROOT / settings.jvm.tweety_libs_dir
    version = settings.jvm.tweety_version
    carriers = []
    for jar in sorted(libs.glob("*.jar")):
        try:
            with zipfile.ZipFile(jar) as z:
                if resource in z.namelist():
                    carriers.append(jar)
        except zipfile.BadZipFile:
            continue
    if not carriers:
        raise AssertionError(
            f"no jar under {libs} carries {resource!r}: either the classpath is "
            "empty, or a version bump dropped the vendored natives. Both are "
            "real findings -- do not relax this into a skip."
        )
    # Prefer the configured version. Without this the first carrier wins
    # alphabetically, which on a machine holding both 1.28 and 1.29 fat jars
    # compares the vendored DLL against 1.28 while the JVM loads 1.29 -- a
    # drift guard reading the wrong side of the drift. They happen to be
    # byte-identical today (measured), which is exactly why the mistake would
    # not have shown up until the day it mattered.
    for jar in carriers:
        if version in jar.name:
            return jar
    return carriers[0]


class TestNativeSatDecides:
    """A backend that instantiates but does not decide is what FP-20 forbade."""

    @pytest.mark.parametrize("solver_name", SOLVERS)
    def test_solver_decides_and_discriminates(self, solver_name):
        """SAT must answer True and UNSAT must answer False — same solver.

        Asserting only the SAT case would pass on a stub that always says
        "satisfiable". The pair is the discriminating substitution.
        """
        Lit = jpype.JClass("org.tweetyproject.arg.adf.syntax.pl.Literal")
        Clause = jpype.JClass("org.tweetyproject.arg.adf.syntax.pl.Clause")
        cls = jpype.JClass(f"org.tweetyproject.arg.adf.sat.solver.{solver_name}")
        a, b = Lit.create("a"), Lit.create("b")

        verdicts = {}
        for label, clauses in (
            ("sat", ([a], [b.neg()])),
            ("unsat", ([a], [a.neg()])),
        ):
            state = cls().createState()
            try:
                for literals in clauses:
                    state.add(Clause.of(*literals))
                verdicts[label] = bool(state.satisfiable())
            finally:
                state.close()

        assert (
            verdicts["sat"] is True
        ), f"{solver_name} called (a) & (~b) unsatisfiable — it is not deciding"
        assert (
            verdicts["unsat"] is False
        ), f"{solver_name} called (a) & (~a) satisfiable — it is not deciding"

    def test_adf_axis_is_live_not_degraded(self):
        """The consumer's own probe must find a solver.

        ``ADFHandler._get_solver`` degrades to ``None`` when the trio cannot
        load, and every reasoner then returns nothing. Reading the solver
        through the handler — not through jpype — is what proves the axis the
        pipeline actually uses is live.
        """
        assert ADFHandler()._get_solver() is not None, (
            "ADF reasoners have no SAT backend: the axis is degraded, "
            "not merely untested"
        )


class TestVendoredLibrariesComeFromTheJar:
    """Drift between the vendored DLL and the jar must be loud, not silent."""

    @pytest.mark.parametrize("lib", LIBS)
    def test_vendored_dll_is_byte_identical_to_jar_resource(self, lib):
        on_disk = _native_dir() / f"{lib}.dll"
        assert on_disk.is_file(), (
            f"{on_disk} is missing — Native{lib.capitalize()}Solver will hand a "
            "jar: URL to System.load and the ADF axis dies silently"
        )
        carrier = _jar_carrying(f"{lib}.dll")
        with zipfile.ZipFile(carrier) as z:
            in_jar = z.read(f"{lib}.dll")
        assert hashlib.sha256(on_disk.read_bytes()).hexdigest() == (
            hashlib.sha256(in_jar).hexdigest()
        ), (
            f"{lib}.dll differs from the resource in {carrier.name}. If the "
            "jar was bumped (#21), re-extract the trio; do not silence this."
        )

    @pytest.mark.parametrize("lib", LIBS)
    def test_dll_binds_the_adf_api_not_the_sat_binding_api(self, lib):
        """Pins *why* FP-20 read false, so nobody re-derives the wrong class.

        The positive half also guards the negative: if the ADF symbol were
        absent too, this test would fail rather than quietly confirm.
        """
        blob = (_native_dir() / f"{lib}.dll").read_bytes()
        adf_symbol = f"Java_org_tweetyproject_arg_adf_sat_solver_Native".encode()
        binding_symbol = f"Java_org_tweetyproject_sat_{lib}_Binding".encode()
        assert adf_symbol in blob, (
            f"{lib}.dll exports no arg.adf JNI symbol — it cannot back any "
            "ADF reasoner"
        )
        assert binding_symbol not in blob, (
            f"{lib}.dll now exports {binding_symbol.decode()}; the "
            "sat.*.Binding API became reachable and FP-20's exclusion of it "
            "should be revisited rather than left in place"
        )
