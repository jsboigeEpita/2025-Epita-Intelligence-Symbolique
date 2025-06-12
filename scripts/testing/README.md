# Scripts de Test

Ce répertoire contient des scripts spécifiques pour des scénarios de test, des simulations, ou des validations ponctuelles de composants du projet d'analyse argumentative. Ces scripts peuvent compléter les tests unitaires et d'intégration formels.

## Scripts Disponibles

- **`debug_test_crypto_cycle.py`**: Script pour déboguer le cycle de chiffrement/déchiffrement dans des contextes de test.
- **`get_test_metrics.py`**: Calcule et affiche des métriques sur l'exécution des tests (potentiellement à partir de rapports JUnit/XML).
- **`run_all_embed_tests.py`** / **`run_embed_tests.py`**: Scripts pour exécuter des tests spécifiques liés à l'embarquement de données ou de modèles.
- **`run_tests_alternative.py`**: Un autre script pour lancer des tests, potentiellement avec une configuration ou un périmètre différent.
- **`simple_test_runner.py`** / **`test_runner_simple.py`**: Runners de test simplifiés pour des exécutions rapides ou ciblées.
- **`simulation_agent_informel.py`** : Script de simulation pour tester le comportement des agents informels dans différents contextes d'analyse.
- **`test_agent_informel.py`** : Script de test pour valider le fonctionnement des agents informels et leur capacité à analyser des arguments.
- **`test_fallacy_adapter.py`**: Script dédié au test de l'adaptateur de sophismes, vérifiant sa capacité à interfacer correctement avec les logiques de détection de sophismes.
- **`test_rhetorical_analysis.py`**: Script pour tester les fonctionnalités d'analyse rhétorique, potentiellement en exécutant des analyses sur des exemples de textes et en validant les sorties.
- **`validate_embed_tests.py`**: Valide les résultats des tests d'embarquement.

## Utilisation

Chaque script peut avoir ses propres arguments et modes de fonctionnement. Référez-vous à l'aide de chaque script (ex: `python scripts/testing/nom_script.py --help`) ou à son code source pour les détails.

### Exemple Général

```bash
# Exécuter un script de test spécifique
python scripts/testing/test_fallacy_adapter.py

# Exécuter une simulation
python scripts/testing/simulation_agent_informel.py --corpus exemples
```

## Intégration avec les Tests Unitaires

Ces scripts peuvent être utilisés en complément des tests unitaires (situés dans le répertoire `tests/` principal) pour valider le comportement des composants dans des scénarios plus complexes ou plus proches des conditions réelles d'utilisation. Ils ne remplacent pas les tests formels mais offrent un moyen de prototypage ou de validation rapide.

## Bonnes Pratiques

1.  **Isolation** : Les scripts de test devraient idéalement être isolés et ne pas dépendre d'un état trop spécifique du système pour faciliter leur exécution.
2.  **Reproductibilité** : Les tests devraient viser à être reproductibles.
3.  **Documentation** : Chaque script devrait, autant que possible, documenter son objectif, ses paramètres et son comportement attendu.
4.  **Validation** : Les scripts devraient inclure des mécanismes de validation (assertions, vérifications de sortie) pour confirmer que les résultats sont corrects.

L'objectif à terme est d'intégrer la logique de validation de ces scripts dans le framework de test principal (`pytest` et les tests dans `tests/`) lorsque cela est pertinent et apporte une valeur ajoutée à la suite de tests automatisée.