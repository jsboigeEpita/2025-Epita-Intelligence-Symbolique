"""Tests du helper ``parse_kernel_json_object`` (#1773 constat 4, amendement R819).

Le helper EST la convention réutilisable : TweetyLogicPlugin (#1774) doit
adopter la même forme d'erreur, pas une variante locale. Ces tests fixent
le contrat :
- non-objet JSON => erreur structurée avec le type reçu, jamais d'exception ;
- clé requise absente => l'erreur nomme les clés reçues ET attendues.
"""

from argumentation_analysis.plugins.kernel_input import parse_kernel_json_object


class TestParseKernelJsonObject:
    def test_invalid_json_string(self):
        params, err = parse_kernel_json_object("not json", ["text"])
        assert params is None
        assert err == {"error": "Invalid JSON input"}

    def test_json_array_is_not_an_object(self):
        params, err = parse_kernel_json_object("[1, 2]", ["text"])
        assert params is None
        assert err["error"] == "Invalid input: expected a JSON object"
        assert err["received_type"] == "list"

    def test_non_string_non_object(self):
        params, err = parse_kernel_json_object(123, ["text"])
        assert params is None
        assert err["received_type"] == "int"

    def test_json_string_scalar_is_not_an_object(self):
        params, err = parse_kernel_json_object('"a string"', ["text"])
        assert params is None
        assert err["received_type"] == "str"

    def test_missing_required_key_names_both_sides(self):
        params, err = parse_kernel_json_object(
            {"logic_type": "pl"},
            expected_keys=["text", "logic_type"],
            required_keys=["text"],
        )
        assert params is None
        assert "text" in err["error"]
        assert err["received_keys"] == ["logic_type"]
        assert "text" in err["expected_keys"]

    def test_valid_object_passes_through(self):
        params, err = parse_kernel_json_object(
            '{"text": "a"}', expected_keys=["text"], required_keys=["text"]
        )
        assert err is None
        assert params == {"text": "a"}

    def test_optional_missing_key_is_fine(self):
        params, err = parse_kernel_json_object("{}", expected_keys=["text"])
        assert err is None
        assert params == {}
