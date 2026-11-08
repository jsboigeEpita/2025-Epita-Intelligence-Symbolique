"""#3493 — a leaf named by a slogan never reaches a writer as the document's words.

Cycle 4b's judge kept one M2: the Act II render attributed to the document an
appeal it does not contain, because the writer had received a taxonomy leaf's
NAME (``text_fr`` embedding an example in guillemets) and wrote it as the
speaker's own appeal.

The rule is subtraction at the writers' entry, one function
(``generic_fallacy_name``): a leaf whose name carries an example in guillemets
reaches the writer as the leaf's generic line (``desc_fr``); every other name
is returned byte for byte. The detector, the state and the export keep the
taxonomy's real name, and the vendored CSV is not edited.

The taxonomy file is the repo's own vendored data, not the analysed corpus:
no document text, no source name appears here.
"""

from __future__ import annotations

import csv
import io
from types import SimpleNamespace

from argumentation_analysis.utils.taxonomy_loader import (
    get_taxonomy_path,
    generic_fallacy_name,
    fallacy_taxonomy_label,
)

#: The M2 leaf: its ``text_fr`` embeds an example slogan, and its ``desc_fr``
#: is the generic procedure. Measured on the vendored file (row PK 306).
SLOGAN_LEAF = "Appel à « la France qui se lève tôt »"
SLOGAN_PATH = "2.2.1.2.2.1"
SLOGAN_FAMILY = "Influence"
SLOGAN_INNER = "la France qui se lève tôt"
SLOGAN_GENERIC = (
    "Vous utilisez la valeur du travail pour légitimer une idée, en "
    "ciblant une classe sociale précise."
)


def _quoted_leaves():
    """Every taxonomy row whose ``text_fr`` carries an example in guillemets."""
    rows = []
    with io.open(str(get_taxonomy_path()), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name = row.get("text_fr") or ""
            if "«" in name:
                rows.append(row)
    return rows


# --- the M2 leaf: the writer's input no longer carries the slogan ----------


def test_the_slogan_leaf_reaches_the_writer_as_the_generic_line():
    writer_name = generic_fallacy_name(SLOGAN_LEAF, SLOGAN_PATH)
    assert writer_name == SLOGAN_GENERIC
    assert SLOGAN_INNER not in writer_name
    assert "«" not in writer_name


def test_the_shared_label_prints_the_generic_line_and_keeps_the_branch():
    """The three evidence sites read `fallacy_taxonomy_label` — M2's entry."""
    label = fallacy_taxonomy_label(SLOGAN_LEAF, SLOGAN_FAMILY, SLOGAN_PATH, quoted=True)
    assert SLOGAN_INNER not in label
    assert "«" not in label  # a substituted definition is not a quoted name
    assert SLOGAN_GENERIC in label
    # The branch still names the category: the reader keeps the taxonomy's map.
    assert "Influence" in label
    assert "Appel à l’émotion" in label


def test_a_slogan_leaf_without_a_path_still_loses_its_example():
    """No stored path: the inner slogan goes, the rest of the wording stays."""
    label = generic_fallacy_name("Effet « pas d’ici »", None)
    assert "pas d’ici" not in label
    assert label  # a frame remains — the detection is never dropped


def test_the_family_still_resolves_from_the_recorded_name():
    """`_fallacy_family` must keep reading the RECORDED name, not the line.

    Measured: the keyword classifier maps this leaf's recorded name to
    ``relevance``; the generic line would map differently. The property that
    matters is that the family does not move when the printed name does.
    """
    from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
        DeepSynthesisAgent,
    )

    recorded_family = DeepSynthesisAgent._fallacy_family(SLOGAN_LEAF)
    state = SimpleNamespace(
        identified_fallacies={
            "fallacy_1": {"type": SLOGAN_LEAF, "justification": "synthetic"}
        },
        neural_fallacy_scores=[],
    )
    diagnoses = DeepSynthesisAgent._build_fallacy_diagnoses(state)
    assert diagnoses[0].family == recorded_family
    # And the printed path carries the generic line, not the slogan.
    assert SLOGAN_INNER not in diagnoses[0].taxonomy_path


