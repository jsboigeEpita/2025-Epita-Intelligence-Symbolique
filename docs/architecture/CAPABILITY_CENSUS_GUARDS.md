# Capability census guards

Moved verbatim from the root `CLAUDE.md` (claudish#874: the root file is re-read by every request of this workspace; its detail is read here, on demand). The root file keeps the rule and a pointer to this page.

These rules sit under `Architecture → Semantic Kernel Plugins` in the root file. They describe how the capability surface is counted and guarded.

> ⚠ **Counting `@kernel_function` with a plain grep over-counts**: the class docstrings of
> `quality_scoring_plugin.py` and `french_fallacy_plugin.py` each open a line with
> `@kernel_function`, which `grep -c '^\s*@kernel_function'` scores as a decorator. Count the
> decorated `def`s, not the decorator lines.

> ⚠ **One capability surface per module** (#1842, resolved): `debate`, `governance`,
> `quality` and `synthesis/deep_synthesis_agent` each used to declare capabilities on a
> second surface (`__init__.register_with_capability_registry`) that only tests — or nobody —
> called. Those dead functions are deleted; the one table per module is the production
> surface `orchestration/registry_setup.py` populates (`counter_argument` keeps its module
> function, which `setup_registry` imports and calls). Each specialist's routing entry is
> the capability production demands: `adversarial_debate`, `argument_quality`,
> `governance_simulation`, `counter_argument_generation`, `deep_synthesis` — internal
> features (scoring, virtues, voting methods) are not separate registry entries.
> `tests/unit/argumentation_analysis/orchestration/test_one_capability_surface_1842.py`
> guards the surface: any new unwired definer reddens, and so does any **new**
> declared capability with zero production demanders. The orphans the tree
> already carries are named debt, not silence: each sits in the guard's
> `PENDING_TRIAGE` map with the issue owning its triage (#1604 — components with
> no demanded name, a wire-or-retire decision; 9 pairs / 6 components, measured
> 2026-09-27 on #1604's branch — the figure moves with every triage that lands,
> re-measure before quoting). The census reads registrations made inside
> `for name, caps, ... in <rows>:` loops and fails on a register call it cannot
> read: before #1604 it skipped them, which hid 32 of 56 components. The map
> shrinks as triage lands and never grows to absorb new silence; a stale
> entry reddens on its own, whether its
> component stopped declaring it or production started demanding it. When adding a
> capability, add it to the surface `setup_registry` populates, **and give it
> a consumer** — a phase asking for it, or a capability table a resolver reads.

> ⚠ **"Requested" means `add_phase(capability="…")`, not a `find_*` grep.**
> Phases are what consume capabilities: `workflow_dsl.py` resolves `phase.capability` through
> `find_for_capability` at run time, and `argumentation_analysis/` carries **48** distinct
> `capability=` phase literals. The resolver has **five spellings**, and they partition
> sharply: production calls *only* the untyped `find_for_capability` (12 sites across six
> modules — `workflow_dsl`, `router`, `hierarchy_bridge`, `capability_eval`, and the two MCP
> tool modules), while the three typed variants
> (`find_agents_`/`find_plugins_`/`find_services_for_capability`) have **zero** production
> callers and live entirely under `tests/`. A grep on one spelling therefore measures
> whichever half it matched, not the resolver — enumerate the surface before counting it.
> Scope every figure, too: `argument_quality` (**22** production phases, 30 counting tests),
> `counter_argument_generation` (13 / 16), `governance_simulation` (11 / 15) and
> `adversarial_debate` (9 / 11) are all consumed on real runs; the production figure is the
> one a claim about real runs may quote.
> `tests/unit/argumentation_analysis/orchestration/test_capability_resolver_surface_1980.py`
> re-derives the partition — it reddens when a sixth spelling appears or a typed variant gains
> a production caller, not when the codebase grows.
> A capability is also requested through a **table** a resolver reads with a variable
> (`for cap in caps: registry.find_for_capability(cap)`): the hierarchical bridge map
> `_OBJECTIVE_CAPABILITY_MAP`, the delegation `LEGACY_TO_REGISTRY_CAPABILITY`, the router's
> `KNOWN_CAPABILITIES`. No literal grep sees that demand; the #1842 census counts it since
> #2424 (`_capability_tables`), and `test_table_carried_demand_resolves` holds every name a
> table carries to a provider of `setup_registry()` — `TABLE_DEMAND_GAPS` names the exceptions.
> Since #2788 the census also reads **row tables** that a loop unpacks into
> `add_phase(capability=<var>)` (the evaluation workflows, the router's optional phases), and the
> literal form on all three phase callees (`add_phase`, `add_conditional_phase`, `add_loop`). A
> phase capability it cannot read fails the census, unless `DYNAMIC_PHASE_CAPABILITIES` names
> the site and where its demand is measured.
