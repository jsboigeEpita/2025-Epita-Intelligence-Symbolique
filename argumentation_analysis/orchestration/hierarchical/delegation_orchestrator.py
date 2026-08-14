"""
M3 — True hierarchical 3-tier delegation orchestrator (RA-10 #1069 / ORC-2).

Restores the dormant strategic→tactical→operational delegation chain as a
*selectable* orchestration axis, comparable to the M2 "bridge" path
(`HierarchicalOrchestrator` → `objectives_to_workflow` → `WorkflowExecutor`).

Why dormant, not deleted
------------------------
The 3-tier decomposition / translation logic in
``strategic/manager.py``, ``tactical/coordinator.py`` and
``interfaces/tactical_operational.py`` is fully intact. The chain is unwired
*only* because two pub/sub auto-subscription points were deliberately
commented out:

* ``TaskCoordinator._subscribe_to_strategic_directives`` (coordinator.py:257)
* ``OperationalManager._subscribe_to_messages`` (operational/manager.py:310)

Rather than re-enable async pub/sub (and its message-bus race conditions),
M3 drives the tiers by **explicit sequential calls** — deterministic, unit
testable, and reusing the existing translation logic untouched.

Anti-pendule (#1019 / north-star R311)
--------------------------------------
M3 does **not** replace the DAG/bridge (M2). Both remain selectable via the
``--hierarchical-mode {bridge,delegation}`` flag. Degraded delegation
**fails loud**:

* If the strategic tier yields zero objectives, raise :class:`DelegationError`
  instead of silently injecting a hardcoded objective list. (The M2 bridge's
  hardcoded 4-objective fallback at ``orchestrator.py:102-128`` is the explicit
  contrast point this module refuses to imitate.)
* If a required operational capability has no provider, the per-task result is
  an honest ``status="failed"`` propagated upward — never a heuristic
  substitution.
"""

from typing import Any, Awaitable, Callable, Dict, List, Optional
import logging

from argumentation_analysis.orchestration.hierarchical.strategic.manager import (
    StrategicManager,
)
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import (
    TaskCoordinator,
)
from argumentation_analysis.orchestration.hierarchical.interfaces.tactical_operational import (
    TacticalOperationalInterface,
)
from argumentation_analysis.orchestration.hierarchical.hierarchy_bridge import (
    RegistryBackedOperationalRegistry,
)

logger = logging.getLogger(__name__)

# Type alias for the operational tier seam: a command dict in, a result dict out.
OperationalExecutor = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]

# CC #1531 item 1 — the operational tier ALREADY tells us, honestly, when it
# could not analyse. Nobody was listening: the aggregation below counted
# ``status == "completed"`` (a task RAN) and called it a success rate (a task
# PRODUCED), so a provider announcing its own unavailability rolled up into
# "performance globale élevée". That is the #1019 pattern in its canonical
# form — a degradation flag with no consumer.
#
# The keys below are grounded in the actual writers, not invented (a flag read
# from a key nobody writes fabricates a zero just as surely as one nobody
# reads discards a truth):
#   * ``degraded: True``                 — invoke_callables.py (many sites)
#   * ``status: "unavailable"``          — adapters/dung_student_provider.py:205
#   * ``extraction_status: "failed:..."`` — invoke_callables.py:5414
_DEGRADED_OUTPUT_STATUSES = frozenset({"unavailable", "failed", "error", "degraded"})


def _degradation_reasons(outputs: Any) -> List[str]:
    """Collect the operational tier's own degradation self-reports.

    Returns a (possibly empty) list of short reason strings. Empty means the
    provider made no claim of degradation — **not** that it produced content.

    That distinction is the whole point. A provider that ran fine over a clean
    corpus and honestly found zero fallacies is a *success* that returns zero;
    treating every empty output as a failure would be the mirror error, and
    would make the verdict lie in the other direction. Only a self-declared
    non-analysis is counted here.
    """
    if not isinstance(outputs, dict):
        return []
    reasons: List[str] = []
    if outputs.get("degraded") is True:
        reasons.append("degraded")
    status = outputs.get("status")
    if isinstance(status, str) and status.lower() in _DEGRADED_OUTPUT_STATUSES:
        reasons.append(f"status={status}")
    extraction_status = outputs.get("extraction_status")
    if isinstance(extraction_status, str) and extraction_status.startswith("failed"):
        reasons.append(f"extraction_status={extraction_status}")
    return reasons


