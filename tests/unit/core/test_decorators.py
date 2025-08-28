import unittest
from unittest.mock import MagicMock, call
from src.core.decorators import track_tokens
from src.benchmarking.benchmark_service import BenchmarkService

class TestTrackTokensDecorator(unittest.TestCase):

    def test_track_tokens_with_string_args(self):
        """
        Vérifie que le décorateur suit correctement les tokens pour des arguments
        et une valeur de retour de type chaîne de caractères.
        """
        # Création d'un mock pour le BenchmarkService
        mock_benchmark_service = MagicMock(spec=BenchmarkService)

        # Fonction de test simple à décorer
        @track_tokens(benchmark_service=mock_benchmark_service)
        def simple_function(text1, text2):
            return f"{text1} {text2}"

        # Appel de la fonction décorée
        result = simple_function("Hello", text2="World")

        # Vérification du résultat de la fonction
        self.assertEqual(result, "Hello World")

        # Vérification des appels à record_metric
        # "Hello" -> 1 token, "World" -> 1 token
        # "Hello World" -> 2 tokens
        expected_calls = [
            call('input_tokens', 2),
            call('output_tokens', 2)
        ]
        mock_benchmark_service.record_metric.assert_has_calls(expected_calls, any_order=False)

    def test_track_tokens_with_dict_args(self):
        """
        Vérifie le suivi des tokens lorsque les arguments et le retour
        sont des dictionnaires contenant des chaînes de caractères.
        """
        mock_benchmark_service = MagicMock(spec=BenchmarkService)

        @track_tokens(benchmark_service=mock_benchmark_service)
        def function_with_dict(payload):
            return {"response": f"Processed {payload['data']}"}

        payload = {"data": "some text"}
        result = function_with_dict(payload)

        self.assertEqual(result, {"response": "Processed some text"})

        # "some text" -> 2 tokens
        # "Processed some text" -> 3 tokens
        expected_calls = [
            call('input_tokens', 2),
            call('output_tokens', 3)
        ]
        mock_benchmark_service.record_metric.assert_has_calls(expected_calls, any_order=False)

    def test_track_tokens_with_no_strings(self):
        """
        Vérifie que le décorateur gère correctement les cas où il n'y a
        aucune chaîne de caractères en entrée ou en sortie.
        """
        mock_benchmark_service = MagicMock(spec=BenchmarkService)

        @track_tokens(benchmark_service=mock_benchmark_service)
        def function_with_no_strings(num1, num2):
            return num1 + num2

        result = function_with_no_strings(10, 20)

        self.assertEqual(result, 30)

        expected_calls = [
            call('input_tokens', 0),
            call('output_tokens', 0)
        ]
        mock_benchmark_service.record_metric.assert_has_calls(expected_calls, any_order=False)

if __name__ == '__main__':
    unittest.main()