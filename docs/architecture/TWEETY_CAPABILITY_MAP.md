# Tweety Capability Map

Maps Tweety library modules to the Lego architecture slots declared in `CapabilityRegistry`.

## Current Tweety Integration

The system uses Tweety 1.28 via JPype. JVM initialization is handled by `core/jvm_setup.py`.

### Active Tweety Usage

| Component | Tweety Module | Usage |
|-----------|--------------|-------|
| `TweetyBridge` (`agents/core/logic/tweety_bridge.py`) | `org.tweetyproject.logics.fol` | FOL parsing, belief sets, reasoners |
| `FOLLogicAgent` | `logics.fol.parser.FolParser` | First-order logic formulas |
| `ModalLogicAgent` | `logics.ml.reasoner` | Modal logic reasoning (S5) |
| `PropositionalLogicAgent` | `logics.pl.parser.PlParser` | Propositional logic |
| Bootstrap (`core/bootstrap.py`) | `arg.aspic` | ASPIC parser + PlFormulaGenerator |
| `abs_arg_dung/` library | `arg.dung` | Dung argumentation frameworks |

### Tweety JARs

Located in `libs/tweety/`:
- `org.tweetyproject.tweety-full-1.28-with-dependencies.jar` — main JAR

## Lego Extension Slots

These slots are declared in `orchestration/unified_pipeline.py` via `_declare_tweety_slots()`. They are **unfilled** — ready for future implementation.

| Slot Name | Description | Tweety Package | Status |
|-----------|-------------|----------------|--------|
| `aspic_plus_reasoning` | ASPIC+ structured argumentation | `org.tweetyproject.arg.aspic` | **Slot declared** — partial use in bootstrap |
| `aba_reasoning` | Assumption-Based Argumentation | `org.tweetyproject.arg.aba` | **Slot declared** — not implemented |
| `adf_reasoning` | Abstract Dialectical Frameworks | `org.tweetyproject.arg.adf` | **Slot declared** — not implemented |
| `bipolar_argumentation` | Bipolar argumentation (support + attack) | `org.tweetyproject.arg.bipolar` | **Slot declared** — not implemented |
| `ranking_semantics` | Qualitative argument ranking | `org.tweetyproject.arg.rankings` | **Slot declared** — not implemented |
| `probabilistic_argumentation` | Probabilistic argument acceptance | `org.tweetyproject.arg.prob` | **Slot declared** — not implemented |
| `dialogue_protocols` | Agent dialogue and negotiation | `org.tweetyproject.agents.dialogues` | **Slot declared** — not implemented |
| `belief_revision` | Belief dynamics and revision | `org.tweetyproject.beliefdynamics` | **Slot declared** — not implemented |

## Filled Capability Slots

These capabilities are registered in `setup_registry()`:

| Capability | Component | Type | Student Project |
|-----------|-----------|------|-----------------|
| `argument_quality` | `ArgumentQualityEvaluator` | Agent | 2.3.5 |
| `adversarial_debate` | `DebateAgent` | Agent | 1.2.7 |
| `governance_simulation` | `GovernanceAgent` | Agent | 2.1.6 |
| `belief_maintenance` | `JTMS` | Service | 1.4.1 |
| `local_llm` | `LocalLLMService` | Service | 2.3.6 |
| `counter_argument_generation` | `CounterArgumentAgent` | Agent | 2.3.3 |
| `neural_fallacy_detection` | `FrenchFallacyAdapter` | Agent (optional) | 2.3.2 |
| `semantic_indexing` | `SemanticIndexService` | Service (optional) | Arg_Semantic_Index |
| `speech_transcription` | `SpeechTranscriptionService` | Service (optional) | speech-to-text |

## How to Fill a Tweety Slot

To implement a Tweety extension slot:

1. Create a service class in `argumentation_analysis/services/` that wraps the Tweety calls via JPype
2. Register it in `setup_registry()` with the slot's capability name
3. Mark it with `requires=["jvm"]` so the registry knows it needs JVM
4. Create tests with `@pytest.mark.jpype` marker
5. The slot will automatically be filled and available in workflow phases

Example:
```python
# In setup_registry():
from argumentation_analysis.services.aspic_service import AspicService

registry.register_service(
    name="aspic_service",
    service_class=AspicService,
    capabilities=["aspic_plus_reasoning"],
    requires=["jvm"],
    metadata={"description": "ASPIC+ structured argumentation via Tweety"},
)
```

## References

- Professor's Tweety notebooks: `D:\CoursIA\MyIA.AI.Notebooks\SymbolicAI\Tweety\`
- Tweety project: https://tweetyproject.org/
- Issue #21: Planned Tweety environment update
- Issues #24-#27, #31: Tweety/FOL improvements (parallel track)
