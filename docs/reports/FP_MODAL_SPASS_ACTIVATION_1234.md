# Modal axis — SPASS was never genuinely activated (régression #1234)

**Date**: 2026-06-23 · **Machine**: po-2025 (WSL2 fol-linux stack) · **Issue**: #1234
**Class**: anti-théâtre #1019 / delivery-contract regression (modal analogue of eprover #1204)

## TL;DR

The modal-logic axis advertised SPASS (a SOTA modal theorem prover) as its
external solver, but **SPASS was never genuinely running**. The axis silently
fell back to `SimpleMlReasoner` (pure-Java, naive Kripke enumeration), which
**OOMs at ~12 atoms** — so real KBs never decided (`valid=None`). Three layers,
all firsthand-verified:

1. **Default never selected SPASS.** `config.modal_solver` defaults to `TWEETY`,
   not `SPASS`. The modal axis ran `SimpleMlReasoner` everywhere.
2. **The vendored binary was never a CLI prover, and was deleted.** The shipped
   `SPASS.exe` was a GUI/elevation InstallShield build (`requireAdministrator`
   manifest → `CreateProcess error=740`, `isInstalled()==False`) — verified
   firsthand from its PE manifest. It was deleted in the cleanup-gate commit
   `f1234b58` ("Nettoyer l'index Git", 426 files) together with the Tweety
   notebooks and `_archives/Argument_Analysis/ext_tools`.
3. **Even a freshly-built SPASS 3.9 CLI cannot be driven by Tweety 1.29 without
   a delivery-contract fix.** See below — this is the actual blocker, and the
   modal twin of the eprover #1204/#1196 regression class.

## The delivery-contract regression (the real blocker)

A genuine SPASS 3.9 CLI built from source (WSL, `scripts/setup/build_spass_modal.sh`)
**works standalone** (UNSAT→"Proof found", SAT→"Completion found"). But driving
it through `ModalHandler` → Tweety `SPASSMlReasoner.query` throws
*"SPASS returned no result which can be interpreted"*.

Captured firsthand (logging wrapper around the real binary), the exact Tweety
invocation `SPASS -PGiven=0 -PProblem=0 <tmp>.dfg` fails at parse time:

```
In file <tmp>.dfg at line 14, column 33: got 'EML', expected special type (eml)
```

**Root cause**: Tweety 1.29's `SPASSMlReasoner` emits the DFG special-formulae
logic token in **uppercase** —

```
list_of_special_formulae(axioms,EML).
```

— but **SPASS 3.9's DFG parser requires it lowercase** (`eml`; see
`dfgparser.c: dfg_parse_special_type_isEml`, token `T_eml`). SPASS aborts before
reasoning. It is a Tweety↔SPASS **version mismatch**, not a reasoning failure —
exactly analogous to the Tweety↔E argc=0 delivery-contract regression (#1204).

## Fix — activate SPASS, no contournement

The SOTA prover does **100%** of the modal reasoning (EML→FOL translation +
saturation). We repair **only** the interface keyword case, at the delivery
boundary, mirroring the #1204 sentinel pattern:

- **`scripts/solvers/spass_eml_adapter.sh`** — rewrites `list_of_special_formulae(X,EML)`
  → `(X,eml)` in the DFG temp file Tweety passes as a file argument, then `exec`s
  the real SPASS unchanged. Relocatable (`$SPASS_REAL_BIN` or sibling `./SPASS`).
- **`argumentation_analysis/core/jvm_setup.py`** — SPASS detection now *prefers*
  the adapter (`ext_tools/spass/spass_eml_adapter.sh`) when present, so Tweety
  invokes it transparently as `EXTERNAL_TOOL_PATHS['spass']`. If only the raw
  binary is present, modal SPASS fails **honestly** on the EML mismatch (`None`,
  no fabrication, #1019).
- **`scripts/setup/build_spass_modal.sh`** — reproducible SPASS 3.9 source build
  (`spass39.tgz`; gcc+make+flex+bison, conda-forge userspace, sudo-free) +
  adapter install into the gitignored `ext_tools/spass/`.
- **`argumentation_analysis/orchestration/workflows.py`** — modal phase ceiling
  180→420 s (parity with pl/fol, #705). Secondary; the OOM itself is fixed by
  SPASS (saturation, no enumeration), not by more time.

### Rejected: the PySAT routing contournement

An earlier #1234 draft routed 0-modal-operator translations to PL/PySAT. Though
mathematically sound for a no-□/◇ KB, it **routes around** the modal solver
instead of activating it — rejected per the directive *"pas de contournement,
tous les outils SOTA doivent être activés."* Reverted.

## Firsthand proof (production `ModalHandler`, WSL fol-linux, SPASS via adapter)

Detection registered the adapter; `ModalHandler` loaded `SPASSMlReasoner` with
it; **all cases decided via SPASS**, traceable to `(spass)`:

| KB (synthetic atoms only) | `SimpleMlReasoner` (TWEETY) | SPASS (adapter) |
|---|---|---|
| inconsistent `Rain, !Rain` | False | **False** ✓ |
| consistent `[](Rain⇒Wet), Rain` | True | **True** ✓ |
| **12-atom propositional chain** | **OOM → None** | **True** ✓ (no OOM) |
| **12-atom modal `[](aᵢ⇒aᵢ₊₁)` + `<>(a1)`** | **OOM → None** | **True** ✓ (no OOM) |

The two 12-atom KBs are the FP-16 #1231 OOM cases. SPASS decides them; the
default reasoner cannot. Encoded as the gated
`tests/integration/.../test_spass_real.py::TestRealSpassConsistency`
(`test_multi_atom_kb_decides_via_spass_without_oom`), which skips honestly where
SPASS is not a runnable CLI build (e.g. Windows CI with no binary).

## Reproducibility

- Build: `bash scripts/setup/build_spass_modal.sh` (needs `spass39.tgz` from the
  official SPASS distribution; flex/bison/make/gcc).
- Run: set `modal_solver=spass` (`MODAL_SOLVER=spass`); detection wires the
  adapter; the gated real test asserts the verdicts above.
- Bases: branch `fix/1234-modal-reasoner-oom-routing` off main `ce6c5474`.

## Follow-ups (coordinator-gated)

- **Windows SPASS CLI build** (Cygwin/MSVC) + `.bat` adapter — the canonical
  pipeline runs on Windows, where no SPASS CLI yet exists; until then modal-SPASS
  is honest-degraded (`None`) there, decided only on the Linux/WSL stack.
- **Binary vendoring policy** — whether to vendor a prebuilt SPASS under
  `ext_tools/` (as eprover.exe is), or keep build-from-source only.

## Related

- #1204 (Tweety↔E delivery contract, sync+async sentinel) — the FOL twin.
- #1219/#1221 (modal pipeline reaches SimpleMlReasoner), #1231/FP-16 (modal OOM).
- #1019 (anti-théâtre invariant) — the family this fix belongs to.