def _task_productivity(result: Dict[str, Any]) -> float:
    """Per-task productivity weight: 1.0 clean, 0.5 produced-but-partial, 0.0 none.

    #1550 (mirror of CC #1531 item 1): item 1 made the rate count production
       rather than execution — closing a real false positive (``success_rate``
    1.0 on empty tasks). But its discriminant was binary: a task that produced a
    REAL artifact AND honestly flagged a partial degradation (``degraded``) fell
    in the same bucket as a task that produced nothing. The real production was
    erased by the partial-degradation admission — a verdict of void on real
    production, the mirror image of the original defect.

    The discriminant here is the PRESENCE of a substantive artifact (a non-empty
    list in ``outputs``) among self-declared degradation:

    * not degraded → **1.0**. A clean run that honestly finds zero fallacies on
      a clean corpus is a success that found nothing (``test_empty_output_
      without_self_report_still_counts`` pins this — emptiness is not failure).
    * degraded + a non-empty artifact → **0.5**. The task produced real analysis
      AND admitted a partial gap; ``degraded`` is a discount, not a zero.
    * degraded + no artifact (or no outputs) → **0.0**. A self-declared
      non-analysis (item 1's ``status: unavailable`` / empty ``total_fallacies``
      forms) stays closed.

    Justification in one line (DoD #3): ``degraded`` discounts a task that
    produced; only the ABSENCE of production zeroes it. The rejected alternative
    — reading only ``outputs.status in _DEGRADED_OUTPUT_STATUSES`` — does not
    survive the item-1 guard's task shape (a degraded result with no ``outputs``
    field must still read 0.0, which a status-only check would miss).
    """
    if result.get("status") != "completed":
        return 0.0
    if not result.get("degraded"):
        return 1.0
    outputs = result.get("outputs")
    if isinstance(outputs, dict) and any(
        isinstance(v, list) and v for v in outputs.values()
    ):
        return 0.5
    return 0.0


class DelegationError(RuntimeError):
    """Raised when the 3-tier delegation chain cannot proceed honestly.

    M3 fails loud rather than fabricating a degraded result (anti-pendule
    #1019). This covers: an empty strategic objective set, a tactical
    decomposition that yields no tasks, and a missing operational tier.
    """


async def _absent_operational_executor(command: Dict[str, Any]) -> Dict[str, Any]:
    """Default executor when neither an executor nor a registry was provided.

    Fails loud on first invocation — M3 has no operational tier to delegate to,
    and silently returning a stub result would be exactly the heuristic theatre
    #1019 forbids.
    """
    raise DelegationError(
        "No operational_executor and no capability_registry provided — the M3 "
        "delegation chain has no operational tier to delegate to. Refusing a "
        "heuristic no-op fallback (anti-pendule #1019)."
    )


