# Tests de Performance du Système d'Analyse Argumentative

Ce répertoire contient les résultats des tests de performance effectués sur le système d'analyse argumentative, permettant d'évaluer ses capacités et ses limites dans différents contextes d'utilisation.

## Structure du Répertoire

```
performance_tests/
├── rapport_synthese_manuel.md
└── README.md
```

## Contenu du Répertoire

### [Rapport de Synthèse Manuel](./rapport_synthese_manuel.md)

Ce document présente une synthèse manuelle des tests de performance prévus sur différents extraits de discours pour évaluer les performances de l'agent d'analyse rhétorique. Il inclut :

- Une introduction au contexte des tests
- Une description détaillée des extraits analysés
- Une analyse préliminaire de chaque extrait
- Les défis anticipés pour l'agent d'analyse
- Des recommandations pour les tests futurs

## Extraits Analysés

Le rapport de synthèse couvre l'analyse des extraits suivants :

1. **exemple_sophisme.txt** - Texte argumentatif sur la régulation de l'IA contenant plusieurs sophismes identifiables
2. **texte_sans_marqueurs.txt** - Texte informatif sur la pensée critique sans sophismes évidents
3. **article_scientifique.txt** - Article académique sur l'analyse d'arguments par NLP
4. **discours_politique.txt** - Discours politique avec structure rhétorique claire
5. **discours_avec_template.txt** - Allocution présidentielle avec marqueurs explicites

## Objectifs des Tests de Performance

Les tests de performance visent à évaluer :

1. **Précision** : Capacité du système à identifier correctement les arguments et sophismes
2. **Robustesse** : Comportement du système face à différents styles et structures de texte
3. **Efficacité** : Temps d'exécution et utilisation des ressources
4. **Adaptabilité** : Capacité à s'adapter à différents contextes argumentatifs

## Métriques d'Évaluation

Les performances du système sont évaluées selon les métriques suivantes :

- **Précision dans l'identification des arguments**
- **Précision dans l'identification des sophismes**
- **Taux de faux positifs** (sophismes incorrectement identifiés)
- **Temps d'exécution** pour différentes longueurs de texte

## Utilisation des Résultats

Les résultats des tests de performance peuvent être utilisés pour :

1. **Identifier les forces et faiblesses** du système d'analyse
2. **Orienter le développement futur** en ciblant les aspects à améliorer
3. **Établir des benchmarks** pour évaluer les améliorations futures
4. **Documenter les capacités** du système pour les utilisateurs

## Exécution de Nouveaux Tests

Pour exécuter de nouveaux tests de performance :

1. Utilisez le script `scripts/execution/run_performance_tests.py`
2. Configurez les paramètres de test selon vos besoins
3. Analysez les résultats générés dans ce répertoire

```bash
python scripts/execution/run_performance_tests.py --config config/performance_test_config.json
```

## Problèmes Connus

- Problèmes avec les dépendances Python (`pydantic_core` et `numpy`) qui peuvent empêcher l'exécution complète des tests automatisés
- Certains tests nécessitent une analyse manuelle pour une évaluation qualitative complète

## Liens vers la Documentation Associée

- [Scripts d'Exécution](../../scripts/execution/README.md)
- [Documentation des Outils d'Analyse](../../docs/outils/README.md)
- [Exemples de Textes](../../examples/README.md)
- [Résultats Globaux](../README.md)