# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.agents.core.counter_argument.parser
Covers ArgumentParser, VulnerabilityAnalyzer (parse_llm_response / parse_structured_text
withdrawn #2137 — zero callers).
"""

import pytest

from argumentation_analysis.agents.core.counter_argument.parser import (
    NO_MARKER,
    PREMISE_MARKER_ALONE,
    ArgumentParser,
    VulnerabilityAnalyzer,
)
from argumentation_analysis.agents.core.counter_argument.definitions import (
    Argument,
    Vulnerability,
    CounterArgumentType,
)


@pytest.fixture
def parser():
    return ArgumentParser()


@pytest.fixture
def analyzer():
    return VulnerabilityAnalyzer()


# ============================================================
# ArgumentParser — initialization
# ============================================================


class TestParserInit:
    def test_creates_instance(self, parser):
        assert isinstance(parser, ArgumentParser)

    def test_has_premise_markers(self, parser):
        assert isinstance(parser.premise_markers, list)
        assert "car" in parser.premise_markers
        assert "parce que" in parser.premise_markers

    def test_has_conclusion_markers(self, parser):
        assert isinstance(parser.conclusion_markers, list)
        assert "donc" in parser.conclusion_markers
        assert "par conséquent" in parser.conclusion_markers

    def test_has_argument_types(self, parser):
        assert "deductive" in parser.argument_types
        assert "inductive" in parser.argument_types
        assert "abductive" in parser.argument_types

    def test_has_vulnerability_analyzer(self, parser):
        assert isinstance(parser.vulnerability_analyzer, VulnerabilityAnalyzer)


# ============================================================
# ArgumentParser — parse_argument
# ============================================================


class TestParseArgument:
    def test_returns_argument(self, parser):
        result = parser.parse_argument("Il pleut, donc le sol est mouillé.")
        assert isinstance(result, Argument)

    def test_stores_original_text(self, parser):
        text = "Il pleut, donc le sol est mouillé."
        result = parser.parse_argument(text)
        assert result.content == text

    def test_has_premises(self, parser):
        result = parser.parse_argument("Il pleut car il y a des nuages.")
        assert len(result.premises) >= 1

    def test_has_conclusion(self, parser):
        result = parser.parse_argument("Il pleut, donc le sol est mouillé.")
        assert result.conclusion != ""

    def test_has_argument_type(self, parser):
        result = parser.parse_argument("Tous les chats sont mortels.")
        assert result.argument_type in ("deductive", "inductive", "abductive")

    def test_has_confidence(self, parser):
        result = parser.parse_argument("Il pleut.")
        assert 0.0 <= result.confidence <= 1.0

    def test_premise_marker_car(self, parser):
        result = parser.parse_argument("Le sol est mouillé car il pleut.")
        # "car" is a premise marker — text after "car" is a premise
        assert any("pleut" in p.lower() for p in result.premises)

    def test_conclusion_marker_donc(self, parser):
        result = parser.parse_argument("Il pleut. Donc le sol est mouillé.")
        assert "mouillé" in result.conclusion.lower()


# ============================================================
# ArgumentParser — a premise marker alone (#2600)
# ============================================================


class TestPremiseMarkerOnlyText:
    """#2600 — « X car Y » : le marqueur sépare, il n'est pas le texte.

    Sans marqueur de conclusion, la phrase entière servait à la fois de
    prémisse et de conclusion : la forme d'un argument circulaire, pour un
    texte qui n'en contient aucun. Le marqueur introduit la prémisse — ce qui
    suit est la prémisse, ce qui précède est la conclusion — et le marqueur
    lui-même n'apparaît ni dans l'une ni dans l'autre.
    """

    def test_car_split(self, parser):
        result = parser.parse_argument("Il faut partir car il pleut.")

        assert result.conclusion == "Il faut partir", result.conclusion
        assert result.premises == ["il pleut"], result.premises

    def test_parce_que_split(self, parser):
        result = parser.parse_argument("Le sol est mouillé parce que la pluie tombe.")

        assert result.conclusion == "Le sol est mouillé", result.conclusion
        assert result.premises == ["la pluie tombe"], result.premises

    def test_puisque_split(self, parser):
        result = parser.parse_argument("Il rentre puisque la nuit tombe.")

        assert result.conclusion == "Il rentre", result.conclusion
        assert result.premises == ["la nuit tombe"], result.premises

    def test_the_marker_is_in_neither_part(self, parser):
        result = parser.parse_argument("Il faut partir car il pleut.")

        assert "car" not in result.conclusion.lower(), result.conclusion
        assert all("car" not in p.lower() for p in result.premises), result.premises

    def test_premise_is_not_the_conclusion(self, parser):
        result = parser.parse_argument("Il faut partir car il pleut.")

        assert result.conclusion not in result.premises, result

    def test_parse_prose_splits_too(self, parser):
        argument = parser.parse_prose("Il faut partir car il pleut.")

        assert argument is not None
        assert argument.premises == ["il pleut"], argument.premises
        assert argument.conclusion == "Il faut partir", argument.conclusion


# ============================================================
# ArgumentParser — a premise marker OPENING its sentence (#2600 review)
# ============================================================


class TestPremiseMarkerOpeningTheSentence:
    """#2600 review — « Puisque X, Y » : main reconstruisait juste.

    Un marqueur de prémisse en TÊTE de phrase est la construction causale la
    plus courante en français. La coupe au marqueur ne peut pas s'y appliquer :
    il n'y a rien avant lui, et prendre tout ce qui suit met la conclusion
    DANS la prémisse — la forme circulaire que #2600 retire. Ces formes
    retombent sur le comportement de main (partage par la virgule : la clause
    portant le marqueur est la prémisse, la clause suivante la conclusion).
    """

    def test_puisque_keeps_the_clause_split(self, parser):
        argument = parser.parse_prose("Puisque il pleut, il faut partir.")

        assert argument.premises == ["Puisque il pleut"], argument.premises
        assert argument.conclusion == "il faut partir", argument.conclusion

    def test_comme_keeps_the_clause_split(self, parser):
        argument = parser.parse_prose("Comme il pleut, il faut partir.")

        assert argument.premises == ["Comme il pleut"], argument.premises
        assert argument.conclusion == "il faut partir", argument.conclusion

    def test_etant_donne_que_keeps_the_clause_split(self, parser):
        argument = parser.parse_prose("Étant donné que les prix montent, il faut agir.")

        assert argument.premises == [
            "Étant donné que les prix montent"
        ], argument.premises
        assert argument.conclusion == "il faut agir", argument.conclusion

    def test_premise_is_not_the_conclusion(self, parser):
        argument = parser.parse_prose("Puisque il pleut, il faut partir.")

        assert argument.conclusion not in argument.premises, argument

    def test_mid_sentence_split_still_applies(self, parser):
        # The control: the issue's own case keeps its repair.
        argument = parser.parse_prose("Il faut partir car il pleut.")

        assert argument.premises == ["il pleut"], argument.premises
        assert argument.conclusion == "Il faut partir", argument.conclusion


# ============================================================
# ArgumentParser — a premise marker opening ANOTHER sentence (#2671)
# ============================================================


class TestPremiseMarkerOpeningAnotherSentence:
    """#2671 — « Il faut partir. Car il pleut. » : l'argument sortait inversé.

    Le marqueur ouvre SA phrase et d'autres phrases existent. La coupe dans la
    phrase n'avait rien avant le marqueur ; le texte retombait sur les replis
    par phrase, et la réparation « prémisse identique » échangeait les rôles :
    la phrase du marqueur devenait la conclusion. Ce qui suit le marqueur est
    la prémisse ; l'affirmation qu'elle soutient est la phrase qui précède (ou
    qui suit, quand le marqueur ouvre le texte) ; le marqueur n'est dans
    aucune des deux.
    """

    @pytest.mark.parametrize(
        "text",
        [
            "Il faut partir. Car il pleut.",
            "Il faut partir. Parce que il pleut.",
            "Il faut partir. Puisque il pleut.",
            "Il faut partir! Car il pleut.",
        ],
    )
    def test_the_marker_sentence_is_the_premise(self, parser, text):
        argument = parser.parse_prose(text)

        assert argument.premises == ["il pleut"], argument.premises
        assert argument.conclusion == "Il faut partir", argument.conclusion

    def test_the_marker_is_in_neither_part(self, parser):
        argument = parser.parse_prose("Il faut partir. Car il pleut.")

        assert "car" not in argument.conclusion.lower(), argument.conclusion
        assert all("car" not in p.lower() for p in argument.premises), argument

    def test_the_claim_is_the_nearest_sentence_before(self, parser):
        argument = parser.parse_prose(
            "Il faut partir. Nous devons nous dépêcher. Car il pleut."
        )

        assert argument.premises == ["il pleut"], argument.premises
        assert argument.conclusion == "Nous devons nous dépêcher", argument

    def test_the_sentence_before_wins_over_the_sentence_after(self, parser):
        argument = parser.parse_prose(
            "Il faut partir. Car il pleut. La route est glissante."
        )

        assert argument.premises == ["il pleut"], argument.premises
        assert argument.conclusion == "Il faut partir", argument.conclusion

    def test_a_marker_opening_the_text_supports_the_next_sentence(self, parser):
        argument = parser.parse_prose("Car il pleut. Il faut partir.")

        assert argument.premises == ["il pleut"], argument.premises
        assert argument.conclusion == "Il faut partir", argument.conclusion

    def test_a_preposed_clause_keeps_its_own_reading(self, parser):
        # « Puisque X, Y » dans une phrase qui n'est pas seule : la lecture
        # locale (la forme épinglée par la review de #2600) l'emporte.
        argument = parser.parse_prose(
            "Il faut partir. Puisque il pleut, la route est glissante."
        )

        assert argument.premises == ["Puisque il pleut"], argument.premises
        assert argument.conclusion == "la route est glissante", argument

    def test_a_preposed_clause_opening_the_text_keeps_its_reading(self, parser):
        argument = parser.parse_prose(
            "Comme il pleut, il faut partir. Nous prendrons le bus."
        )

        assert argument.premises == ["Comme il pleut"], argument.premises
        assert argument.conclusion == "il faut partir", argument.conclusion

    def test_car_does_not_open_a_preposed_clause(self, parser):
        # « car » coordonne : « Car X, et Y » est UNE prémisse, pas une
        # prémisse suivie de sa conclusion.
        argument = parser.parse_prose(
            "Il faut partir. Car il pleut, et la route est glissante."
        )

        assert argument.premises == [
            "il pleut, et la route est glissante"
        ], argument.premises
        assert argument.conclusion == "Il faut partir", argument.conclusion


class TestPremiseMarkerStandingAlone:
    """#2678 — une phrase seule dont le marqueur de prémisse laisse un côté
    vide revenait comme un argument circulaire présenté en succès
    (« Car il pleut. » : prémisse « Prémisse implicite: Car il pleut »,
    conclusion « Car il pleut »). ``parse_prose`` la refuse et dit pourquoi."""

    @pytest.mark.parametrize(
        "text",
        [
            "Car il pleut.",
            "Puisque il pleut.",
            "Parce que il pleut.",
            "Il faut partir car.",
            "Car.",
        ],
    )
    def test_a_marker_leaving_a_side_empty_is_refused(self, parser, text):
        assert parser.parse_prose(text) is None
        assert parser.unparseable_reason(text) == PREMISE_MARKER_ALONE

    def test_no_marker_keeps_its_own_reason(self, parser):
        text = "Il fait beau aujourd'hui."

        assert parser.parse_prose(text) is None
        assert parser.unparseable_reason(text) == NO_MARKER

    def test_a_parsed_text_has_no_reason(self, parser):
        assert parser.unparseable_reason("Il faut partir car il pleut.") is None

    def test_control_a_circular_text_is_read_not_refused(self, parser):
        # Les deux côtés existent et disent la même chose : c'est le texte
        # qui est circulaire, et l'analyse doit le voir.
        argument = parser.parse_prose("Il pleut car il pleut.")

        assert argument is not None
        assert argument.premises == ["il pleut"], argument.premises
        assert argument.conclusion == "Il pleut", argument.conclusion

    def test_control_a_clause_after_the_marker_is_read(self, parser):
        argument = parser.parse_prose("Car il pleut, il faut partir.")

        assert argument is not None
        assert argument.conclusion == "il faut partir", argument.conclusion

    def test_control_another_sentence_is_not_a_lone_marker(self, parser):
        # Le refus dit « une seule phrase » : un texte de deux phrases n'y
        # entre pas, quelle que soit sa lecture (#2671 et au-delà).
        for text in ("Il faut partir. Car il pleut.", "Il faut partir car. Il pleut."):
            assert parser.unparseable_reason(text) is None, text

    def test_parse_argument_still_returns_for_the_agent(self, parser):
        # Le contrat « rend toujours » de parse_argument (appels de l'agent)
        # reste : la prémisse fabriquée y est étiquetée « implicite ».
        argument = parser.parse_argument("Car il pleut.")

        assert argument.premises == ["Prémisse implicite: Car il pleut"]


# ============================================================
# ArgumentParser — _extract_premises
# ============================================================


class TestExtractPremises:
    def test_with_premise_marker(self, parser):
        premises = parser._extract_premises("X car Y.")
        assert len(premises) >= 1

    def test_with_conclusion_marker(self, parser):
        premises = parser._extract_premises("A. Donc B.")
        assert len(premises) >= 1

    def test_no_markers_multi_sentence(self, parser):
        premises = parser._extract_premises("Première phrase. Deuxième phrase.")
        assert len(premises) >= 1

    def test_no_markers_single_sentence(self, parser):
        premises = parser._extract_premises("Une seule phrase")
        assert len(premises) == 1
        assert "Une seule phrase" in premises[0]

    def test_parce_que_marker(self, parser):
        premises = parser._extract_premises("Le sol est mouillé parce que il a plu")
        assert len(premises) >= 1

    def test_etant_donne_marker(self, parser):
        premises = parser._extract_premises(
            "Étant donné que les preuves existent, on peut conclure."
        )
        assert len(premises) >= 1


# ============================================================
# ArgumentParser — _extract_conclusion
# ============================================================


class TestExtractConclusion:
    def test_with_conclusion_marker(self, parser):
        conclusion = parser._extract_conclusion("Il pleut. Donc le sol est mouillé.")
        assert "mouillé" in conclusion.lower() or "donc" in conclusion.lower()

    def test_with_premise_marker_conclusion_before(self, parser):
        conclusion = parser._extract_conclusion("Le sol est mouillé car il pleut.")
        # conclusion is before "car"
        assert "mouillé" in conclusion.lower()

    def test_no_marker_returns_last_sentence(self, parser):
        conclusion = parser._extract_conclusion("Première. Deuxième. Troisième.")
        assert "Troisième" in conclusion

    def test_empty_text(self, parser):
        conclusion = parser._extract_conclusion("")
        assert conclusion == ""

    def test_single_sentence(self, parser):
        conclusion = parser._extract_conclusion("Une seule phrase")
        assert "Une seule phrase" in conclusion

    def test_par_consequent(self, parser):
        conclusion = parser._extract_conclusion("Il fait beau. Par conséquent on sort.")
        assert "conséquent" in conclusion.lower() or "sort" in conclusion.lower()


# ============================================================
# ArgumentParser — _determine_argument_type
# ============================================================


class TestDetermineArgumentType:
    def test_deductive_tous(self, parser):
        assert (
            parser._determine_argument_type("Tous les hommes sont mortels")
            == "deductive"
        )

    def test_deductive_chaque(self, parser):
        assert (
            parser._determine_argument_type("Chaque élève doit réussir") == "deductive"
        )

    def test_deductive_toujours(self, parser):
        assert parser._determine_argument_type("Il est toujours vrai") == "deductive"

    def test_deductive_necessairement(self, parser):
        assert (
            parser._determine_argument_type("Cela est nécessairement vrai")
            == "deductive"
        )

    def test_inductive_generalement(self, parser):
        assert (
            parser._determine_argument_type("Généralement les gens préfèrent")
            == "inductive"
        )

    def test_inductive_souvent(self, parser):
        assert parser._determine_argument_type("C'est souvent le cas") == "inductive"

    def test_inductive_la_plupart(self, parser):
        assert (
            parser._determine_argument_type("La plupart des gens sont d'accord")
            == "inductive"
        )

    def test_abductive_meilleure_explication(self, parser):
        assert (
            parser._determine_argument_type("La meilleure explication est")
            == "abductive"
        )

    def test_abductive_probablement(self, parser):
        assert parser._determine_argument_type("C'est probablement vrai") == "abductive"

    def test_abductive_cause(self, parser):
        assert (
            parser._determine_argument_type("La cause de cet événement") == "abductive"
        )

    def test_abductive_explique(self, parser):
        assert parser._determine_argument_type("Cela explique pourquoi") == "abductive"

    def test_deductive_si_alors(self, parser):
        assert parser._determine_argument_type("Si A est vrai alors B") == "deductive"

    def test_default_is_inductive(self, parser):
        # No markers at all
        assert parser._determine_argument_type("Le ciel est bleu") == "inductive"

    def test_inductive_statistiques(self, parser):
        assert (
            parser._determine_argument_type("Les statistiques montrent que")
            == "inductive"
        )

    def test_inductive_exemple(self, parser):
        assert parser._determine_argument_type("Par exemple ceci prouve") == "inductive"


# ============================================================
# ArgumentParser — _calculate_confidence
# ============================================================


class TestCalculateConfidence:
    def test_base_confidence(self, parser):
        # No premises, no conclusion
        confidence = parser._calculate_confidence([], "")
        assert confidence == 0.5

    def test_premises_add_confidence(self, parser):
        confidence = parser._calculate_confidence(["une prémisse"], "")
        assert confidence >= 0.7  # 0.5 + 0.2

    def test_conclusion_adds_confidence(self, parser):
        confidence = parser._calculate_confidence([], "une conclusion")
        assert confidence >= 0.7  # 0.5 + 0.2

    def test_both_add_confidence(self, parser):
        confidence = parser._calculate_confidence(["prémisse"], "conclusion")
        assert confidence >= 0.89  # 0.5 + 0.2 + 0.2 (float precision)

    def test_premise_marker_bonus(self, parser):
        confidence = parser._calculate_confidence(["car il pleut"], "conclusion")
        assert confidence >= 0.99  # 0.5 + 0.2 + 0.2 + 0.1 (float precision)

    def test_conclusion_marker_bonus(self, parser):
        confidence = parser._calculate_confidence(["prémisse"], "donc il fait beau")
        assert confidence >= 0.99  # 0.5 + 0.2 + 0.2 + 0.1 (float precision)

    def test_max_is_one(self, parser):
        confidence = parser._calculate_confidence(["car il pleut"], "donc il fait beau")
        assert confidence == 1.0


# ============================================================
# ArgumentParser — _split_into_sentences
# ============================================================


class TestSplitIntoSentences:
    def test_period_split(self, parser):
        sentences = parser._split_into_sentences("A. B. C.")
        assert len(sentences) == 3

    def test_exclamation_split(self, parser):
        sentences = parser._split_into_sentences("A! B!")
        assert len(sentences) == 2

    def test_question_split(self, parser):
        sentences = parser._split_into_sentences("A? B?")
        assert len(sentences) == 2

    def test_empty_parts_removed(self, parser):
        sentences = parser._split_into_sentences("A... B.")
        assert all(s.strip() for s in sentences)

    def test_single_sentence(self, parser):
        sentences = parser._split_into_sentences("Une phrase sans ponctuation finale")
        assert len(sentences) == 1


# ============================================================
# ArgumentParser — _fix_identical_premise_conclusion
# ============================================================


class TestFixIdenticalPremiseConclusion:
    def test_no_fix_needed_different(self, parser):
        premises, conclusion = parser._fix_identical_premise_conclusion(
            ["A"], "B", "A. B."
        )
        assert premises == ["A"]
        assert conclusion == "B"

    def test_no_fix_empty_premises(self, parser):
        premises, conclusion = parser._fix_identical_premise_conclusion([], "B", "B")
        assert premises == []
        assert conclusion == "B"

    def test_no_fix_empty_conclusion(self, parser):
        premises, conclusion = parser._fix_identical_premise_conclusion(["A"], "", "A")
        assert premises == ["A"]
        assert conclusion == ""

    def test_fixes_with_premise_marker(self, parser):
        # Single sentence (no period) with "car" marker — comma fallback applies
        text = "Le sol est mouillé, car il pleut"
        premises, conclusion = parser._fix_identical_premise_conclusion(
            ["Le sol est mouillé, car il pleut"],
            "Le sol est mouillé, car il pleut",
            text,
        )
        # Should split by comma since it's one sentence
        assert len(premises) >= 1

    def test_comma_fallback(self, parser):
        text = "Première partie, deuxième partie"
        premises, conclusion = parser._fix_identical_premise_conclusion(
            ["Première partie, deuxième partie"],
            "Première partie, deuxième partie",
            text,
        )
        # Should split by comma
        assert len(premises) >= 1
        assert conclusion != ""


# ============================================================
# ArgumentParser — identify_vulnerabilities
# ============================================================


class TestIdentifyVulnerabilities:
    def test_returns_list(self, parser):
        arg = Argument(
            content="Tous les chats sont noirs",
            premises=["Tous les chats sont noirs"],
            conclusion="Les chats sont noirs",
            argument_type="deductive",
            confidence=0.8,
        )
        result = parser.identify_vulnerabilities(arg)
        assert isinstance(result, list)

    def test_sorted_by_score_descending(self, parser):
        arg = Argument(
            content="Tous les chats sont évidemment noirs car c'est naturellement vrai",
            premises=["Tous les chats sont évidemment noirs"],
            conclusion="C'est naturellement vrai",
            argument_type="deductive",
            confidence=0.8,
        )
        vulns = parser.identify_vulnerabilities(arg)
        for i in range(len(vulns) - 1):
            assert vulns[i].score >= vulns[i + 1].score


# ============================================================
# VulnerabilityAnalyzer — initialization
# ============================================================


class TestVulnerabilityAnalyzerInit:
    def test_creates_instance(self, analyzer):
        assert isinstance(analyzer, VulnerabilityAnalyzer)

    def test_has_patterns(self, analyzer):
        assert isinstance(analyzer.vulnerability_patterns, dict)
        assert "generalisation_abusive" in analyzer.vulnerability_patterns
        assert "hypothese_non_fondee" in analyzer.vulnerability_patterns
        assert "fausse_dichotomie" in analyzer.vulnerability_patterns
        assert "pente_glissante" in analyzer.vulnerability_patterns
        assert "causalite_douteuse" in analyzer.vulnerability_patterns

    def test_patterns_have_counter_types(self, analyzer):
        for name, info in analyzer.vulnerability_patterns.items():
            assert "counter_type" in info
            assert isinstance(info["counter_type"], CounterArgumentType)


# ============================================================
# VulnerabilityAnalyzer — _analyze_text
# ============================================================


class TestAnalyzeText:
    def test_generalisation_tous(self, analyzer):
        vuln = analyzer._analyze_text("Tous les experts sont d'accord")
        assert vuln is not None
        assert vuln.type == "generalisation_abusive"

    def test_generalisation_toujours(self, analyzer):
        vuln = analyzer._analyze_text("C'est toujours le cas")
        assert vuln is not None
        assert vuln.type == "generalisation_abusive"

    def test_hypothese_evidemment(self, analyzer):
        vuln = analyzer._analyze_text("C'est évidemment vrai")
        assert vuln is not None
        assert vuln.type == "hypothese_non_fondee"

    def test_hypothese_bien_sur(self, analyzer):
        vuln = analyzer._analyze_text("Bien sûr que c'est correct")
        assert vuln is not None
        assert vuln.type == "hypothese_non_fondee"

    def test_dichotomie_soit(self, analyzer):
        vuln = analyzer._analyze_text("Soit on accepte soit on refuse")
        assert vuln is not None
        assert vuln.type == "fausse_dichotomie"

    def test_pente_glissante(self, analyzer):
        vuln = analyzer._analyze_text("Cela mènera à la catastrophe")
        assert vuln is not None
        assert vuln.type == "pente_glissante"

    def test_causalite_douteuse(self, analyzer):
        vuln = analyzer._analyze_text("Le réchauffement provoque des tempêtes")
        assert vuln is not None
        assert vuln.type == "causalite_douteuse"

    def test_no_vulnerability(self, analyzer):
        vuln = analyzer._analyze_text("Le ciel est bleu")
        assert vuln is None

    def test_returns_vulnerability_object(self, analyzer):
        vuln = analyzer._analyze_text("Tous les oiseaux volent")
        assert isinstance(vuln, Vulnerability)
        assert vuln.score == 0.7
        assert vuln.target == ""  # Set later by caller


# ============================================================
# VulnerabilityAnalyzer — _analyze_structure
# ============================================================


class TestAnalyzeStructure:
    def test_no_premises(self, analyzer):
        arg = Argument(
            content="test",
            premises=[],
            conclusion="conclusion",
            argument_type="inductive",
            confidence=0.5,
        )
        vuln = analyzer._analyze_structure(arg)
        assert vuln is not None
        assert vuln.type == "manque_de_premisses"
        assert vuln.score == 0.9

    def test_incoherent_argument(self, analyzer):
        arg = Argument(
            content="test",
            premises=["Les pommes sont rouges"],
            conclusion="La lune est brillante",
            argument_type="inductive",
            confidence=0.5,
        )
        vuln = analyzer._analyze_structure(arg)
        assert vuln is not None
        assert vuln.type == "incoherence_logique"

    def test_coherent_argument(self, analyzer):
        arg = Argument(
            content="test",
            premises=["Les pommes sont des fruits"],
            conclusion="Donc les pommes sont comestibles",
            argument_type="inductive",
            confidence=0.5,
        )
        vuln = analyzer._analyze_structure(arg)
        # "pommes" is shared keyword → coherent
        assert vuln is None


# ============================================================
# VulnerabilityAnalyzer — _check_coherence
# ============================================================


class TestCheckCoherence:
    def test_shared_keywords_coherent(self, analyzer):
        arg = Argument(
            content="test",
            premises=["Les chats domestiques"],
            conclusion="Les chats sauvages",
            argument_type="inductive",
            confidence=0.5,
        )
        assert analyzer._check_coherence(arg) is True

    def test_no_shared_keywords_incoherent(self, analyzer):
        arg = Argument(
            content="test",
            premises=["Les pommes rouges"],
            conclusion="La lune brillante",
            argument_type="inductive",
            confidence=0.5,
        )
        assert analyzer._check_coherence(arg) is False


# ============================================================
# VulnerabilityAnalyzer — _extract_key_words
# ============================================================


class TestExtractKeyWords:
    def test_removes_stop_words(self, analyzer):
        words = analyzer._extract_key_words("le chat est un animal")
        assert "le" not in words
        assert "est" not in words
        assert "un" not in words
        assert "chat" in words
        assert "animal" in words

    def test_lowercases(self, analyzer):
        words = analyzer._extract_key_words("Chat Animal")
        assert "chat" in words
        assert "animal" in words

    def test_removes_punctuation(self, analyzer):
        words = analyzer._extract_key_words("chat, animal!")
        assert "chat" in words
        assert "animal" in words

    def test_empty_text(self, analyzer):
        words = analyzer._extract_key_words("")
        assert words == []


# ============================================================
# VulnerabilityAnalyzer — analyze_vulnerabilities (integration)
# ============================================================


class TestAnalyzeVulnerabilities:
    def test_premise_vulnerability_tagged(self, analyzer):
        arg = Argument(
            content="test",
            premises=["Tous les experts disent que"],
            conclusion="La conclusion est valide",
            argument_type="inductive",
            confidence=0.7,
        )
        vulns = analyzer.analyze_vulnerabilities(arg)
        premise_vulns = [v for v in vulns if v.target.startswith("premise_")]
        assert len(premise_vulns) >= 1
        assert premise_vulns[0].target == "premise_0"

    def test_conclusion_vulnerability_tagged(self, analyzer):
        arg = Argument(
            content="test",
            premises=["Les données montrent"],
            conclusion="C'est évidemment correct",
            argument_type="inductive",
            confidence=0.7,
        )
        vulns = analyzer.analyze_vulnerabilities(arg)
        conclusion_vulns = [v for v in vulns if v.target == "conclusion"]
        assert len(conclusion_vulns) >= 1

    def test_structure_vulnerability_no_premises(self, analyzer):
        arg = Argument(
            content="test",
            premises=[],
            conclusion="conclusion",
            argument_type="inductive",
            confidence=0.5,
        )
        vulns = analyzer.analyze_vulnerabilities(arg)
        structure_vulns = [v for v in vulns if v.target == "structure"]
        assert len(structure_vulns) >= 1

    def test_clean_argument_no_vulnerabilities(self, analyzer):
        arg = Argument(
            content="test",
            premises=["Les données scientifiques"],
            conclusion="Confirment l'hypothèse des données",
            argument_type="inductive",
            confidence=0.8,
        )
        vulns = analyzer.analyze_vulnerabilities(arg)
        # No text patterns, has premises, coherent → no vulns
        assert len(vulns) == 0


# TestParseLlmResponse / TestParseStructuredText withdrawn with their targets
# (#2137): parse_llm_response and parse_structured_text had zero callers.