def make_registry_operational_executor(
    capability_registry: Any,
) -> OperationalExecutor:
    """Build the default production operational executor backed by the registry.

    Routes each operational command through the SAME `CapabilityRegistry`
    providers M2 uses, but via the 3-tier control flow rather than a DAG. A
    command whose required capabilities have no provider yields an honest
    ``status="failed"`` result (surfaced upward), NOT a heuristic fallback.

    Args:
        capability_registry: A `CapabilityRegistry` exposing providers.

    Returns:
        An async ``command -> result`` callable.
    """
    op_registry = RegistryBackedOperationalRegistry(capability_registry)

    async def _executor(command: Dict[str, Any]) -> Dict[str, Any]:
        required = command.get("required_capabilities") or []
        # BO-1 #1471 cont. R648: bridge the legacy capability names hardcoded
        # in TaskCoordinator.agent_capabilities (coordinator.py:79-92) to the
        # registry-side capability names. This was the actual cause-racine:
        # delegation-mode's M3 chain produced no_provider_for_required_capabilities
        # for tasks labelled ``text_extraction`` / ``argument_identification`` /
        # etc., even when the registry had providers under different names
        # (``fact_extraction``, ``argument_parsing``, ...). Anti-pendule #1019:
        # map only at the lookup seam, never silently replace an unmatched
        # legacy cap with a fabricated one (the legacy caps still surface in
        # the ``required_capabilities`` field of failed-task results).
        chosen: Optional[str] = next(
            (cap for cap in required if op_registry.has_capability(cap)), None
        )
        if chosen is None:
            for legacy in required:
                mapped = LEGACY_TO_REGISTRY_CAPABILITY.get(legacy)
                if mapped and op_registry.has_capability(mapped):
                    chosen = mapped
                    break
        # Fallback for empty ``required_capabilities`` (generic tasks): read
        # the originating strategic objective's NL description and try the
        # bridge's keyword map. Keeps the fix surgical — we reuse
        # ``_OBJECTIVE_CAPABILITY_MAP`` rather than reinventing it.
        if chosen is None and not required:
            nl = command.get("strategic_objective_description", "").lower()
            if nl:
                # Imported lazily to avoid a hard cycle with the bridge module.
                from argumentation_analysis.orchestration.hierarchical.hierarchy_bridge import (
                    _OBJECTIVE_CAPABILITY_MAP,
                )

                for keyword, caps in _OBJECTIVE_CAPABILITY_MAP.items():
                    if keyword in nl:
                        for c in caps:
                            if op_registry.has_capability(c):
                                chosen = c
                                break
                        if chosen is not None:
                            break
        base = {
            "task_id": command.get("tactical_task_id"),
            "objective_id": command.get("objective_id"),
        }
        if chosen is None:
            # Fail loud per-task: no provider covers the required capabilities.
            return {
                **base,
                "status": "failed",
                "reason": "no_provider_for_required_capabilities",
                "required_capabilities": list(required),
            }
        input_data = {
            "description": command.get("description", ""),
            "text_extracts": command.get("text_extracts", []),
            "parameters": command.get("parameters", {}),
            "strategic_objective_description": command.get(
                "strategic_objective_description", ""
            ),
        }
        # BO-1 #1471 cont. R648: bridge the dict/str signature mismatch. Every
        # ``_invoke_*`` registered in the CapabilityRegistry (see
        # invoke_callables.py) is declared ``async def _invoke_X(input_text: str,
        # context: Dict)``. The bridge mode (``objectives_to_workflow`` →
        # ``WorkflowExecutor``) passes the raw user ``text`` as ``input_text``;
        # the delegation mode previously passed the full ``input_data`` dict
        # here, which raised ``AttributeError: 'dict' object has no attribute
        # 'strip'`` (or similar) the moment any provider tried to handle it as
        # text. Pass the textual payload (``description``) as the position the
        # signatures actually declare, and keep the structured fields in the
        # context so providers that need them can still find them.
        #
        # CC #1531: ce qui est passé en position 1 doit être le CORPUS, pas le
        # libellé de la tâche. ``description`` est une étiquette de ~30
        # caractères ("Extraire les segments...") — les runs de délégation
        # montraient ``source_length: 28`` et un agent répondant honnêtement
        # « aucun texte fourni », pendant que la chaîne concluait au succès.
        # Le corpus arrive par ``text_extracts`` (voir
        # ``TacticalOperationalInterface._determine_relevant_extracts``).
        corpus_text = "\n\n".join(
            str(extract.get("content", "")).strip()
            for extract in input_data["text_extracts"]
            if isinstance(extract, dict) and str(extract.get("content", "")).strip()
        )
        if not corpus_text:
            # Fail loud plutôt qu'analyser un libellé : sans corpus la tâche ne
            # peut rien produire, et un ``completed`` ici remonterait en
            # success_rate=1.0 puis en « performance globale élevée » (#1019).
            return {
                **base,
                "status": "failed",
                "reason": "insufficient_input",
                "capability": chosen,
            }
        textual_input = corpus_text
        bridge_context = {
            **(command.get("context") or {}),
            "input_data": input_data,
        }
        result = await op_registry.invoke_capability(
            chosen, textual_input, bridge_context
        )
        if result is None:
            return {
                **base,
                "status": "failed",
                "reason": "provider_returned_none",
                "capability": chosen,
            }
        task_result = {
            **base,
            "status": "completed",
            "capability": chosen,
            "outputs": result,
        }
        # CC #1531 item 1: surface the provider's own degradation self-report at
        # the top level of the task result, where the aggregation can see it.
        # ``status`` stays ``completed`` on purpose — the call DID return; what
        # did not happen is production, and conflating the two would lose
        # information rather than add it.
        reasons = _degradation_reasons(result)
        if reasons:
            task_result["degraded"] = True
            task_result["degradation_reasons"] = reasons
        return task_result

    return _executor


