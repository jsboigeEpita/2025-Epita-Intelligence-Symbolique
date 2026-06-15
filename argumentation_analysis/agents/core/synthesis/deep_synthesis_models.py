"""Data models for the DeepSynthesis multi-page grounded analysis report."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class SourceOverview:
    """Section 1: contextual frame for the analysed source."""

    opaque_id: str = ""
    era: str = ""
    language: str = ""
    discourse_type: str = ""
    length_chars: int = 0
    length_words: int = 0
    contextual_frame: str = ""
    # PP #715: enriched context fields for qualitative synthesis
    speaker: str = ""
    date_or_year: str = ""
    venue: str = ""
    topic: str = ""
    register: str = ""
    synopsis: str = ""


@dataclass
class ArgumentMapEntry:
    """A single argument in the argument map (Section 2)."""

    arg_id: str
    stance: str  # "pro" | "con" | "neutral"
    description: str
    attacks: List[str] = field(default_factory=list)  # arg_ids this one attacks
    attacked_by: List[str] = field(default_factory=list)


@dataclass
class FallacyDiagnosis:
    """Section 3: a single fallacy anchored in taxonomy."""

    fallacy_id: str
    family: str
    taxonomy_path: str
    textual_span: str
    commentary: str
    impacted_args: List[str] = field(default_factory=list)


@dataclass
class FormalFinding:
    """Section 4: a single formal-method finding."""

    logic_type: str  # "PL", "FOL", "Modal", "ASPIC", etc.
    axioms: List[str] = field(default_factory=list)
    queries: List[str] = field(default_factory=list)
    results: List[str] = field(default_factory=list)
    inconsistency_measures: Dict[str, Any] = field(default_factory=dict)
    linked_args: List[str] = field(default_factory=list)


@dataclass
class DungStructure:
    """Section 5: Dung AF analysis."""

    framework_name: str = ""
    arguments: List[str] = field(default_factory=list)
    attacks: List[List[str]] = field(default_factory=list)
    grounded_extension: List[str] = field(default_factory=list)
    preferred_extensions: List[List[str]] = field(default_factory=list)
    stable_extensions: List[List[str]] = field(default_factory=list)
    interpretation: str = ""


@dataclass
class BeliefRetraction:
    """Section 6: a single JTMS belief retraction."""

    belief_name: str
    was_valid: Optional[bool]
    trigger: str  # fallacy or contradiction that caused retraction


@dataclass
class CounterArgumentEntry:
    """Section 7: a scored counter-argument."""

    counter_id: str
    original_arg: str
    counter_content: str
    strategy: str
    score: float
    criteria_scores: Dict[str, float] = field(default_factory=dict)
    targets_weakest: bool = False


@dataclass
class CrossTextParallel:
    """Section 8: a rhetorical parallel between corpora."""

    corpus_x: str
    corpus_y: str
    move_x: str
    move_y: str
    parallel_type: str  # "analogy", "contrast", "escalation", etc.
    commentary: str = ""


@dataclass
class ConvergentVerdict:
    """A cross-method convergence verdict (Track DD #637).

    Surfaces an argument flagged as weak by several *independent* analysis
    methods. The agreement across perspectives is the spectacular insight a
    0-shot LLM cannot reproduce.
    """

    arg_id: str
    score: int  # number of independent methods concurring
    methods: List[str] = field(default_factory=list)
    statement: str = ""  # human-readable named verdict


@dataclass
class DeepSynthesisReport:
    """Complete multi-page deep synthesis report with 9 sections."""

    source_overview: SourceOverview = field(default_factory=SourceOverview)
    argument_map: List[ArgumentMapEntry] = field(default_factory=list)
    fallacy_diagnoses: List[FallacyDiagnosis] = field(default_factory=list)
    formal_findings: List[FormalFinding] = field(default_factory=list)
    dung_structure: DungStructure = field(default_factory=DungStructure)
    belief_retractions: List[BeliefRetraction] = field(default_factory=list)
    counter_arguments: List[CounterArgumentEntry] = field(default_factory=list)
    cross_text_parallels: List[CrossTextParallel] = field(default_factory=list)
    final_synthesis: str = ""
    # FB-31 #1108 — Section 9 status (fail-loud, mirrors grounded_synthesis_status):
    # "llm" (LLM-conducted synthesis), "unavailable" (no LLM / empty result),
    # "failed" (LLM raised). When the status is not "llm", final_synthesis is
    # empty — there is NO count-template fallback dressed up as synthesis (the
    # determinization residue #1019/#1109 says to remove, not institutionalize).
    final_synthesis_status: str = ""
    convergent_verdicts: List[ConvergentVerdict] = field(default_factory=list)
    convergence_conclusion: str = ""
    # LLM-polished prose for the convergence section (Track GG #644).
    # Empty when no kernel is configured or no verdicts exist; renderer then
    # falls back to the template verdict statements.
    convergence_prose: str = ""
    # Adjudication table (Track NN #659) — grounded vs claimed fallacy families.
    # Each entry: {"family": str, "status": "grounded"|"claimed", "evidence": str}
    adjudication_table: List[Dict[str, str]] = field(default_factory=list)
    # FB-18 Mode A (#1039) — grounded transversal synthesis: 4-section LLM
    # synthesis where every insight carries [artifact:...] citations anchored
    # in the verified state artifacts. Empty when no LLM is available; the
    # status field then says so explicitly (fail-loud, no template imposture).
    grounded_synthesis: str = ""
    grounded_synthesis_status: str = ""  # "llm" | "unavailable" | "failed"
    # FB-18 value-gates VG-1..VG-4 verdicts, computed on grounded_synthesis.
    value_gates: Dict[str, Any] = field(default_factory=dict)
    populated_artifact_fields: int = 0
    # Metadata
    report_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    total_state_fields: int = 0
    sections_populated: int = 0
    report_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_overview": self.source_overview.__dict__,
            "argument_map": [a.__dict__ for a in self.argument_map],
            "fallacy_diagnoses": [f.__dict__ for f in self.fallacy_diagnoses],
            "formal_findings": [f.__dict__ for f in self.formal_findings],
            "dung_structure": self.dung_structure.__dict__,
            "belief_retractions": [b.__dict__ for b in self.belief_retractions],
            "counter_arguments": [c.__dict__ for c in self.counter_arguments],
            "cross_text_parallels": [p.__dict__ for p in self.cross_text_parallels],
            "final_synthesis": self.final_synthesis,
            "final_synthesis_status": self.final_synthesis_status,
            "convergent_verdicts": [v.__dict__ for v in self.convergent_verdicts],
            "convergence_conclusion": self.convergence_conclusion,
            "convergence_prose": self.convergence_prose,
            "adjudication_table": self.adjudication_table,
            "grounded_synthesis": self.grounded_synthesis,
            "grounded_synthesis_status": self.grounded_synthesis_status,
            "value_gates": self.value_gates,
            "populated_artifact_fields": self.populated_artifact_fields,
            "report_timestamp": self.report_timestamp,
            "total_state_fields": self.total_state_fields,
            "sections_populated": self.sections_populated,
            "report_version": self.report_version,
        }
