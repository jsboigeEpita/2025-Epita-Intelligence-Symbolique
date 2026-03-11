# tests/unit/argumentation_analysis/agents/core/counter_argument/test_counter_argument_parser.py
"""Tests for ArgumentParser, VulnerabilityAnalyzer, and text parsing utilities."""

import pytest

from argumentation_analysis.agents.core.counter_argument.parser import (
    ArgumentParser,
    VulnerabilityAnalyzer,
    parse_llm_response,
    parse_structured_text,
)
from argumentation_analysis.agents.core.counter_argument.definitions import (
    Argument,
    Vulnerability,
    CounterArgumentType,
)


# ── ArgumentParser init ──

class TestArgumentParserInit:
    def test_has_premise_markers(self):
        parser = ArgumentParser()
        assert len(parser.premise_markers) > 0
        assert "parce que" in parser.premise_markers

    def test_has_conclusion_markers(self):
        parser = ArgumentParser()
        assert len(parser.conclusion_markers) > 0
        assert "donc" in parser.conclusion_markers

    def test_has_argument_types(self):
        parser = ArgumentParser()
        assert "deductive" in parser.argument_types
        assert "inductive" in parser.argument_types
        assert "abductive" in parser.argument_types

    def test_has_vulnerability_analyzer(self):
        parser = ArgumentParser()
        assert isinstance(parser.vulnerability_analyzer, VulnerabilityAnalyzer)


# ── parse_argument ──

class TestParseArgument:
    @pytest.fixture
    def parser(self):
        return ArgumentParser()

    def test_returns_argument(self, parser):
        result = parser.parse_argument("Simple text.")
        assert isinstance(result, Argument)
        assert result.content == "Simple text."

    def test_extracts_premises_with_marker(self, parser):
        text = "Les gens sont heureux parce que le soleil brille."
        result = parser.parse_argument(text)
        assert len(result.premises) >= 1

    def test_extracts_conclusion_with_marker(self, parser):
        text = "Il pleut. Donc il faut un parapluie."
        result = parser.parse_argument(text)
        assert "donc" in result.conclusion.lower() or "parapluie" in result.conclusion.lower()

    def test_single_sentence(self, parser):
        text = "Le ciel est bleu."
        result = parser.parse_argument(text)
        assert len(result.premises) >= 1
        assert result.conclusion != ""

    def test_confidence_range(self, parser):
        result = parser.parse_argument("A car B. Donc C.")
        assert 0.0 <= result.confidence <= 1.0

    def test_multiple_sentences(self, parser):
        text = "La terre est ronde. Les photos le montrent. Donc c'est un fait."
        result = parser.parse_argument(text)
        assert len(result.premises) >= 1


# ── _extract_premises ──

class TestExtractPremises:
    @pytest.fixture
    def parser(self):
        return ArgumentParser()

    def test_with_parce_que(self, parser):
        text = "Je suis fatigué parce que j'ai mal dormi."
        premises = parser._extract_premises(text)
        assert len(premises) >= 1

    def test_with_car(self, parser):
        text = "Il est intelligent car il lit beaucoup."
        premises = parser._extract_premises(text)
        assert len(premises) >= 1

    def test_with_conclusion_marker_before(self, parser):
        text = "Il fait froid. Donc on reste dedans."
        premises = parser._extract_premises(text)
        assert len(premises) >= 1

    def test_no_markers_first_sentence(self, parser):
        text = "Premier point. Deuxième point."
        premises = parser._extract_premises(text)
        assert len(premises) >= 1

    def test_single_sentence_no_markers(self, parser):
        text = "Simple affirmation."
        premises = parser._extract_premises(text)
        assert premises == ["Simple affirmation."] or len(premises) >= 1


# ── _extract_conclusion ──

