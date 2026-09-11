# -*- coding: utf-8 -*-
"""#2149 — aucune surface vivante n'appelle une méthode qui n'existe pas.

Trois vocabulaires se croisaient sur le même paramètre :

- l'ABC `AbstractFallacyDetector` (core/interfaces/fallacy_detector.py) déclare
  `detect(text) -> dict` ;
- `ContextualFallacyDetector` (agents/tools/analysis/new) expose
  `detect_contextual_fallacies(argument, context_description, ...)` ;
- `contextual_fallacy_analyzer` appelait `detect_fallacies(...)` — implémenté
  par **aucune** classe du dépôt ;
- et le showcase appelait `analyze_fallacies_with_context(...)` sur l'agent —
  méthode qui n'existe sur aucune classe non plus.

Les tests à `MagicMock` ne pouvaient pas le voir : un mock fabrique l'attribut
manquant. Ces deux gardes ferment la récidive :

1. `test_no_phantom_detector_method_at_live_call_sites` — AST-scanne les trois
   surfaces réparées ; ré-introduire l'un des appels fantômes rougit. Chaque
   fichier doit encore porter l'appel réel qu'il doit avoir (contrôle positif) :
   un fichier vidé ou renommé ne doit pas passer par vacuité.
2. `test_analyzer_result_key_matches_the_key_the_showcase_reads` — le contrat
   que le showcase suppose (la clé `contextual_fallacies`) est vérifié sur un
   détecteur **réel** conforme à l'ABC, pas sur un mock.
"""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[6]

#: Méthodes qu'aucune classe du dépôt n'implémente (#2149).
PHANTOM_METHODS = frozenset({"detect_fallacies", "analyze_fallacies_with_context"})

#: Surface -> appel réel qu'elle doit porter (contrôle de non-vacuité).
LIVE_SITES = {
    "argumentation_analysis/plugins/analysis_tools/logic/contextual_fallacy_analyzer.py": "detect",
    "argumentation_analysis/adapters/contextual_fallacy_detector_adapter.py": "detect_contextual_fallacies",
    "project_core/rhetorical_analysis_from_scripts/educational_showcase_system.py": "analyze_context",
}


def _called_attribute_names(tree: ast.AST):
    """Yield the attribute name of every `x.<name>(...)` call in an AST."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            yield node.func.attr


def test_no_phantom_detector_method_at_live_call_sites():
    """Aucune surface réparée n'appelle une méthode qui n'existe pas."""
    for rel_path, live_call in LIVE_SITES.items():
        path = REPO_ROOT / rel_path
        assert path.exists(), f"{rel_path} introuvable — ancrage de garde périmé"

        called = list(
            _called_attribute_names(ast.parse(path.read_text(encoding="utf-8")))
        )

        phantom_hits = sorted(PHANTOM_METHODS.intersection(called))
        assert not phantom_hits, (
            f"{rel_path} appelle {phantom_hits} — méthode implémentée par aucune "
            f"classe du dépôt (#2149). Les vocabulaires vivants sont : "
            f"`detect` (ABC), `detect_contextual_fallacies` (new/), "
            f"`analyze_context` (base)."
        )

        assert live_call in called, (
            f"{rel_path} n'appelle plus `{live_call}` — contrôle de non-vacuité : "
            f"un fichier renommé ou vidé ne doit pas passer cette garde."
        )


def test_analyzer_result_key_matches_the_key_the_showcase_reads():
    """La clé lue par le showcase est bien celle que l'analyseur produit.

    Chaîne réelle : showcase -> `analyze_context(...)` -> `contextual_fallacies`.
    Le détecteur est RÉEL et conforme à l'ABC (un MagicMock fabriquerait la
    méthode manquante et validerait un contrat inexistant).
    """
    from argumentation_analysis.core.interfaces.fallacy_detector import (
        AbstractFallacyDetector,
    )
    from argumentation_analysis.plugins.analysis_tools.logic.contextual_fallacy_analyzer import (
        EnhancedContextualFallacyAnalyzer,
    )

    class _ConformingDetector(AbstractFallacyDetector):
        def detect(self, text: str) -> dict:
            return {
                "fallacies": [
                    {
                        "fallacy_type": "Appel à l'autorité",
                        "keyword": "experts",
                        "context_text": "Les experts sont unanimes",
                        "confidence": 0.7,
                    }
                ]
            }

    analyzer = EnhancedContextualFallacyAnalyzer(fallacy_detector=_ConformingDetector())
    analyzer.learning_data = {
        "context_patterns": {},
        "fallacy_patterns": {},
        "feedback_history": [],
        "confidence_adjustments": {},
    }
    analyzer.feedback_history = []
    analyzer.context_embeddings_cache = {}
    analyzer._save_learning_data = lambda: None

    result = analyzer.analyze_context("Les experts sont unanimes.", "commercial")

    assert "contextual_fallacies" in result, (
        "la clé lue par le showcase (educational_showcase_system.py) a disparu "
        "de la réponse de `analyze_context`"
    )
    assert result["potential_fallacies_count"] == 1
