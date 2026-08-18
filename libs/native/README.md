# Native SAT Libraries — the ADF trio, extracted from the Tweety uber-jar

This directory holds `minisat.dll`, `lingeling.dll` and `picosat.dll`, the JNI
libraries backing Tweety's **ADF** SAT solvers. They are byte-identical copies
of resources carried by `libs/tweety/org.tweetyproject.tweety-full-*.jar`.

| File | sha256 (Tweety 1.29) | bytes |
| ---- | -------------------- | ----- |
| `minisat.dll` | `bfbc70c08e391f1a8da424476382fccd4fd0a7e9444d349bfce323303dd0da13` | 1 206 530 |
| `lingeling.dll` | `18159a7abce5c05466df572d395bc1c8a4ab4c5b0a2d1074a234358daf72a089` | 872 513 |
| `picosat.dll` | `390158b980e0bcdec32ae43ab8bf23758970b019d7742b80a2f80eda0e691fb0` | 387 866 |

## Why the files must sit here and not only in the jar

`org.tweetyproject.arg.adf.sat.solver.Native*Solver` locates its library with
`getResource("/<name>.dll")` and passes the URL straight to `System.load`.

- Resolved from inside the jar the URL is `jar:file:/…/tweety-full-1.29.jar!/minisat.dll`,
  and `System.load` rejects it: *"Expecting an absolute path of the library"*.
- Resolved from this directory — first on the classpath since #333 — it is
  `file:/…/libs/native/minisat.dll`, which loads.

So the trio was never a wiring problem. It was a *content* problem: the only
copy lived somewhere `System.load` cannot read from.

## What FP-20 #1244 measured, and why it still holds

FP-20 probed `org.tweetyproject.sat.{minisat,lingeling,picosat}.*SatSolver` and
got `UnsatisfiedLinkError: Binding.init()`. That verdict is **correct and
permanent for those classes**: these DLLs export no
`Java_org_tweetyproject_sat_*_Binding_*` symbol at all. They export
`Java_org_tweetyproject_arg_adf_sat_solver_Native*Solver_*`.

One jar ships two JNI APIs under the same informal name "minisat". FP-20's
exclusion of the `sat.*.Binding` family from the PL/SAT comparison
(`compare_pl_backends`) therefore stands unchanged — it is not narrowed away by
this directory being populated. What changes is only that the *other* family,
`arg.adf`, is now reachable.

Anti-théâtre (#1019) is satisfied by measurement, not by assertion:
`tests/unit/argumentation_analysis/agents/core/logic/test_native_sat_decides_1798.py`
requires each solver to answer **True** on `(a) ∧ (¬b)` and **False** on
`(a) ∧ (¬a)`. A backend that instantiates without deciding fails that pair, and
is not promoted.

## Consequence for the ADF axis

Every `org.tweetyproject.arg.adf.reasoner.*` reasoner takes an
`IncrementalSatSolver` in its constructor, and the JNI trio is the only
implementation in the JARs. With this directory empty, `ADFHandler._get_solver()`
returns `None` and all seven ADF semantics degrade to nothing (#1796). With it
populated, the axis is live.

## On a Tweety version bump (#21)

Re-extract the three files from the new uber-jar. The byte-identity test goes
red **first**, naming the drift — do not silence it:

```bash
python -c "import zipfile;z=zipfile.ZipFile('libs/tweety/<new>.jar');[open(f'libs/native/{n}.dll','wb').write(z.read(f'{n}.dll')) for n in ('minisat','lingeling','picosat')]"
```

## Other backends (unchanged)

| Backend | Type | Decides |
| ------- | ---- | ------- |
| `Sat4jSolver` | Pure-Java (Tweety 1.29) | Yes — default for PL |
| `SimpleDpllSolver` | Pure-Java (Tweety 1.29) | Yes — cross-check |
| PySAT ×6 | Python-side (cadical195/cryptominisat5/glucose42/maplechrono/lingeling/minisat22) | Yes — comparison |
| ADF JNI trio | Native (this directory) | Yes — ADF reasoners only |

PySAT's `lingeling`/`minisat22` are self-contained Python-side solvers bundled
by `python-sat`; they are unrelated to these JNI libraries.

The `.so` counterparts also present here are the Linux resources of the same
jar, kept untracked: CI is Windows and nothing exercises them yet.

`jvm_setup.py` additionally sets `-Djava.library.path=libs/native`. Tweety's ADF
loader never calls `System.loadLibrary`, so that option is not what makes the
trio work — the classpath entry is.