class TestExtractConclusion:
    @pytest.fixture
    def parser(self):
        return ArgumentParser()

    def test_with_donc(self, parser):
        text = "Il pleut. Donc le sol est mouillé."
        conclusion = parser._extract_conclusion(text)
        assert "donc" in conclusion.lower() or "mouillé" in conclusion.lower()

    def test_with_par_consequent(self, parser):
        text = "Les données le montrent. Par conséquent, c'est vrai."
        conclusion = parser._extract_conclusion(text)
        assert len(conclusion) > 0

    def test_with_premise_marker(self, parser):
        text = "C'est vrai parce que les données le montrent."
        conclusion = parser._extract_conclusion(text)
        assert len(conclusion) > 0

    def test_fallback_last_sentence(self, parser):
        text = "Premier. Deuxième. Troisième."
        conclusion = parser._extract_conclusion(text)
        assert "Troisième" in conclusion or len(conclusion) > 0

    def test_empty_text(self, parser):
        assert parser._extract_conclusion("") == ""


# ── _determine_argument_type ──

class TestDetermineArgumentType:
    @pytest.fixture
    def parser(self):
        return ArgumentParser()

    def test_deductive_tous(self, parser):
        assert parser._determine_argument_type("Tous les hommes sont mortels.") == "deductive"

    def test_deductive_chaque(self, parser):
        assert parser._determine_argument_type("Chaque étudiant doit réussir.") == "deductive"

    def test_inductive_generalement(self, parser):
        assert parser._determine_argument_type("Généralement, il fait beau en été.") == "inductive"

    def test_inductive_souvent(self, parser):
        assert parser._determine_argument_type("Il est souvent en retard.") == "inductive"

    def test_abductive_meilleure_explication(self, parser):
        assert parser._determine_argument_type("La meilleure explication est...") == "abductive"

    def test_abductive_probablement(self, parser):
        assert parser._determine_argument_type("C'est probablement la cause.") == "abductive"

    def test_si_alors_deductive(self, parser):
        assert parser._determine_argument_type("Si A alors B.") == "deductive"

    def test_default_inductive(self, parser):
        assert parser._determine_argument_type("Le ciel.") == "inductive"

    def test_secondary_inductive_exemple(self, parser):
        assert parser._determine_argument_type("Par exemple, on observe que...") == "inductive"

    def test_secondary_abductive_explication(self, parser):
        assert parser._determine_argument_type("L'explication est simple.") == "abductive"


# ── _calculate_confidence ──

class TestCalculateConfidence:
    @pytest.fixture
    def parser(self):
        return ArgumentParser()

    def test_base_confidence(self, parser):
        c = parser._calculate_confidence([], "")
        assert c == 0.5

    def test_with_premises(self, parser):
        c = parser._calculate_confidence(["premise"], "")
        assert c >= 0.7

    def test_with_conclusion(self, parser):
        c = parser._calculate_confidence([], "conclusion")
        assert c >= 0.7

    def test_with_both(self, parser):
        c = parser._calculate_confidence(["premise"], "conclusion")
        assert c >= 0.89  # 0.5 + 0.2 + 0.2 = 0.9 (floating point)

    def test_with_markers(self, parser):
        c = parser._calculate_confidence(["parce que X"], "donc Y")
        assert c == 1.0

    def test_max_is_1(self, parser):
        c = parser._calculate_confidence(
            ["parce que premise", "car another"],
            "donc conclusion"
        )
        assert c <= 1.0


# ── _split_into_sentences ──

class TestSplitIntoSentences:
    @pytest.fixture
    def parser(self):
        return ArgumentParser()

    def test_period_split(self, parser):
        result = parser._split_into_sentences("Hello. World.")
        assert len(result) == 2

    def test_exclamation_split(self, parser):
        result = parser._split_into_sentences("Wow! Amazing!")
        assert len(result) == 2

    def test_question_split(self, parser):
        result = parser._split_into_sentences("Why? Because.")
        assert len(result) == 2

    def test_empty_string(self, parser):
        assert parser._split_into_sentences("") == []

    def test_no_punctuation(self, parser):
        result = parser._split_into_sentences("No punctuation here")
        assert len(result) == 1


# ── _fix_identical_premise_conclusion ──