# --- byte-identity for every other leaf -----------------------------------


def test_a_leaf_without_guillemets_is_byte_identical():
    # Measured on the vendored file before the fix; the value must not move.
    assert (
        fallacy_taxonomy_label("Pente glissante", "Tricherie", "6.1.2.1", quoted=True)
        == "« Pente glissante » (Tricherie > Présentation trompeuse des faits)"
    )
    assert (
        fallacy_taxonomy_label("Sophisme métonymique", "Influence", None)
        == "Sophisme métonymique (famille Influence)"
    )
    assert generic_fallacy_name("Pente glissante", "6.1.2.1") == "Pente glissante"


# --- the rule, not a hand list --------------------------------------------


def test_every_quoted_leaf_in_the_taxonomy_is_covered_by_the_same_rule():
    rows = _quoted_leaves()
    # Census at 1 408 rows (the issue's figure). A taxonomy update that adds
    # a fifth leaf is covered by the rule itself, which is why this is a floor.
    assert len(rows) >= 4
    for row in rows:
        name = row.get("text_fr") or ""
        path = row.get("path") or ""
        writer_name = generic_fallacy_name(name, path)
        assert "«" not in writer_name, name
        assert "»" not in writer_name, name
        # The definition resolves for every one of them on the vendored file.
        assert writer_name == (row.get("desc_fr") or "").strip(), name
    # The four the issue names are in there, found without being listed.
    assert SLOGAN_PATH in {row.get("path") for row in rows}


# --- the writers' own inputs ----------------------------------------------


def test_the_act2_prompt_carries_the_generic_line_never_the_slogan():
    from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
        build_act2_evidence,
        build_act2_prompt,
    )

    state = SimpleNamespace(
        identified_arguments={"arg_1": "Un appui synthétique."},
        identified_fallacies={
            "fallacy_1": {
                "type": SLOGAN_LEAF,
                "family": SLOGAN_FAMILY,
                "taxonomy_path": SLOGAN_PATH,
                "target_argument_id": "arg_1",
                "justification": "Le passage invoque la valeur du travail.",
                "confidence": 0.5,
            }
        },
        argument_quality_scores={},
        counter_arguments=[],
    )
    prompt = build_act2_prompt(build_act2_evidence(state))
    assert SLOGAN_INNER not in prompt
    assert SLOGAN_GENERIC in prompt


def test_the_synthesis_writer_receives_the_generic_name():
    from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
        writer_fallacy_type,
    )

    assert (
        writer_fallacy_type({"type": SLOGAN_LEAF, "taxonomy_path": SLOGAN_PATH})
        == SLOGAN_GENERIC
    )
    # Byte-identical for a record that carries no quoted name.
    assert (
        writer_fallacy_type({"type": "Pente glissante", "taxonomy_path": "6.1.2.1"})
        == "Pente glissante"
    )


def test_the_fallacy_diagnoses_path_carries_no_slogan():
    from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
        DeepSynthesisAgent,
    )

    state = SimpleNamespace(
        identified_fallacies={
            "fallacy_1": {
                "type": SLOGAN_LEAF,
                "taxonomy_path": SLOGAN_PATH,
                "justification": "synthetic",
            },
            # No stored path: the synthesised one must stay clean too.
            "fallacy_2": {
                "type": SLOGAN_LEAF,
                "justification": "synthetic",
            },
        },
        neural_fallacy_scores=[
            {"id": "n_1", "label": "Effet « pas d’ici »", "confidence": 0.7}
        ],
    )
    diagnoses = DeepSynthesisAgent._build_fallacy_diagnoses(state)
    for diagnosis in diagnoses:
        assert SLOGAN_INNER not in diagnosis.taxonomy_path
        assert "pas d’ici" not in diagnosis.taxonomy_path
        assert "«" not in diagnosis.taxonomy_path
