# Issue #1648 — Inventory of Flattening Sites

**Issue:** `#1648` — "Motif d'aplatissement : 11 modules ecrivant dans le conteneur d'un autre formalisme" (Epic `#1644`, mode 2).
**Status:** Open at time of investigation (aout 2026).
**Scope:** Per-site inventory of writers that flatten into a neighbouring formalism's
container; per-container reader inventory; recommended single remedy; anti-#1019
regression test idea.
**Privacy discipline:** Opaque corpus IDs (`corpus_A`, `corpus_B`) only. No real source
names. No plaintext dataset content. The dispatcher's commit is docs-only.

---

## 0. Methodology and ground rules

**Triple grounding (technique only, docs-only investigation):**
- **Writer source-of-truth:** `argumentation_analysis/orchestration/state_writers.py`
  (only place where state is mutated via `add_*` hooks). Read with `Read` offset 1-1649.
- **Invoke source-of-truth:** `argumentation_analysis/orchestration/invoke_callables.py`
  (9594 lines; `_invoke_*` returns are the payload the writer sees).
- **Handler source-of-truth:** `argumentation_analysis/agents/core/logic/<name>_handler.py`
  (defines the **native** data structure of each formalism — what was actually
  computed before flattening).
- **Reader source-of-truth:** grep over `argumentation_analysis/` (production only,
  `tests/` excluded). The `Reporting/R6` restitution and the `evaluation/` mining
  code are the canonical consumers.

**Definition adopted.** A "flattening site" is a writer `W` such that:
1. `W` writes into a container `C` whose **legitimate owner** is formalism `F ≠ formalism(W)`;
2. the writer re-emits a **subset** of the invoke return into `C`, dropping
   information that was present in the invoke output (and therefore producible);
3. the dropped information is **distinctive** of `formalism(W)` (not shared with `F`).

The 11 sites in the issue body match this definition; the inventory is below.

**Conventions used in tables.** "**Distinct info lost**" enumerates invoke-return keys
(or, when absent there, source-of-information at the handler) that the writer does
NOT surface into `C`. "**Source vs re-read gap**" enumerates ways the writer
*synthesises* or *replaces* the emitted payload (e.g. string-encoding a fact into
`formulas`, or emitting `attacks=[]` in place of available data).

**Anti-pendule guardrails (from issue body, restated for the table):**
- "Ne pas supposer que la perte est au writer. Elle peut etre a l'invoke." For
  each site, the "Distinct info lost" column distinguishes **invoke-side loss**
  (handler did not return the key) from **writer-side loss** (writer received
  the key but did not surface it). When the distinction cannot be made from
  static reading, it is labelled "**non verifie**".
- "Ne pas traiter `attacks=[]` comme une evidence a corriger" — for ADF, the
  absence of attacks is **correct** (the formalism has acceptance conditions,
  not binary attacks). For ABA, attacks **are derivable** from contraries and
  their absence is a real loss. Section 2 answers this case-by-case.

---

## 1. Per-site inventory (11 sites)

### 1.1 Sites writing to `state.dung_frameworks`

The container `state.dung_frameworks` is declared at
`core/shared_state.py:442` and populated via `add_dung_framework`
(`core/shared_state.py:811-829`). The canonical owner is `dung_extensions`
(`_invoke_dung_extensions` → `_write_dung_extensions_to_state`).