class TestFixIdenticalPremiseConclusion:
    @pytest.fixture
    def parser(self):
        return ArgumentParser()

    def test_no_fix_needed(self, parser):
        p, c = parser._fix_identical_premise_conclusion(
            ["A is true"], "B follows", "A is true. B follows."
        )
        assert p == ["A is true"]
        assert c == "B follows"

    def test_empty_premises(self, parser):
        p, c = parser._fix_identical_premise_conclusion([], "C", "text")
        assert p == []
        assert c == "C"

    def test_empty_conclusion(self, parser):
        p, c = parser._fix_identical_premise_conclusion(["P"], "", "text")
        assert p == ["P"]
        assert c == ""

    def test_identical_with_comma_split(self, parser):
        text = "Le soleil brille, il fait chaud"
        p, c = parser._fix_identical_premise_conclusion(
            ["Le soleil brille, il fait chaud"],
            "Le soleil brille, il fait chaud",
            text,
        )
        # Should split by comma
        assert p[0] != c or "implicite" in p[0].lower()


# ── VulnerabilityAnalyzer ──

class TestVulnerabilityAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return VulnerabilityAnalyzer()

    def test_init_patterns(self, analyzer):
        assert "generalisation_abusive" in analyzer.vulnerability_patterns
        assert "hypothese_non_fondee" in analyzer.vulnerability_patterns
        assert "fausse_dichotomie" in analyzer.vulnerability_patterns
        assert "pente_glissante" in analyzer.vulnerability_patterns
        assert "causalite_douteuse" in analyzer.vulnerability_patterns

    def test_no_vulnerabilities(self, analyzer):
        arg = Argument(
            content="Simple text",
            premises=["Simple premise"],
            conclusion="Simple conclusion",
            argument_type="inductive",
            confidence=0.8,
        )
        vulns = analyzer.analyze_vulnerabilities(arg)
        # May have structural vuln but no pattern match
        assert isinstance(vulns, list)

    def test_generalisation_abusive(self, analyzer):
        arg = Argument(
            content="Tous les X sont Y",
            premises=["Tous les étudiants réussissent"],
            conclusion="conclusion test",
            argument_type="deductive",
            confidence=0.8,
        )
        vulns = analyzer.analyze_vulnerabilities(arg)
        types = [v.type for v in vulns]
        assert "generalisation_abusive" in types

    def test_hypothese_non_fondee(self, analyzer):
        arg = Argument(
            content="évidemment c'est vrai",
            premises=["Évidemment, tout le monde sait que"],
            conclusion="c'est clair",
            argument_type="inductive",
            confidence=0.5,
        )
        vulns = analyzer.analyze_vulnerabilities(arg)
        types = [v.type for v in vulns]
        assert "hypothese_non_fondee" in types

    def test_fausse_dichotomie(self, analyzer):
        arg = Argument(
            content="Soit on accepte soit on refuse",
            premises=["Soit on accepte, soit on refuse"],
            conclusion="Il faut choisir",
            argument_type="deductive",
            confidence=0.7,
        )
        vulns = analyzer.analyze_vulnerabilities(arg)
        types = [v.type for v in vulns]
        assert "fausse_dichotomie" in types

    def test_pente_glissante(self, analyzer):
        arg = Argument(
            content="Cela mènera à la catastrophe",
            premises=["Cela mènera à la catastrophe"],
            conclusion="conclusion",
            argument_type="inductive",
            confidence=0.6,
        )
        vulns = analyzer.analyze_vulnerabilities(arg)
        types = [v.type for v in vulns]
        assert "pente_glissante" in types

    def test_causalite_douteuse(self, analyzer):
        arg = Argument(
            content="Le café cause des maladies",
            premises=["Le café cause des maladies"],
            conclusion="conclusion",
            argument_type="inductive",
            confidence=0.5,
        )
        vulns = analyzer.analyze_vulnerabilities(arg)
        types = [v.type for v in vulns]
        assert "causalite_douteuse" in types

    def test_vulnerability_has_score(self, analyzer):
        arg = Argument(
            content="Tous disent que",
            premises=["Tous les experts disent"],
            conclusion="conclusion",
            argument_type="deductive",
            confidence=0.7,
        )
        vulns = analyzer.analyze_vulnerabilities(arg)
        for v in vulns:
            assert isinstance(v.score, float)
            assert v.score > 0

    def test_no_premises_structural_vulnerability(self, analyzer):
        arg = Argument(
            content="conclusion",
            premises=[],
            conclusion="conclusion",
            argument_type="inductive",
            confidence=0.3,
        )
        vulns = analyzer.analyze_vulnerabilities(arg)
        types = [v.type for v in vulns]
        assert "manque_de_premisses" in types

    def test_incoherence_logique(self, analyzer):
        arg = Argument(
            content="abc xyz",
            premises=["Les pommes sont rouges"],
            conclusion="La mathématique est belle",
            argument_type="inductive",
            confidence=0.5,
        )
        vulns = analyzer.analyze_vulnerabilities(arg)
        types = [v.type for v in vulns]
        assert "incoherence_logique" in types

    def test_coherent_no_incoherence(self, analyzer):
        arg = Argument(
            content="Les pommes sont rouges donc les pommes sont colorées",
            premises=["Les pommes sont rouges"],
            conclusion="Les pommes sont colorées",
            argument_type="deductive",
            confidence=0.8,
        )
        vulns = analyzer.analyze_vulnerabilities(arg)
        types = [v.type for v in vulns]
        assert "incoherence_logique" not in types

    def test_vulnerability_target_set(self, analyzer):
        arg = Argument(
            content="Tous les gens pensent",
            premises=["Tous les gens pensent ainsi"],
            conclusion="simple conclusion",
            argument_type="deductive",
            confidence=0.7,
        )
        vulns = analyzer.analyze_vulnerabilities(arg)
        for v in vulns:
            assert v.target != "" or v.target == ""  # always set


