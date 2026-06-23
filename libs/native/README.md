# Native SAT Libraries — Honest-Absent

This directory previously held `lingeling.dll`, `minisat.dll`, and `picosat.dll` for
Tweety's JNI SAT backends. They have been removed (FP-20 #1244, Epic #1191).

## Why removed

Firsthand probe (R473, po-2025): `System.loadLibrary()` for all three DLLs succeeds,
but instantiating `org.tweetyproject.sat.{lingeling,minisat,picosat}.*SatSolver` throws
`UnsatisfiedLinkError: Binding.init()` — the JNI entry-point symbol is absent from the
vendored builds (JNI ABI mismatch). None of these solvers ever decided on this machine.

Anti-théâtre (#1019): a backend that throws `UnsatisfiedLinkError` on instantiation is
worse than honest-absent. Promoting it would fabricate a solver capability that does not
exist.

## Active SAT backends

| Backend | Type | Decides |
| ------- | ---- | ------- |
| `Sat4jSolver` | Pure-Java (Tweety 1.29) | Yes — default |
| `SimpleDpllSolver` | Pure-Java (Tweety 1.29) | Yes — cross-check |
| PySAT ×6 | Python-side (cadical195/cryptominisat5/glucose42/maplechrono/lingeling/minisat22) | Yes — comparison |

PySAT's `lingeling`/`minisat22` are self-contained Python-side solvers bundled by
`python-sat`; they are unrelated to the removed JNI DLLs.

## java.library.path

The `jvm_setup.py` initialization still sets `-Djava.library.path=libs/native` (harmless
with an empty directory). The `download_native_sat_libs()` helper has been removed.
