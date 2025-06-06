# Tests Unitaires pour les Outils d'Analyse Simulés (Mocks)

## Objectif

Ce répertoire contient les tests unitaires pour un ensemble de classes "mock" (simulées). Chacune de ces classes imite le comportement d'un outil d'analyse complexe (extraction d'arguments, détection de biais, analyse de cohérence, etc.) en utilisant des règles simples basées sur des mots-clés et des heuristiques.

L'objectif de ces tests n'est pas de valider une analyse sémantique profonde, mais de **s'assurer que les mocks eux-mêmes sont fiables et prévisibles**. Ils garantissent que ces simulateurs retournent des données structurées et cohérentes, ce qui est essentiel pour tester les composants de plus haut niveau qui dépendent de ces outils sans avoir besoin de lancer de véritables modèles de langage coûteux et non déterministes.

## Fonctionnalités Testées

Chaque fichier de test valide un outil simulé spécifique :

-   **`test_advanced_tools.py`** : Vérifie que la fonction de création d'outils avancés (`create_mock_advanced_rhetorical_tools`) assemble correctement le dictionnaire d'outils simulés.
-   **`test_argument_mining.py`** : Valide le `MockArgumentMiner`. Teste sa capacité à identifier des arguments explicites (avec "Prémisse:"/"Conclusion:"), implicites (avec "donc", "ainsi") et des affirmations simples, en fonction de mots-clés et de la longueur du texte.
-   **`test_bias_detection.py`** : Valide le `MockBiasDetector`. Teste la détection de divers biais cognitifs (confirmation, généralisation, etc.) en se basant sur une liste de motifs textuels prédéfinis.
-   **`test_claim_mining.py`** : Valide le `MockClaimMiner`. Teste l'extraction de "revendications" (claims) à partir d'un texte, soit via des mots-clés, soit en considérant le texte entier comme une revendication globale.
-   **`test_clarity_scoring.py`** : Valide le `MockClarityScorer`. Teste le calcul d'un score de clarté basé sur des pénalités (phrases longues, jargon, mots ambigus, etc.).
-   **`test_coherence_analysis.py`** : Valide le `MockCoherenceAnalyzer`. Teste le calcul d'un score de cohérence basé sur des bonus (mots de transition, répétition de thèmes) et des pénalités (contradictions).
-   **`test_emotional_tone_analysis.py`** : Valide le `MockEmotionalToneAnalyzer`. Teste la détection d'émotions (joie, tristesse, etc.) via des mots-clés et le calcul d'un score d'intensité pour chaque émotion.
-   **`test_engagement_analysis.py`** : Valide le `MockEngagementAnalyzer`. Teste le calcul d'un score d'engagement basé sur des signaux comme les questions directes, les appels à l'action et l'utilisation de pronoms inclusifs.
-   **`test_evidence_detection.py`** : Valide le `MockEvidenceDetector`. Teste la détection de "preuves" en suivant un ordre de priorité : mots-clés, données factuelles (chiffres), puis citations.
-   **`test_fallacy_categorization.py`** : Valide le `MockFallacyCategorizer`. Teste la capacité à regrouper une liste de sophismes dans des catégories prédéfinies (Pertinence, Ambiguïté, etc.).
-   **`test_fallacy_detection.py`** : Valide le `MockFallacyDetector`. Teste la détection de sophismes spécifiques en se basant sur la présence de phrases ou mots-clés déclencheurs.
-   **`test_rhetorical_analysis.py`** : Valide le `MockRhetoricalAnalyzer`. Teste l'identification de figures de style (métaphore, question rhétorique) et la détermination d'une tonalité globale à partir de mots-clés.

## Dépendances Clés

-   **`pytest`** : Utilisé comme framework de test, avec un usage intensif des fixtures pour instancier les classes mockées.
-   **`logging` (via `caplog`)** : Utilisé pour vérifier que les mocks journalisent correctement les avertissements lorsqu'ils reçoivent des entrées invalides (ex: non textuelles).