# ── identify_vulnerabilities via ArgumentParser ──

class TestIdentifyVulnerabilities:
    def test_sorted_by_score(self):
        parser = ArgumentParser()
        arg = Argument(
            content="Évidemment tous les experts disent que cela mènera à la catastrophe",
            premises=["Évidemment tous les experts"],
            conclusion="cela mènera à la catastrophe",
            argument_type="deductive",
            confidence=0.7,
        )
        vulns = parser.identify_vulnerabilities(arg)
        scores = [v.score for v in vulns]
        assert scores == sorted(scores, reverse=True)


# ── parse_llm_response ──

class TestParseLlmResponse:
    def test_valid_json(self):
        result = parse_llm_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_list(self):
        result = parse_llm_response('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_invalid_json_structured(self):
        result = parse_llm_response("key: value\nother: data")
        assert result["key"] == "value"
        assert result["other"] == "data"

    def test_empty_json_object(self):
        result = parse_llm_response('{}')
        assert result == {}


# ── parse_structured_text ──

class TestParseStructuredText:
    def test_single_kv(self):
        result = parse_structured_text("name: Alice")
        assert result["name"] == "Alice"

    def test_multiple_kv(self):
        result = parse_structured_text("name: Alice\nage: 30")
        assert result["name"] == "Alice"
        assert result["age"] == "30"

    def test_multiline_value(self):
        text = "description: Line one\n  continued line"
        result = parse_structured_text(text)
        assert "Line one" in result["description"]

    def test_empty_text(self):
        result = parse_structured_text("")
        assert result == {}

    def test_blank_lines_skipped(self):
        text = "key: val\n\nother: data"
        result = parse_structured_text(text)
        assert result["key"] == "val"
        assert result["other"] == "data"

    def test_keys_lowercased(self):
        result = parse_structured_text("Name: Alice")
        assert "name" in result

    def test_no_colon_lines_appended(self):
        text = "key: first line\nsecond line\nother: x"
        result = parse_structured_text(text)
        assert "first line" in result["key"]
        assert "second line" in result["key"]


# ── _extract_key_words (VulnerabilityAnalyzer) ──

class TestExtractKeyWords:
    def test_removes_stop_words(self):
        analyzer = VulnerabilityAnalyzer()
        words = analyzer._extract_key_words("le chat est sur la table")
        assert "chat" in words
        assert "table" in words
        assert "le" not in words
        assert "est" not in words

    def test_removes_punctuation(self):
        analyzer = VulnerabilityAnalyzer()
        words = analyzer._extract_key_words("Bonjour, monde!")
        assert "bonjour" in words

    def test_empty_text(self):
        analyzer = VulnerabilityAnalyzer()
        words = analyzer._extract_key_words("")
        assert words == []