# Legacy capability names emitted by ``TaskCoordinator._decompose_objective_to_tasks``
# (see coordinator.py:79-92 agent_capabilities table) mapped to the canonical
# CapabilityRegistry names that actually carry a provider. Keyed by legacy name
# (the only one the tactical tier ever emits). Anti-pendule: minimal mapping,
# only the names that the empirical probe (R648) showed were failing — extending
# to unknown legacy caps is NOT a goal here, honesty about the gap is.
LEGACY_TO_REGISTRY_CAPABILITY: Dict[str, str] = {
    "text_extraction": "fact_extraction",
    "argument_identification": "argument_parsing",
    "argument_visualization": "argument_visualization",  # placeholder; no provider yet
    "summary_generation": "synthesis",
    "formal_logic": "propositional_logic",
    "validity_checking": "propositional_logic",
    "consistency_analysis": "propositional_logic",
    "rhetorical_analysis": "argument_quality",
    "preprocessing": "fact_extraction",
}


class DelegationOrchestrator:
    """M3 — explicit strategic→tactical→operational delegation.

    The three tiers are driven by direct sequential calls (no pub/sub):

    1. **S** — ``StrategicManager.initialize_analysis`` → NL objectives.
       Fail loud if empty.
    2. **T** — ``TaskCoordinator.process_strategic_objectives`` decomposes the
       objectives into ``tactical_state.tasks["pending"]``.
    3. **T→O** — for each pending task,
       ``TacticalOperationalInterface.translate_task_to_command`` builds the
       operational command, which is then augmented with the originating
       strategic objective's NL description (decomposition only carries the
       ``objective_id``, so the intent is re-attached here to flow S→T→O), and
       handed to the injectable ``operational_executor``.
    4. **O→T→S** — results are aggregated per objective and passed to
       ``StrategicManager.evaluate_final_results`` for the final verdict.

    The two seams (``strategic_manager`` and ``operational_executor``) are
    injectable so the chain can be unit tested without an LLM or live agents.
    """

    def __init__(
        self,
        strategic_manager: Optional[StrategicManager] = None,
        tactical_coordinator: Optional[TaskCoordinator] = None,
        tactical_operational_interface: Optional[TacticalOperationalInterface] = None,
        operational_executor: Optional[OperationalExecutor] = None,
        capability_registry: Any = None,
        middleware: Any = None,
    ):
        self.logger = logging.getLogger(__name__)
        self.capability_registry = capability_registry
        self.middleware = middleware

        self.strategic_manager = strategic_manager or StrategicManager(
            middleware=middleware
        )
        self.tactical_coordinator = tactical_coordinator or TaskCoordinator(
            middleware=middleware
        )
        # Interface MUST share the coordinator's tactical state so the bottom-up
        # result-processing updates the same task records the coordinator created.
        self.interface = tactical_operational_interface or TacticalOperationalInterface(
            tactical_state=self.tactical_coordinator.state,
            middleware=middleware,
        )

        if operational_executor is not None:
            self.operational_executor = operational_executor
        elif capability_registry is not None:
            self.operational_executor = make_registry_operational_executor(
                capability_registry
            )
        else:
            self.operational_executor = _absent_operational_executor

    async def analyze(
        self,
        text: str,
        checkpoint_callback: Optional[Callable[..., None]] = None,
    ) -> Dict[str, Any]:
        """Run the full S→T→O delegation chain on ``text``.

        Returns a dict with the objectives, task count, per-task operational
        results, and the strategic evaluation/conclusion.

        Args:
            text: The argument text to analyze.
            checkpoint_callback: Optional ``(operational_results, ctx)``
                callable fired after each operational task completes (CB #1528
                item 2). The T→O loop is strictly sequential, so the caller
                sees exactly the tasks that finished. It exists so a
                wall-clock-bounded caller can recover a REAL partial verdict
                after an external ``asyncio.wait_for`` cancels the chain:
                without it, everything the finished tasks produced dies with
                the coroutine. Recording only — never load-bearing for the
                chain itself.

        Raises:
            DelegationError: if the strategic tier yields no objectives or the
                tactical tier decomposes them into zero tasks (fail loud).
        """
        # --- S: strategic tier ---------------------------------------------
        strategic_result = self.strategic_manager.initialize_analysis(text)
        objectives: List[Dict[str, Any]] = strategic_result.get("objectives", []) or []
        if not objectives:
            raise DelegationError(
                "Strategic tier produced zero objectives — refusing to fabricate "
                "a hardcoded objective list (anti-pendule #1019). M3 fails loud "
                "where the M2 bridge would inject 4 default objectives."
            )
        obj_map = {obj["id"]: obj for obj in objectives}
        self.logger.info("M3 strategic tier produced %d objective(s).", len(objectives))

        # --- T: tactical decomposition -------------------------------------
        # CC #1531: propager le corpus S→T. La décomposition ne transporte que
        # les objectifs; sans ce fil le tier tactique n'a AUCUN accès au texte
        # et l'interface T→O fabriquait un extrait factice. C'est le côté
        # écriture de la chaîne écriture→lecture consommée par
        # ``TacticalOperationalInterface._determine_relevant_extracts``.
        self.tactical_coordinator.state.set_raw_text(text)
        decomposition = self.tactical_coordinator.process_strategic_objectives(
            objectives
        )
        pending_tasks = list(self.tactical_coordinator.state.get_pending_tasks())
        if not pending_tasks:
            raise DelegationError(
                f"Tactical tier decomposed {len(objectives)} objective(s) into "
                "zero tasks — the delegation chain is broken; refusing a silent "
                "no-op (anti-pendule #1019)."
            )
        self.logger.info(
            "M3 tactical tier decomposed into %d task(s).", len(pending_tasks)
        )

        # --- #1735 T3: la désignation motivée remonte à la trace ------------
        # ``TaskCoordinator.assign_task_to_operational`` a écrit, pour chaque
        # tâche, qui (``task_assignments``) et pourquoi
        # (``task_assignments_motivation``) dans l'état tactique. On expose la
        # paire ici pour que la trace du run la porte. Le scrub réutilise le
        # mécanisme de ``strategic_bridge`` (dispatch #1735 : « réutilise-la,
        # ne recâble pas ») — la motivation est du texte libre et PEUT contenir
        # un nom de source : elle passe par le même strip par clé nominative
        # que les objectifs stratégiques déjà syncés.
        from argumentation_analysis.core.strategic_bridge import _scrub_dict

        task_assignments = []
        for task in pending_tasks:
            # L'id est garanti : la décomposition tactique le construit toujours
            # (``base_task_id + n``, coordinator._decompose_objective_to_tasks).
            task_id = task["id"]
            task_assignments.append(
                _scrub_dict(
                    {
                        "task_id": task_id,
                        "description": task.get("description", ""),
                        "agent_id": self.tactical_coordinator.state.task_assignments.get(
                            task_id
                        ),
                        "motivation": (
                            self.tactical_coordinator.state.task_assignments_motivation.get(
                                task_id, ""
                            )
                        ),
                    }
                )
            )

        # --- T→O: translate + execute each task ----------------------------
        operational_results: List[Dict[str, Any]] = []
        for task in pending_tasks:
            command = self.interface.translate_task_to_command(task)
            # Thread the strategic NL intent S→T→O. Decomposition carries only
            # the objective_id, so re-attach the originating objective's NL
            # description here — this is the write side of the write→read chain.
            objective = obj_map.get(command.get("objective_id"))
            command["strategic_objective_description"] = (
                objective.get("description", "") if objective else ""
            )
            result = await self.operational_executor(command)
            operational_results.append(result)
            # Bottom-up: feed the result back through the tactical interface so
            # the shared tactical state reflects task completion.
            try:
                self.interface.process_operational_result(command, result)
            except Exception as exc:  # noqa: BLE001 — best-effort bookkeeping
                self.logger.warning(
                    "process_operational_result failed for %s: %s",
                    command.get("id"),
                    exc,
                )

            # CB #1528 item 2: hand the caller what has been produced so far.
            # Guarded like the pipeline's ``_record_completed`` — a recording
            # hook must never be able to break the run it observes.
            if checkpoint_callback is not None:
                try:
                    checkpoint_callback(
                        list(operational_results),
                        {"planned_tasks": len(pending_tasks)},
                    )
                except Exception as cb_err:  # noqa: BLE001
                    self.logger.warning("Checkpoint callback failed: %s", cb_err)

        # --- O→T→S: aggregate + strategic evaluation -----------------------
        eval_input = self._aggregate_results_by_objective(
            objectives, operational_results
        )
        final = self.strategic_manager.evaluate_final_results(eval_input)

        # --- CC #1531 item 1: an honest verdict ----------------------------
        # ``degraded`` means "no operational task produced anything" — not
        # "some task complained". A run where three tasks produced and one
        # provider was unavailable still concludes, with a rate lowered by the
        # aggregation above; punishing it would be the mirror error. But a run
        # where NOTHING was produced has no analysis to report, and saying so
        # is the only honest option: averaging self-declared non-analyses into
        # a 0.5 and calling it "satisfaisante" is how the fabricated verdict
        # was manufactured.
        reasons: List[str] = []
        for result in operational_results:
            label = result.get("capability") or result.get("task_id") or "task"
            if result.get("degraded"):
                reasons.extend(
                    f"{label}: {r}" for r in result.get("degradation_reasons", [])
                )
            elif result.get("status") == "failed":
                reasons.append(f"{label}: {result.get('reason', 'failed')}")
        # #1550: ``produced_anything`` uses the SAME productivity predicate as
        # the per-objective rate above (``_task_productivity``), so a run where
        # every task produced real analysis but each flagged a partial gap is
        # still a verdict, not a degrade. The previous binary form
        # (``completed and not degraded``) was the same mirror defect at the
        # verdict level — coherent predicate, two consumers.
        produced_anything = any(_task_productivity(r) > 0 for r in operational_results)
        degraded = bool(operational_results) and not produced_anything

        conclusion = final.get("conclusion")
        if degraded:
            self.logger.warning(
                "M3 delegation produced no operational output on %d task(s); "
                "emitting a degraded verdict instead of a success (CC #1531).",
                len(operational_results),
            )
            conclusion = (
                "Analyse dégradée : aucune des "
                f"{len(operational_results)} tâche(s) opérationnelle(s) n'a "
                "produit de résultat exploitable. Aucune conclusion sur "
                "l'argumentation n'est émise."
            )

        return {
            "mode": "delegation",
            "objectives": objectives,
            "tasks_created": decomposition.get("tasks_created", len(pending_tasks)),
            # #1735 T3: la désignation motivée (qui + pourquoi), scrubée.
            # Lue par la trace CLI (run_orchestration.py) et par les
            # consommateurs du résultat — pas par le harnais de comparaison
            # (il reste sur terminates/wall-time/decides/scope, #1735 T4).
            "task_assignments": task_assignments,
            "operational_results": operational_results,
            "evaluation": final.get("evaluation"),
            "conclusion": conclusion,
            # Read by scripts/compare_orchestration_modes.py so a degraded run
            # scores ``decides`` False (``—``) without touching the uniform
            # ``_compute_decides`` helper (CA #1529).
            "degraded": degraded,
            "degradation_reasons": reasons,
        }

    @staticmethod
    def _aggregate_results_by_objective(
        objectives: List[Dict[str, Any]],
        operational_results: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, float]]:
        """Compute a per-objective success_rate from the operational results.

        Shapes the input expected by ``StrategicManager.evaluate_final_results``:
        ``{obj_id: {"success_rate": float}}``. The rate is the fraction of an
        objective's tasks that completed (failures count honestly against it).

        CC #1531 item 1: a task that ran but whose provider declared itself
        degraded / unavailable does **not** count toward the rate. Before this,
        ``success_rate`` was an *execution* rate wearing the name of a
        *production* rate, and the strategic tier read it as performance.
        """
        by_obj: Dict[str, List[Dict[str, Any]]] = {obj["id"]: [] for obj in objectives}
        for result in operational_results:
            oid = result.get("objective_id")
            if oid in by_obj:
                by_obj[oid].append(result)

        eval_input: Dict[str, Dict[str, float]] = {}
        for oid, results in by_obj.items():
            if not results:
                success_rate = 0.0
            else:
                productive = sum(_task_productivity(r) for r in results)
                success_rate = productive / len(results)
            eval_input[oid] = {"success_rate": success_rate}
        return eval_input


async def run_delegation_analysis(
    text: str,
    capability_registry: Any = None,
    strategic_manager: Optional[StrategicManager] = None,
    operational_executor: Optional[OperationalExecutor] = None,
    middleware: Any = None,
    checkpoint_callback: Optional[Callable[..., None]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Convenience entry point for M3 delegation analysis.

    Mirrors ``run_hierarchical_analysis`` (M2) so the two modes are symmetric
    selectable axes. Extra ``kwargs`` are accepted and ignored for signature
    compatibility with the M2 convenience function.

    ``checkpoint_callback`` (CB #1528 item 2) is forwarded, not ignored: it is
    the seam a wall-clock-bounded caller uses to recover a real partial
    verdict when the chain is cancelled mid-flight.
    """
    orchestrator = DelegationOrchestrator(
        strategic_manager=strategic_manager,
        operational_executor=operational_executor,
        capability_registry=capability_registry,
        middleware=middleware,
    )
    return await orchestrator.analyze(text, checkpoint_callback=checkpoint_callback)