| # | Module | Container | Writer (file:line) | Invoke (file:line) | Distinct info lost | Source vs re-read gap |
|---|--------|-----------|--------------------|--------------------|--------------------|-----------------------|
| 1 | **ABA** | `state.dung_frameworks` | `_write_aba_to_state` (`state_writers.py:831-845`) | `_invoke_aba` (`invoke_callables.py:3603-3646`) → `handler.analyze_aba_framework` (`agents/core/logic/aba_handler.py:59-128`) | **Contraries** (`Dict[str, str]` mapping assumption → contrary) consumed at `invoke_callables.py:3610,3640` but NEVER returned by handler (`aba_handler.py:115-125` returns `{semantics, extensions, assumptions, rules_count, statistics}` only). Also: ABA semantics is multi-extension (`preferred`/`stable`/`complete`/`well_founded`/`ideal`), the writer stores only ONE composite `{"aba_extensions": extensions}` key — distinct semantics names are collapsed into a single list. **[Corrected 2026-09-07, #1648 sonde]** The contraries claim is outdated on both halves: the handler DOES return `contraries` (measured payload key), and the Wave-2 sidecar carries `formalism_specific.contraries` value-equal into the state. Measured remaining losses: `rules_count` + `statistics` dropped at the writer; semantics still collapsed under the single `aba_extensions` key. | **`attacks=[]` hard-coded** (`state_writers.py:843`). Native Dung `add_dung_framework` interprets empty attacks as "no attack relations" → extension trivially contains all arguments. See Section 2. **[Corrected 2026-09-07, #1648 sonde]** Measured `attacks=[]` confirmed. |
| 2 | **ADF** | `state.dung_frameworks` | `_write_adf_to_state` (`state_writers.py:848-861`) | `_invoke_adf` (`invoke_callables.py:3649-3668`) → `handler.analyze_adf` (`agents/core/logic/adf_handler.py:61-126`) | **Acceptance conditions** (the `Dict[str, str]` mapping `statement → "tautology"|"contradiction"|"negation:stmt"`). Consumed at `invoke_callables.py:3654,3662` (`_adf_conditions_from_context(args, context)`). The handler computes interpretations over the conditions but returns `{semantics, statements, interpretations, statistics}` — **conditions are NOT in the return dict** (loss at the handler level). **#2063 correction (2026-09-06): writer-side loss too** — the writer read `models`/`extensions`, keys the handler never writes, so `extensions["adf_models"]` was `[]` on every run while `interpretations`/`statistics`/`degraded`/`note` went to the floor. Fixed: reads `interpretations`, provenance in the `formalism_specific` sidecar. | **`attacks=[]` hard-coded** (`state_writers.py:859`). **Correct representation** for ADF: ADF has no binary attack relation, only acceptance conditions. See Section 2. Writer is technically correct on `attacks=[]`; the conditions loss is upstream — and until #2063 the writer ALSO dropped the interpretations it received (phantom key). **[Corrected 2026-09-07, #1648 sonde]** Post-#2063 behaviour now MEASURED end-to-end on the JVM path: `interpretations` reach `extensions.adf_models` value-equal, `statistics` reaches the `formalism_specific` sidecar, statements reach `arguments`; the `degraded`/`note` provenance keys are correctly absent on a non-degraded payload (presence-gated, nothing fabricated). Acceptance conditions confirmed absent from the handler return — the upstream gap stands. |
| 3 | **SetAF** | `state.dung_frameworks` | `_write_setaf_to_state` (`state_writers.py:1199-1209`) | `_invoke_setaf` (`invoke_callables.py:4126-4180`) → `handler.analyze_setaf` (`agents/core/logic/setaf_handler.py:69-134`) | **Joint (set) attacks** — the native data structure `List[{attackers: List[str], target: str}]`. The handler returns them in `output["attacks"]` (line 123), but the writer hard-codes `attacks=[]` with comment "set attacks don't map to binary attacks" (`state_writers.py:1207`). The information exists in the invoke return; the writer explicitly drops it. **[Corrected 2026-09-07, #1648 sonde]** Outdated: the Wave-2 sidecar preserves them — measured `formalism_specific.set_attacks` value-equal with the handler's dict-shaped echo. Remaining measured losses: handler `statistics` dropped; `attacks=[]` by design. | Writer synthesises the extensions dict as `{"setaf_extensions": [...]}`. Any reader looking for Dung-style `attacks` sees `[]` — silent lossy projection. See Section 2. **[Corrected 2026-09-07, #1648 sonde]** Confirmed measured; #1698 retention counters (submitted/retained/dropped) DO reach the entry top-level. |
| 4 | **Weighted** | `state.dung_frameworks` | `_write_weighted_to_state` (`state_writers.py:1212-1226`) | `_invoke_weighted` (`invoke_callables.py:4183-4249`) → `handler.analyze_weighted_framework` (`agents/core/logic/weighted_handler.py:73-153`) | **Attack weights** — the handler returns `output["attacks"]` as `List[{source, target, weight}]` (line 139-141). The writer extracts only `[src, tgt]` (drops `weight`). **Also lost: `weight_statistics`** (the handler returns `min_weight`, `max_weight`, `avg_weight` at lines 130-134, never consumed). **[Corrected 2026-09-07, #1648 sonde]** Both halves are outdated, and the measured loss is *worse* than described. On the real invoke→writer path the writer receives `attacks` as raw `(src, tgt, weight)` **triples**, not the handler's dicts: `_annotate_attack_retention` (#1698, `invoke_callables.py:3462`) overwrites the handler's dict-shaped echo with the filtered input triples. The writer's dict-only sanitiser then filters every triple out: measured state entry has `attacks=[]` (not even `[src, tgt]` pairs) and **no** `attack_weights` sidecar — the Wave-2 sidecar for Weighted is unreachable on the production path, Tweety-version-independent (the shape clobber is Python-side). `weight_statistics` IS consumed now (measured `formalism_specific.weight_statistics` value-equal). | Writer produces attacks as `[src, tgt]` pairs — a list-shape that downstream readers expect, but the weight is invisible. `weight_statistics` is computed at the handler but discarded at the writer. **[Corrected 2026-09-07, #1648 sonde]** Measured: pairs do NOT survive either (`attacks=[]`); only `weight_statistics` does. |
| 5 | **Social** | `state.dung_frameworks` | `_write_social_to_state` (`state_writers.py:1229-1240`) | `_invoke_social` (`invoke_callables.py:4252-4277`) → `handler.analyze_social_framework` (`agents/core/logic/social_handler.py:56-133`) | **Per-argument social strength scores** (the `Dict[str, float]` of `model.get(arg)`) and **vote tallies** (`Dict[arg, (pos, neg)]`). Both are computed by the handler (`social_handler.py:113` for scores, line 89-92 for votes). The writer stores them only inside `extensions={"social_ranking": [...], "social_scores": {...}}` — opaque to readers that aggregate `attacks`. **[Corrected 2026-09-07, #1648 sonde]** Measured consistent: ranking + scores reach `extensions`, `attacks` preserved as pairs; raw **votes reach the state nowhere** (full-entry search) and `statistics` (voters count, handler) is dropped. No sidecar for Social. | Reader-visible shape: `attacks` preserved as `[src, tgt]` (good), but a reader iterating `attacks` cannot tell a social-vote weighted graph from a Dung binary graph. |
| 6 | **EAF (Epistemic)** | `state.dung_frameworks` | `_write_eaf_to_state` (`state_writers.py:1243-1252`) | `_invoke_eaf` (`invoke_callables.py:4317-4342`) → `handler.analyze_epistemic_framework` (`agents/core/logic/eaf_handler.py:71-130`) | **Epistemic beliefs** — the per-agent `Dict[agent, List[arg]]` mapping. Computed at `invoke_callables.py:4326` (`_eaf_beliefs_from_context`) and returned by the handler (`eaf_handler.py:118`). The writer discards them; only `extensions={"eaf_extensions": extensions}` survives. `statistics.agents_count` is computed (`eaf_handler.py:124`) and dropped. **[Corrected 2026-09-07, #1648 sonde]** **NON MESURÉ** — the local probe runs Tweety 1.28 (see §1.5 env caveat) and `org.tweetyproject.arg.eaf` has **zero classes** in the 1.28 fat jar (measured `unzip -l | grep arg/eaf` = 0) — the module the fleet's 1.31 pin provides does not exist at 1.28. The writer structurally carries a `formalism_specific.epistemic_beliefs` sidecar (code-read, `state_writers.py:1664+`), but this site is **named non-measured, not counted preserved**. | Reader-visible shape: `attacks` preserved as `[src, tgt]` (good), but the EAF-specific epistemic dimension is invisible to readers that read `extensions["eaf_extensions"]` as a flat list of extensions. |
| 7 | **DeLP** | `state.dung_frameworks` | `_write_delp_to_state` (`state_writers.py:1255-1265`) | `_invoke_delp` (`invoke_callables.py:4345-4384`) → `handler.analyze_delp` (`agents/core/logic/delp_handler.py:117-164`) | **The whole dialectical tree** (literal DeLP arguments with strict/defeasible rules, defeat relations, comparison criterion verdict). The handler returns `{program, program_size, criterion, query_results: [{query, answer, message}]}` — the writer stashes the query_results inside `extensions={"delp_query_results": ...}`. **Defeat relations between arguments are nowhere in the state** — DeLP's whole reason for existing. **[Corrected 2026-09-07, #1648 sonde]** Partially outdated: the Wave-2 sidecar preserves `delp_arguments` (program text, measured value-equal), `program_size` and `criterion`; `query_results` reach `extensions.delp_query_results`. The dialectical tree / defeat relations remain absent — confirmed measured. Handler `statistics` dropped. | **Both `arguments=[]` and `attacks=[]` hard-coded** (`state_writers.py:1262-1263`). Reader looking at `state.dung_frameworks["delp_analysis"]` sees an empty AF — the dialectical engine ran but the result is a single (answer, message) per query. **[Corrected 2026-09-07, #1648 sonde]** Measured `arguments=[]`, `attacks=[]` confirmed; program preserved only via the sidecar. |
| 8 | **Dung-arbitration** (native Dung, less critical) | `state.dung_frameworks` | `_write_dung_arbitration_to_state` (`state_writers.py:1067-1125`) | `_invoke_dung_arbitration` (`invoke_callables.py:7974-8048`) → `arbitrate_detections` (logic-only, no JVM) | **Walton-Krabbe declared relations** and **same-span rivalry** (the attack-generation primitives at `invoke_callables.py:8028-8033`). The verdict survives as `attacks` + `extensions={"surviving_ids", "eliminated_ids", "honest_absent", "enabled", "input_count", "surviving_count"}` — comprehensive but inside a non-Dung semantics-keyed bag. | Honest projection (the verdict IS the format), but provenance ("how was the attack generated?") is lost — the `honest_absent` flag is preserved but the *reason* (no declared relations / no same-span rivalry) is not. **[Corrected 2026-09-07, #1648 sonde]** Measured (logic-only, no JVM): every verdict field reaches the state (`surviving_ids`, `eliminated_ids`, `attacks`, `honest_absent`, `enabled`, counts). Walton-Krabbe provenance untested by the probe — the probe supplied no declared relations, so the payload carried none; note the handler's `verdict` dict is written wholesale into `extensions`, so any provenance the handler DID emit would reach the state. |
| 9 | **Dung-verification** (native Dung, less critical) | `state.dung_frameworks` | `_write_dung_extensions_to_state` (`state_writers.py:1037-1064`) | `_invoke_dung_extensions` (`invoke_callables.py:7057-7973`) | None — this IS the legitimate Dung writer; semantics keys match what readers expect. **NB**: it stores primary + additional semantics as separate `name=verification_<sem>` entries (line 1050, 1061). | None observed. Native Dung contract. **[Corrected 2026-09-07, #1648 sonde]** Confirmed measured on the JVM path: `semantics="multi"` produced 11 entries (primary + one `verification_<sem>` per semantics), `arguments`/`attacks`/`extensions` preserved, #1698 retention counters carried onto each entry. |

### 1.2 Sites writing to `state.fol_analysis_results`

The container `state.fol_analysis_results` is declared at
`core/shared_state.py:1079-1111`. The canonical owner is `fol_reasoning`
(`_invoke_fol_reasoning` → `_write_fol_to_state`).

| # | Module | Container | Writer (file:line) | Invoke (file:line) | Distinct info lost | Source vs re-read gap |
|---|--------|-----------|--------------------|--------------------|--------------------|-----------------------|
| 10 | **Description Logic (DL)** | `state.fol_analysis_results` | `_write_dl_to_state` (`state_writers.py:1144-1160`) | `_invoke_dl` (`invoke_callables.py:3971-4000`) → `handler.is_consistent` (`agents/core/logic/dl_handler.py:161-198`) | **The full DL ontology** — TBox (`List[Tuple[concept, equivalent_concept]]`), ABox concepts (`List[Tuple[individual, concept]]`), ABox roles (`List[Tuple[ind, role, ind]]`), and the **subsumption queries** (`query_subsumption` at `dl_handler.py:213`). The invoke receives them at `invoke_callables.py:3973-3975` and counts them in `tbox_size` / `abox_size` (`invoke_callables.py:3992-3993`), but the writer stores only `[f"DL: {message}"]` as `formulas` — sizes are dropped. **[Corrected 2026-09-07, #1648 sonde]** Outdated: the ontology DOES reach the state — the Wave-2 sidecar carries `formalism_specific.{tbox, abox_concepts, abox_roles}` measured value-equal (`input_ontology` re-emitted by the invoke). Measured remaining losses: `tbox_size`/`abox_size` and `statistics` dropped. | Writer synthesises a single fake-formula string `"DL: {message}"` (the consistency verdict's textual representation). Verdict (`consistent`) IS preserved correctly (None/True/False); the **structure** (TBox, ABox, subsumptions) is gone. **Survives honest-absent only by accident** — if `handler.is_consistent` raises, `_invoke_dl` raises `RuntimeError` and nothing is written (anti-#1019, good). But when `is_consistent` succeeds, the ontology disappears. **[Corrected 2026-09-07, #1648 sonde]** Measured: verdict + label preserved; structure preserved via sidecar; only sizes/statistics lost. |

### 1.3 Sites writing to `state.propositional_analysis_results`

The container `state.propositional_analysis_results` is declared at
`core/shared_state.py:1113-1148`. The canonical owner is `propositional_logic`
(`_invoke_propositional_logic` → `_write_propositional_to_state`).

| # | Module | Container | Writer (file:line) | Invoke (file:line) | Distinct info lost | Source vs re-read gap |
|---|--------|-----------|--------------------|--------------------|--------------------|-----------------------|
| 11 | **Conditional Logic (CL)** | `state.propositional_analysis_results` | `_write_cl_to_state` (`state_writers.py:1163-1174`) | `_invoke_cl` (`invoke_callables.py:4003-4034`) → `handler.query` (`agents/core/logic/cl_handler.py:178-212`) | **The conditionals themselves** (the `ClBeliefSet` of `(conclusion | premise)` formulas). The invoke receives them at `invoke_callables.py:4005` (`conditionals = context.get("conditionals", [])`) and the handler parses them via `kb = handler.create_knowledge_base(conditionals)` (line 4017), but the writer stores only `[f"CL({num_conditionals} conditionals): {message}"]`. The count is in the formula string; the conditionals themselves are gone. CL's distinctive semantics (non-material conditionals, system-P/System-Z ranking) is invisible. **[Corrected 2026-09-07, #1648 sonde]** **NON MESURÉ** — under the local Tweety 1.28 the invoke raises `RuntimeError: Conditional Logic unavailable: JVM/Tweety required (too many values to unpack (expected 2))` with the JVM up: a 1.28-vs-1.31 API shape difference inside the handler. The writer structurally carries a `formalism_specific.conditionals` sidecar fed from `input_conditionals` (code-read, `state_writers.py:1461+`), but this site is **named non-measured, not counted preserved**. | Writer synthesises a label `"CL(N conditionals): {msg}"` — the verdict (`entailed` → `satisfiable`) is preserved; structure is dropped. |
| 12 | **SAT** | `state.propositional_analysis_results` | `_write_sat_to_state` (`state_writers.py:1177-1196`) | `_invoke_sat` (`invoke_callables.py:4037-4120`) | **MUS list** (in MUS mode): `output["mus_subsets"]` (line 4088). The writer preserves `mus_count` inside a label `"SAT/MUS: {n} minimal unsatisfiable subsets"` but the actual subsets are dropped. **In solve mode**, the model IS preserved (writer at line 1195 passes `model`). **Backend comparison** (`sat_backend_comparison`) is dropped (line 4119 builds it, writer never reads it). **[Corrected 2026-09-07, #1648 sonde]** Solve mode measured against the real cadical backend: `satisfiable` + full `model` preserved; `statistics` (solver, num_clauses, solve_time) dropped at the writer — writer-side loss confirmed by re-read. MUS mode measured but **vacuous on this backend**: Z3-MARCO returned `mus_count=0, mus_subsets=[]` on three genuinely UNSAT inputs (`["p","~p"]`, `["p & ~p"]`, `["a | b","~a","~b"]`) — a handler-level anomaly worth its own look; the "subsets dropped" verdict stands only on the label evidence. `sat_backend_comparison` not elicited by the probe (single backend). | In MUS mode: synthesises a label, drops the actual subsets. In solve mode: model preserved (writer at line 1195). |
| 13 | **QBF** | `state.propositional_analysis_results` | `_write_qbf_to_state` (`state_writers.py:1268-1276`) | `_invoke_qbf` (`invoke_callables.py:4387-4415`) → `handler.analyze_qbf` (`agents/core/logic/qbf_handler.py:152-177`) | **Quantifiers** (the `List[{type: "forall"|"exists", vars: [...]}]` structure). The invoke receives them at `invoke_callables.py:4389`, the handler returns them at `qbf_handler.py:169` (`"quantifiers": quantifiers`), and **the writer drops them**. The whole point of QBF — alternating quantifiers over propositional matrix — is invisible. **[Corrected 2026-09-07, #1648 sonde]** Outdated: quantifiers are NOT dropped — the Wave-2 sidecar carries `formalism_specific.qbf_quantifiers` (key name differs from the docstring's plain `quantifiers` — an inventory-by-name trap) measured value-equal. Measured remaining loss: `statistics` dropped. | Writer synthesises `[f"QBF: {formula}"]` from the formula string only. Verdict (`valid`) preserved; quantifier alternation lost. **[Corrected 2026-09-07, #1648 sonde]** Measured: `valid` → `satisfiable` + formula label + quantifiers preserved; only `statistics` lost. |

### 1.4 Count reconciliation (issue body says 11)

The 11 sites in the issue body correspond to the 11 entries that **flatten into
another formalism's container** with **distinctive data lost**:

- Sites 1, 2, 3, 4, 5, 6, 7 — seven formalisms (ABA, ADF, SetAF, Weighted, Social,
  EAF, DeLP) flattened into `dung_frameworks`.
- Sites 10, 11, 12, 13 — DL, CL, SAT, QBF flattened into their PL/FOL containers.

**Dung-arbitration (#8) and Dung-verification (#9)** are listed in this table
for completeness but are **not flatteners**:
- Dung-verification is the legitimate native writer.
- Dung-arbitration writes into the same container but with the canonical Dung
  shape (attacks as `[src, tgt]` pairs, surviving/eliminated ids). Its loss is
  provenance-only (Walton-Krabbe relations), which the issue body itself flags
  as "less critical".

If the issue body's "11" excludes Dung-arbitration and Dung-verification, the
count matches. If it includes both, the count is 13. The reader should treat
"11" as the **strict** flatteners; the dispatcher should confirm with the
coordinator.

### 1.5 Probe verification (2026-09-07, #1648 DoD item 1)

Every site above was re-derived by **executing** the real invoke, feeding its
actual return dict to the real writer against a fresh `UnifiedAnalysisState`,
then **reading the state back** and comparing field by field. Verdicts quoted
in the `[Corrected 2026-09-07, #1648 sonde]` annotations come from these runs.
The payload shown is the invoke's returned dict (never re-copied from its
source code), and "preserved" always means *read back from the state object*.

**Method.** Per site: `asyncio.run(<real _invoke_*>)` with a synthetic context
supplying the translator-produced keys (opaque ids only — `asm_a`, `arg1`,
`tom`/`jerry`; no corpus text), then the real `_write_*_to_state(output,
state, ctx)`, then re-read `state.dung_frameworks` / `state.fol_analysis_results`
/ `state.propositional_analysis_results`. The initializer warmup follows the
production contract (#1784) — note sites 1-2 (`_invoke_aba`, `_invoke_adf`)
predate #1784 and do **not** warm themselves: without the pipeline's warmup
they fail with `JVMNotRunning` even on a JVM-capable machine. That is a
call-order dependency worth its own issue.

**Environment caveat (measured against Tweety 1.28, prod pins 1.31).**
`jvm_setup` pins `1.31` (`config/settings.py` `JVMSettings.tweety_version`);
this machine has only the 1.28 jars (no Maven to provision 1.31). The probe
ran with `JVM_TWEETY_VERSION=1.28 JVM_TWEETY_LIBS_DIR=libs/java` (both are
legitimate `JVM_`-prefixed settings overrides; `libs/java` holds the genuine
fat jar, while `libs/tweety`'s 35 module jars all match the `-with-dependencies`
name pattern and would fool `_build_tweety_classpath`'s fat-jar fast path into
a one-jar classpath). The writer-contract questions this inventory asks —
*which invoke keys reach the state* — are Python-side and version-independent;
two sites are **not** measurable at 1.28 and are named below, never counted
preserved.

**Measured verdicts (11 of 13):**

| Site | Verdict (re-read from state) |
|---|---|
| 1 ABA | `contraries` → `formalism_specific.contraries` (value-equal); extensions/arguments preserved; `rules_count`/`statistics` dropped; `attacks=[]` |
| 2 ADF | `interpretations` → `extensions.adf_models` (value-equal); `statistics` → sidecar; conditions absent from handler return (upstream gap confirmed) |
| 3 SetAF | `set_attacks` sidecar value-equal; `attacks=[]` by design; retention counters carried; `statistics` dropped |
| 4 Weighted | **weights lost end-to-end**: `attacks=[]` in state, NO `attack_weights` sidecar (see below); `weight_statistics` sidecar value-equal |
| 5 Social | ranking + scores → `extensions`; attacks preserved as pairs; **votes nowhere**; `statistics` dropped |
| 7 DeLP | program/`program_size`/`criterion` → sidecar value-equal; `query_results` → extensions; defeat relations absent; `statistics` dropped |
| 8 Arbitration | all verdict fields reach `extensions`; Walton-Krabbe provenance not elicited (no declared relations supplied) |
| 9 Verification | 11 entries under `semantics="multi"`; arguments/attacks/extensions + retention counters preserved |
| 10 DL | tbox/abox_concepts/abox_roles → sidecar value-equal; `tbox_size`/`abox_size`/`statistics` dropped |
| 12 SAT | solve: `satisfiable`+`model` preserved, `statistics` dropped (cadical backend); MUS: count in label, subsets not in state — vacuous, see below |
| 13 QBF | `qbf_quantifiers` sidecar value-equal; `valid`→`satisfiable`; `statistics` dropped |

**NON MESURÉ (2 of 13), named per the dispatch contract:**

- **Site 6 EAF** — `org.tweetyproject.arg.eaf` has zero classes in the 1.28
  fat jar (`unzip -l | grep -c "arg/eaf"` = 0). The module exists only in the
  versions the fleet's 1.31 pin provides.
- **Site 11 CL** — with the JVM up, `_invoke_cl` raises
  `RuntimeError: ... (too many values to unpack (expected 2))`: a 1.28-vs-1.31
  API shape difference inside the CL handler.

**Pasted probe output (key excerpts, verbatim).**

Weighted — the production-path loss, invoke payload then state entry re-read:

```
[invoke] payload={"semantics": "grounded", "arguments": ["a", "b"], "attacks": [["a", "b", 0.7]], ...}
  (handler built dicts {"source","target","weight"}; _annotate_attack_retention
   #1698 invoke_callables.py:3462 overwrote output["attacks"] with the raw
   input triples before the writer saw them)
[state] entry={"name": "weighted_grounded", "arguments": ["a", "b"], "attacks": [],
  "extensions": {"weighted_extensions": [[]]},
  "formalism_specific": {"weight_statistics": {"min_weight": 0.7, "max_weight": 0.7, "avg_weight": 0.7}}, ...}
[NO ] attack weights reach state
[NO ] binary attack pairs reach state
[YES] weight_statistics reach state  -> formalism_specific.weight_statistics
```

ABA — contraries preserved (contradicts the original row):

```
[invoke] payload={"semantics": "preferred", "extensions": [["asm_a", "asm_b"]],
  "assumptions": ["asm_a", "asm_b"], "rules_count": 1,
  "contraries": {"asm_a": "asm_b", "asm_b": "asm_a"}, "statistics": {...}}
[state] entry={"name": "aba_preferred", "arguments": ["asm_a", "asm_b"], "attacks": [],
  "extensions": {"aba_extensions": [["asm_a", "asm_b"]]},
  "formalism_specific": {"contraries": {"asm_a": "asm_b", "asm_b": "asm_a"}}}
[YES] contraries reach state  -> formalism_specific.contraries
[NO ] rules_count/statistics reach state
```

SAT solve — writer-side `statistics` loss (real backend, not degraded):

```
[invoke] payload={"satisfiable": true, "model": {"p": true, "q": true, "~p": true, "r": true},
  "statistics": {"solver": "cadical195", "num_clauses": 8, "num_variables": 6,
                 "solve_time": 0.0015, "status": "SAT"}}
[state] entry={"id": "pl_1", "formulas": ["SAT: SAT"], "satisfiable": true,
  "model": {"p": true, "q": true, "~p": true, "r": true}}
[YES] satisfiable reaches state   [YES] model reaches state
[NO ] statistics reach state
```

QBF — quantifiers preserved under the renamed key:

```
[state] entry={"id": "pl_1", "formulas": ["QBF: p => q"], "satisfiable": true, "model": {},
  "formalism_specific": {"qbf_quantifiers": [{"type": "forall", "vars": ["x"]},
                                              {"type": "exists", "vars": ["y"]}]}}
[YES] quantifiers reach state  -> formalism_specific.qbf_quantifiers
```

**New findings surfaced by the probe (not in the original inventory):**

1. **Weighted Wave-2 sidecar is dead code on the production path.** The
   handler returns `attacks` as `List[{source, target, weight}]` dicts
   (`weighted_handler.py:139-141`), but `_annotate_attack_retention`
   (#1698, `invoke_callables.py:3462`) overwrites `output["attacks"]` with the
   filtered **input triples**, and the writer's dict-only sanitiser
   (`state_writers.py:1600-1626`) then drops every triple. Net: neither the
   binary pairs nor `attack_weights` ever reach the state, on any Tweety
   version. (SetAF is unaffected: its input shape IS the dict shape.)
2. **MUS backend anomaly.** Z3-MARCO returned `mus_count=0, mus_subsets=[]`
   on three genuinely UNSAT inputs — the MUS-drop verdict above is label-only.
3. **ABA/ADF call-order dependency.** `_invoke_aba`/`_invoke_adf` don't call
   `ready_initializer()` (#1784 predates them); standalone invocation fails
   with `JVMNotRunning` unless something else warmed the JVM first.
4. **`statistics` is the systematic casualty** — dropped at the writer on
   every site that emits one (ABA, SetAF, Weighted-aggregates-only, Social,
   DeLP, DL, SAT, QBF).

---

## 2. Hard-coded `attacks=[]` verdict (ABA / ADF / SETAF / DeLP)

The issue body singles out ABA and ADF as "aggravated" because they hard-code
`attacks=[]`. This section answers: for each formalism, is the empty list the
**correct representation** of the formalism, or is it a **real loss**?

### 2.1 ABA — REAL LOSS

**Handler return** (`aba_handler.py:115-125`):
```python
{"semantics", "extensions", "assumptions", "rules_count", "statistics"}
```
**No `attacks` key, no `contraries` key.** Contraries were consumed at
`invoke_callables.py:3610,3640` (`contraries = context.get("contraries")`) and
passed to `handler.analyze_aba_framework`. The handler uses them **inside**
Tweety to build the `AbaTheory` (line 87-92 in `aba_handler.py`), but the
returned dict does **not** surface them.

**Consequence:** the writer's `attacks=[]` is a real loss **at the invoke /
handler level**, not the writer's fault. To fix it, the handler would have to
return `{"contraries": ..., "attacks_from_contraries": [...]}` and the writer
would have to project the contrary-derived attacks. **The writer alone cannot
fix this site** — the loss is upstream.

The semantic correctness claim: a Dung AF with `arguments=assumptions` and
`attacks=[]` has a grounded extension equal to all assumptions → ABA cannot
refute anything via this projection. The "aggravated" framing in the issue
body is correct.

### 2.2 ADF — FORMALLY CORRECT, STRUCTURE LOST

ADF is **not** a Dung-style binary attack framework. Its native data is
acceptance conditions (`Dict[statement, {tautology|contradiction|negation:stmt}]`,
`adf_handler.py:89-103`). The semantics computes **interpretations** (3-valued
valuations), not extensions over a binary attack relation.

**Consequence:** `attacks=[]` is **the correct representation** — there are no
attacks to project. The loss is the **acceptance conditions** themselves (and
the interpretations computed from them). The handler returns
`{semantics, statements, interpretations, statistics}` (`adf_handler.py:114-123`)
— conditions are NOT returned.

**[Corrected 2026-09-06, #2063]** This section originally claimed "the fix is
not at the writer" and that `extensions={"adf_models": ...}` was "already
there". Both were wrong for the writer: it read `models`/`extensions` — keys
the handler never writes — so `adf_models` was `[]` on every run while the
interpretations (and `statistics`/`degraded`/`note`) went to the floor. The
writer now reads `interpretations` and carries the provenance fields in a
strictly-additive `formalism_specific` sidecar (ABA Wave-2 model — no dedicated
container: a container without a reader is a self-made mode-1). The acceptance
conditions themselves remain an upstream (handler) gap, unchanged.

### 2.3 SetAF — LOSS AT THE WRITER (handler returns attacks, writer drops them)

**Handler return** (`setaf_handler.py:120-131`):
```python
{"semantics", "arguments", "attacks", "extensions", "extensions_count", "statistics"}
```
**The handler does return `attacks`** as the original `List[{attackers: List[str], target: str}]`
(line 123). The writer explicitly drops them:
```python
state.add_dung_framework(
    ...
    attacks=[],  # set attacks don't map to binary attacks
    extensions={"setaf_extensions": output.get("extensions", [])},
)
```

**The comment is honest** — SetAF's joint (set) attacks are not binary
Dung-style. The writer cannot store them in the binary `attacks` field without
loss. But the writer drops them entirely from the extensions dict too, so
**the joint-attack information is unreachable from the state**.

**The fix is structural.** A dedicated `set_attacks` field, or a
`{"set_attacks": [...]}` key inside `extensions`, would preserve the data
without breaking the Dung contract. Section 4 evaluates this option.

> **[Corrected 2026-09-07, #1648 sonde]** The last two paragraphs are
> historical: the Wave-2 sidecar shipped exactly this fix —
> `entry["formalism_specific"]["set_attacks"]`, measured value-equal against
> the handler's echo on the real invoke→writer path (§1.5). The joint attacks
> are reachable from the state; only the binary `attacks=[]` projection
> remains, by design.

### 2.4 DeLP — WHOLE FORMALISM IS GONE

DeLP has **arguments** (literal `~arg` rules, strict and defeasible), **defeat
relations** (a defeat is a relation between arguments under a comparison
criterion), and **warrant** verdicts (per query). The handler returns
`{program, program_size, criterion, query_results: [{query, answer, message}]}`
(`delp_handler.py:149-158`). The writer stores ONLY:
```python
arguments=[],
attacks=[],
extensions={"delp_query_results": query_results},
```
(`state_writers.py:1260-1265`).

**This is the deepest flattening of the inventory.** A DeLP run produces
literally nothing that survives the writer except a list of `(query, answer,
message)` triples. The argument graph, the defeat relations, the comparison
criterion — all gone. A reader looking at `state.dung_frameworks["delp_analysis"]`
sees an empty AF plus a query-result bag. The fix cannot be at the writer level
alone; it requires a **dedicated DeLP container** (or a `formalism_specific`
sidecar — see Section 4).

---

## 3. Reader inventory

This section inventories ALL production consumers of the three target containers
(grep over `argumentation_analysis/`, excluding `tests/`). For each, we ask:
what does it read, and does it **aggregate over the container as a whole** (in
which case heterogeneous flattened entries pollute the aggregate)?

### 3.1 Readers of `state.dung_frameworks`

| Reader (file:line) | Reads | Aggregate / per-entry | Affected by flattening? |
|--------------------|-------|------------------------|--------------------------|
| `reporting/restitution/act2_narrative_plugin.py:332-375` (`_dung_rejected_by_arg`) | Iterates `frameworks.items()`, reads `arguments` + `extensions` per entry; computes arg ∈ `arguments` but ∉ `extensions` → "rejected". | **Per-entry**. Rejection verdict per `(arg, semantics)`. ABA / SetAF / ADF entries contribute their `extensions` (computed) — so this reader DOES receive the flattened data, but interprets it as Dung extensions. | **Partial.** ABA returns ABA extensions as the `extensions` value; the rejection logic at line 372-374 will treat every argument NOT in any ABA extension as "rejected by ABA semantics" — which is correct for ABA. The reader does not crash, but ABA / ADF / SetAF semantics get the same "Dung" reading. |
| `reporting/restitution/act2_narrative_plugin.py:384-428` (`_collect_dung_trace`) | Picks the first `verification_*` entry (line 411-414). **Ignores `aba_*`, `adf_*`, `setaf_*`, `weighted_*`, `eaf_*`, `delp_analysis`, `social_af` entries** (only matches `verification_<sem>` names). | Single-entry. | **The flatteners are NOT read here** — the reader explicitly filters by name. Confirms the flatteners are inert for this code path. |
| `reporting/restitution/act3_conclusion_plugin.py:530-562` (`_dung_rejected_by_arg`) | Same logic as act2 — iterates all frameworks, computes rejection per `(arg, semantics)`. | **Per-entry**. | Same partial effect as act2. |
| `visualization/html_report.py:516-553` (Dung visualisation) | Iterates `dung_frameworks.values()`, takes the **first** entry (line 548-550). Reads `arguments` + `attacks` + `extensions`. Renders the graph for HTML/JS. | Single-entry (first wins). | **CRITICAL.** The first framework in the dict is **implementation-order-dependent**. ABA / ADF / SetAF writers all use `attacks=[]` → empty graph rendered. With DL / SAT / CL / QBF → no effect (different container). Pattern_mining also reads the first entry — see below. |
| `evaluation/pattern_mining.py:75-114` (`DungTopologyDetector`) | Takes the first framework (line 90), reads `arguments`, `attacks`, `extensions`. Computes `n_attacks / n*(n-1)` density. | Single-entry + density metric. | **CRITICAL.** For ABA / ADF / SetAF, `attacks=[]` → `density=0`. The "dung_unsupported" detection at line 402-418 uses `attacks` as a dict-shape `{from, to}` (line 414-416) — but the writer stores `[src, tgt]` lists. **Two shape mismatches at once**: empty for formalisms that DO have attacks (ABA contraries, SetAF joint attacks, EAF epistemic), and dict-vs-list for the rest. |
| `evaluation/pattern_mining.py:400-418` (formal-signals aggregation) | Iterates ALL frameworks, sums `attacks` (expecting dicts with `{from, to}`). | **Aggregate.** | **CRITICAL.** ABA / ADF / SetAF contribute zero attacks → `dung_unsupported` is under-counted at the corpus level. **The flattened sites SILENTLY zero out a corpus-level signal.** |
| `reporting/restitution/act3_conclusion_plugin.py:530` (used downstream by `_collect_weak_points`) | Same as act2. | Per-entry → aggregated into `StructuringWeakPoint` list. | Same partial effect. |
| `agents/core/synthesis/deep_synthesis_agent.py:587-603` (`_build_dung_structure`) | First entry, reads `name`, `arguments`, `attacks`, `extensions.{grounded,preferred,stable}`. | Single-entry. | **CRITICAL.** ABA's `extensions={"aba_extensions": [...]}` doesn't have a `grounded` / `preferred` key — `extensions.get("grounded", [])` returns `[]` → ABA's grounded extension reported as empty. Same for ADF (`adf_models`). Same for SetAF (`setaf_extensions`). The deep synthesis agent interprets these as "the framework found no extension" — **the flattening directly corrupts the restitution narrative**. |
| `agents/core/synthesis/deep_synthesis_agent.py:1267-1277` (deep context dump) | Iterates up to `max_items_per_field`, formats `name / args=N / attacks=N / grounded_extension=...`. | Per-entry (capped). | ABA / ADF / SetAF report `attacks=0`, `grounded_extension=[]` — same narrative corruption as above. |
| `reporting/reprompt_trace.py:23` | Listed in trace field whitelist. | n/a (just lists the key). | Not affected. |
| `cli/output_formatter.py:212,289` | Counts frameworks, renders summary. | Aggregate count only. | Not affected (count is correct). |
| `reporting/multi_format_exporter.py:28` | Display label only. | n/a. | Not affected. |
| `evaluation/sanitize_state.py:97-160` | Opacification of `arguments` (line 102), `attacks` (line 102), `extensions.{extensions, all_members}` (line 122). | n/a — privacy discipline, no semantics. | Not affected. |
| `services/web_api/services/framework_service.py:36-61` | Standalone Dung analysis endpoint (independent of state). | n/a — separate code path. | Not affected. |
| `plugins/tweety_logic_plugin.py:93-120` | `analyze_dung_framework` (SK plugin). | n/a — produces an invoke result, not a reader. | Not affected. |
| `plugins/narrative_synthesis_plugin.py:143,239` | Same logic as act2 (`_dung_rejected_args`). | Per-entry. | Same partial effect. |

**Summary for `dung_frameworks` readers.** Two readers aggregate across the
container and are sensitive to the flattened entries:
1. **`pattern_mining.py:402-418`** — corpus-level `dung_unsupported` signal is
   under-counted because ABA / ADF / SetAF contribute zero attacks.
2. **`deep_synthesis_agent.py:587-603`** — narrative corruption (single-entry
   wins, ABA's "grounded_extension" is empty even when extensions exist).

All other readers either filter by name (so flatteners are inert) or only count
(so shape is irrelevant).

### 3.2 Readers of `state.fol_analysis_results`

| Reader (file:line) | Reads | Aggregate / per-entry | Affected by flattening? |
|--------------------|-------|------------------------|--------------------------|
| `reporting/restitution/act2_narrative_plugin.py:844-884` | Iterates `fol` (list of dicts), reads `consistent` (None/True/False) and `message`. Aggregates consistent/inconsistent counts. | **Aggregate.** | **Partial.** Verdict IS preserved by DL writer (line 1155-1160). The corpus-level consistent count is correct. **What is lost is the FOL-vs-DL distinction** — a reader cannot tell which entry came from DL and which from real FOL. If a corpus mixes FOL theories and DL ontologies, the count lumps them together. |
| `reporting/restitution/appendix.py:55-111` (`_fol_axis_status`) | Same: reads `consistent` + `formulas` (for the "formules" count). | Aggregate tri-state (decided / degraded / indisponible). | **Partial.** Decision counts correct. The `formules` field shows `1` for DL entries (the synthesised `"DL: ..."` string) versus N for real FOL entries (the formula list). A corpus-level `formules: 1` could be a single FOL theory OR a single DL ontology — **the axis label is correct but the granularity is lost**. |
| `reporting/restitution/state_adapter.py:27` | Listed as a spec §2 axis key — passed verbatim to the renderer. | n/a (key pass-through). | Not affected semantically. |

**Summary for `fol_analysis_results` readers.** The verdict is preserved by DL;
the **origin** (FOL vs DL) is not. The aggregation is **safe** but
**indistinguishable** — a restitution cannot say "FOL said X, DL said Y" if
both wrote into the same container.

### 3.3 Readers of `state.propositional_analysis_results`

| Reader (file:line) | Reads | Aggregate / per-entry | Affected by flattening? |
|--------------------|-------|------------------------|--------------------------|
| `reporting/restitution/act2_narrative_plugin.py:815-842` | Iterates `pl` (list of dicts), reads `_pl_verdict(r)` (which reads `satisfiable` then `consistent` for legacy). Aggregates satisfiable/insatisfiable counts. | **Aggregate.** | **Safe for verdict counts.** The verdict (satisfiable) is preserved by CL, SAT, QBF writers. **Origin is lost** — SAT, CL, QBF, and the real PL all contribute to the same counter. |
| `reporting/restitution/appendix.py:170-199` (`_pl_axis_status`) | Same logic — tri-state satisfiable verdict. | Aggregate tri-state. | Same partial effect. |
| `reporting/restitution/state_adapter.py:26` | Key pass-through. | n/a. | Not affected. |

**Summary for `propositional_analysis_results` readers.** Same verdict-preserved,
origin-lost pattern as FOL. The corpus-level PL-axis verdict is correct; the
PL-vs-CL-vs-SAT-vs-QBF distinction is gone.

---

## 4. Recommended single remedy

The issue body proposes three options. This section evaluates them against the
reader inventory above.

### Option 1 — Dedicated container per formalism + dedicated readers

**Effort.** High. Each of the 7+3 (Dung-side) + 1 (DL) + 3 (PL-side) formalisms
gets its own container (e.g. `state.aba_frameworks`, `state.adf_models`,
`state.set_attacks`, `state.weighted_attacks`, `state.social_scores`,
`state.eaf_beliefs`, `state.delp_arguments`, `state.dl_ontology`,
`state.cl_conditionals`, `state.sat_mus_subsets`, `state.qbf_quantifiers`).
Each reader grows a branch per formalism. The restitution must thread all 11
containers into the R6 narrative.

**Risk.** As the issue body warns ("un conteneur sans lecteur est un mode 1
fabrique de nos propres mains"): a new container with no reader is the same
silently-empty failure the issue is trying to fix. The contract MUST include
the reader migration as a single atomic change.

**Verdict.** **Faithful** (no information loss) but **expensive** and **risk-prone**
(multi-reader migration can produce silent omissions). Only justified if a
reader of one formalism should NEVER see another's data — which is not the
case here (restitution aggregates, but it aggregates at the verdict level, not
at the formalism-specific level).

### Option 2 — Single enriched container with `formalism_specific` field

**Effort.** Medium. Extend `state.dung_frameworks[*]` (and the two others) with
a sidecar `formalism_specific: Dict[str, Any]` carrying the lost data:
- ABA: `{"contraries": {...}, "extensions_by_semantics": {...}}`
- ADF: `{"acceptance_conditions": {...}, "interpretations": [...]}`
- SetAF: `{"set_attacks": [...]}` (joint attacks)
- Weighted: `{"weights": {...}, "weight_statistics": {...}}`
- Social: `{"votes": {...}, "scores": {...}}`
- EAF: `{"epistemic_beliefs": {...}}`
- DeLP: `{"arguments": [...], "defeat_relations": [...], "criterion": "..."}`
- DL: `{"tbox": [...], "abox_concepts": [...], "abox_roles": [...], "subsumptions": [...]}`
- CL: `{"conditionals": [...]}` (the raw CL formula list)
- SAT/MUS: `{"mus_subsets": [...]}` (the actual subsets)
- QBF: `{"quantifiers": [...]}`

Readers that don't care about the sidecar ignore it; readers that do
(formalism-specific consumers) opt in. The existing projection stays — `attacks`
remains binary, `formulas` remains a list — so backward compatibility is
preserved.

**Risk.** The sidecar can become a "fourre-tout" (the issue body's stated
concern). To avoid that, **the sidecar MUST be typed** (a per-formalism TypedDict
in `shared_state.py`) and **the existing readers' contract must explicitly
forbid reading from `formalism_specific`**.

**Verdict.** **Best fit.** Faithful, backward-compatible, single change,
the reader inventory (Section 3) shows that existing readers ONLY consume the
projected fields (`attacks`, `extensions.grounded`, `consistent`, `satisfiable`,
`message`) — none of them would read the sidecar. New formalism-specific
readers (e.g. for ABA contraries, for QBF quantifiers) opt in explicitly.

### Option 3 — Documented lossy projection + parallel preservation

**Effort.** Low. Add a `lossy_projection: True` flag (or similar) to each
flattened entry, plus a parallel `state.formalism_specific: Dict[capability, Any]`
container carrying the lost data. Document at the writer level which fields are
preserved vs lost. Update the readers' contracts to say "this reader reads the
projection only — formalism-specific data is in `state.formalism_specific`".

**Risk.** Same as Option 2 plus the doc-discipline requirement. If the doc
isn't maintained, the projection silently re-becomes the projection-of-record.
This is precisely the current state (de facto lossy, de jure undocumented).

**Verdict.** **Acceptable but inferior.** Option 2 + a brief docstring at the
container level achieves the same outcome with a cleaner type contract.

### **Recommended: Option 2 (enriched container with `formalism_specific` sidecar)**

**Reasoning anchored in Section 3:**
- **Verdict-level readers** (act2 / act3 / appendix / pattern_mining density):
  read only `consistent`, `satisfiable`, `arguments`, `attacks`, `extensions`
  — projection is sufficient for them.
- **Narrative-level readers** (deep_synthesis_agent): currently single-entry,
  picks first framework — **already broken** under the current flattening
  (ABA's `extensions={"aba_extensions": [...]}` does not have `grounded` /
  `preferred` keys, so the deep synthesis gets `[]`). Adding `formalism_specific`
  is not a regression here — the existing readers stay unchanged, the new
  field is opt-in.
- **Corpus-level signals** (pattern_mining `dung_unsupported`): unaffected by
  adding the sidecar. The current under-counting is **preserved as-is** (a
  separate fix); the sidecar gives future readers the data to compute the
  correct count.

**One single change, applied to all 11 sites at once** (per the issue body's
mandate: "Un remede unique est choisi et applique aux onze sites"). One
TypedDict in `core/shared_state.py`, one read in each of the 11 writers, one
typed `formalism_specific` per capability.

### 4.1 Pre-recommendation checks

Before the remedy is applied, the issue body's DoD must be addressed:

1. **Per-module comparison (invoke vs state):** the inventory above IS that
   comparison — "Distinct info lost" enumerates the gap. Future issue: run a
   one-shot test that diffs `invoke_output` against `state.<container>[<id>]`
   per capability and prints the gap. (This is the same anti-#1019 family as
   `feedback_injected_fakes_hide_real_shape_bugs.md`.)
   **[Corrected 2026-09-07, #1648 sonde]** That one-shot diff has now been run
   — 11 of 13 sites executed end-to-end (produce → write → re-read); verdicts
   in §1.5, per-row corrections above. Two sites (EAF, CL) are non-measurable
   on the local 1.28 jars and are named, not counted.

2. **Reader impact measurement:** Section 3 inventories the readers. The
   **before/after** measurement on `pattern_mining.py:402-418` (`dung_unsupported`)
   and `deep_synthesis_agent.py:587-603` (grounded_extension reads) is the
   concrete number the coordinator wants.

3. **`attacks=[]` for ABA/ADF tranché:**
   - **ADF: correct (formally).** Interpretations surfacing is DONE writer-side
     (#2063, 2026-09-06: phantom key `models`/`extensions` fixed, provenance in
     the `formalism_specific` sidecar); the acceptance conditions remain a
     handler-side gap. The attack list stays empty — by construction.
   - **ABA: real loss.** Contraries are upstream of the handler's return dict.
     Either the handler returns `contraries` (and the writer projects the
     contrary-derived attacks), OR a `formalism_specific.contraries` carries
     them.
     **[Corrected 2026-09-07, #1648 sonde]** Both halves are already true and
     measured: the handler returns `contraries`, and the sidecar carries them
     value-equal (§1.5). This bullet is resolved; the remaining ABA losses are
     `rules_count`/`statistics`.
   - **SetAF: writer-side loss.** Handler returns the joint attacks. Fix is
     a `formalism_specific.set_attacks`.
     **[Corrected 2026-09-07, #1648 sonde]** Shipped (Wave-2) and measured —
     resolved.
   - **DeLP: structural.** A `formalism_specific` carrying the DeLP argument
     tree + defeat relations is the minimum viable preservation.
     **[Corrected 2026-09-07, #1648 sonde]** Half-shipped and measured: the
     sidecar carries the program text, `program_size` and `criterion`; defeat
     relations remain absent.

---

## 5. Anti-#1019 regression test idea

The issue body's DoD item 5 demands "Un test qui **échouerait aujourd'hui** :
un module du mode 2 dont l'information distinctive est présente en entrée et
absente après relecture".

**Test concept: `test_1648_aba_writer_preserves_contraries`**

**Setup:**
1. Build a small `UnifiedAnalysisState` (via `core.shared_state.UnifiedAnalysisState`).
2. Stub `ABAHandler.analyze_aba_framework` to return a controlled dict:
   ```python
   {
       "semantics": "preferred",
       "extensions": [["a", "b"], ["a", "c"]],
       "assumptions": ["a", "b", "c"],
       "rules_count": 2,
       "statistics": {"assumptions_count": 3, "rules_count": 2, "extensions_count": 2},
   }
   ```
   (Stubbing the handler avoids JVM / Tweety dependency. The contract under
   test is **the writer**, not the handler.)
3. Inject context `{"contraries": {"a": "b", "b": "a", "c": "a"}}` so the
   distinctive ABA data is in the writer's input path.

**Action:** call `_write_aba_to_state(output, state, ctx)`.

**Assertions (today, the test FAILS):**
- After the call, `state.dung_frameworks` contains ONE entry with name
  `aba_preferred`.
- That entry's `attacks` field contains at least one pair `[a, b]` (because
  `a`'s contrary is `b`, ABA's native semantics gives a `(a, b)` attack).
  **Today this assertion FAILS** — the writer hard-codes `attacks=[]`.
- (Stretch, after the remedy:) that entry's `formalism_specific.contraries`
  equals `{"a": "b", "b": "a", "c": "a"}`.

**Why this catches the flattening bug.** The test pins the writer's contract:
**if the writer receives an ABA output (and the context carries contraries),
the state MUST reflect that the framework has attacks.** Today's writer
silently writes `attacks=[]` and the test fails — the assertion message names
exactly the gap ("ABA writer dropped contraries-derived attacks; `attacks` is
`[]` but should contain `[a, b]`").

**Anti-#1019 discipline.** The stub returns a real, non-empty, distinctively
ABA-shaped output. The assertion reads through the canonical writer, not a
mocked one. This is the same family as the R761 #1643 / R764 #1636 / R765 #1662
fixes: the test must drive the **real code path** and observe the real loss.

**Location.** Suggested: `tests/unit/argumentation_analysis/orchestration/test_state_writers_1648.py`.
Symmetric tests for ADF / SetAF / Weighted / Social / EAF / DeLP / DL / CL /
SAT / QBF can be added in the same file, one per site, all failing today.

**Per-site cost.** Each stub is ~10 lines. The total file is ~250 lines for
11 sites. The test runs without JVM (all stubs), so it is CI-friendly.

---

## Appendix A — File-and-line index (for citable review)

| Site | Writer file:line | Invoke file:line | Handler file:line | Reader file:line (key) |
|------|------------------|------------------|-------------------|------------------------|
| ABA | `state_writers.py:831-845` | `invoke_callables.py:3603-3646` | `aba_handler.py:59-128` | `act2_narrative_plugin.py:332-375` |
| ADF | `state_writers.py:848-861` | `invoke_callables.py:3649-3668` | `adf_handler.py:61-126` | `act2_narrative_plugin.py:332-375` |
| SetAF | `state_writers.py:1199-1209` | `invoke_callables.py:4126-4180` | `setaf_handler.py:69-134` | `pattern_mining.py:402-418` |
| Weighted | `state_writers.py:1212-1226` | `invoke_callables.py:4183-4249` | `weighted_handler.py:73-153` | `pattern_mining.py:402-418` |
| Social | `state_writers.py:1229-1240` | `invoke_callables.py:4252-4277` | `social_handler.py:56-133` | `act2_narrative_plugin.py:332-375` |
| EAF | `state_writers.py:1243-1252` | `invoke_callables.py:4317-4342` | `eaf_handler.py:71-130` | `act3_conclusion_plugin.py:530-562` |
| DeLP | `state_writers.py:1255-1265` | `invoke_callables.py:4345-4384` | `delp_handler.py:117-164` | `deep_synthesis_agent.py:587-603` |
| Dung-arbitration | `state_writers.py:1067-1125` | `invoke_callables.py:7974-8048` | n/a (pure Python) | `act2_narrative_plugin.py:332-375` |
| Dung-verification | `state_writers.py:1037-1064` | `invoke_callables.py:7057-7973` | n/a (delegate to AF handler) | `act2_narrative_plugin.py:384-428` |
| DL | `state_writers.py:1144-1160` | `invoke_callables.py:3971-4000` | `dl_handler.py:161-198` | `act2_narrative_plugin.py:844-884`, `appendix.py:55-111` |
| CL | `state_writers.py:1163-1174` | `invoke_callables.py:4003-4034` | `cl_handler.py:178-212` | `act2_narrative_plugin.py:815-842`, `appendix.py:170-199` |
| SAT | `state_writers.py:1177-1196` | `invoke_callables.py:4037-4120` | `sat_handler.py` (external) | `act2_narrative_plugin.py:815-842` |
| QBF | `state_writers.py:1268-1276` | `invoke_callables.py:4387-4415` | `qbf_handler.py:152-177` | `act2_narrative_plugin.py:815-842` |

## Appendix B — Reader-aggregation impact (recap)

| Reader | Aggregation | Today's behaviour under flatteners | With Option 2 sidecar |
|--------|-------------|------------------------------------|------------------------|
| `pattern_mining.DungTopologyDetector` | Single-entry (first) | ABA / ADF / SetAF first → `n_attacks=0`, `density=0` | Unchanged (sidecar ignored). Future reader could compute correct density. |
| `pattern_mining.formal_signals` (line 402) | Aggregate over all | ABA / ADF / SetAF contribute `0` attacks → `dung_unsupported` under-count | Unchanged (sidecar ignored). Future reader could fix. |
| `deep_synthesis_agent._build_dung_structure` | Single-entry (first) | ABA's `extensions={"aba_extensions": [...]}` → `grounded_extension=[]` reported | Unchanged. Future reader could read sidecar. |
| `act2_narrative._dung_rejected_by_arg` | Per-entry | Each flattener contributes its own rejection set | Unchanged. |
| `act2_narrative._collect_dung_trace` | Filters by `verification_*` | Flatteners are inert (filtered out) | Unchanged. |
| `act2_narrative._pl_finding` (line 815) | Aggregate verdict | CL/SAT/QBF verdicts lumped with PL — count correct, origin lost | Unchanged. **Origin could be surfaced via `formalism_specific`.** |
| `act2_narrative._fol_finding` (line 844) | Aggregate verdict | DL verdict lumped with FOL — count correct, origin lost | Unchanged. **Origin could be surfaced via `formalism_specific`.** |
| `appendix._pl_axis_status` / `_fol_axis_status` | Tri-state aggregate | Same as act2 — verdict correct, origin lost | Unchanged. |
| `html_report` (line 548) | Single-entry (first) | Same as deep_synthesis — first wins | Unchanged. |

**Pattern.** Under Option 2, all existing readers stay **byte-for-byte identical**.
The remedy is **strictly additive**: new sidecar, new writers, no reader
migration. New formalism-specific readers can be written later without
coordinating with the existing readers.

---

## Appendix C — Anti-pendule notes (for the coordinator)

1. **Do not** add 11 dedicated containers (Option 1). The reader inventory
   shows that verdict-level aggregation works today; only the formalism-specific
   dimension is lost. Sidecar is sufficient.
2. **Do not** treat `attacks=[]` as a uniform bug. For ADF, it is **correct**;
   the fix is upstream (return the acceptance conditions). For ABA, the fix is
   upstream too (return the contraries). For SetAF, the fix is at the writer
   (preserve joint attacks in the sidecar). For DeLP, the fix is structural
   (the whole formalism needs a sidecar).
3. **Do not** migrate readers in the same PR as the writer change. The whole
   point of the sidecar is that the existing readers stay unchanged.
4. **Do not** add a `formalism_specific: Dict[str, Any]` (untyped). The
   sidecar must be a TypedDict (or a per-formalism dataclass) so a reader
   cannot accidentally fish random keys out of it.
5. **Do not** claim the remedy fixes `pattern_mining.dung_unsupported` under-
   counting. The sidecar preserves the data; a future PR can write the reader
   that uses it. Confusing "data preserved" with "signal computed" is the
   pendulum the issue body warns against.

---

*Inventory produced for Epic `#1644`, issue `#1648`. Read-only investigation;
no production code modified. Dispatcher will commit as docs-only.*
