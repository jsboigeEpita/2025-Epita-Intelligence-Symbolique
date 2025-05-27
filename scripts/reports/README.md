# Scripts de Génération de Rapports

Ce répertoire contient des scripts dédiés à la génération et à la mise à jour de rapports pour le projet d'analyse argumentative.

## Scripts Disponibles

- **`update_coverage_section.py`** : Met à jour la section de couverture de tests dans les rapports existants avec les dernières données de couverture.
- **`update_final_report.py`** : Met à jour le rapport final avec les dernières informations et analyses.

## Utilisation

### Mise à jour de la Section de Couverture

Le script `update_coverage_section.py` permet de mettre à jour automatiquement les sections de couverture de tests dans les rapports Markdown :

```bash
# Mise à jour standard
python scripts/reports/update_coverage_section.py --report docs/rapport_final.md

# Mise à jour avec options spécifiques
python scripts/reports/update_coverage_section.py --report docs/rapport_final.md --coverage-file .coverage --format html
```

### Mise à jour du Rapport Final

Le script `update_final_report.py` permet de mettre à jour le rapport final avec les dernières informations :

```bash
# Mise à jour standard
python scripts/reports/update_final_report.py

# Mise à jour avec options spécifiques
python scripts/reports/update_final_report.py --output rapports/rapport_final_100_pourcent.md --include-metrics
```

## Intégration avec d'Autres Scripts

Ces scripts sont souvent utilisés en conjonction avec d'autres scripts du projet, notamment :

- `scripts/generate_coverage_report.py` : Génère les données de couverture brutes.
- `scripts/generate_comprehensive_report.py` : Génère un rapport complet qui peut ensuite être mis à jour.
- `scripts/visualize_test_coverage.py` : Crée des visualisations qui peuvent être incluses dans les rapports.

Exemple d'utilisation combinée :

```bash
# Générer les données de couverture, puis mettre à jour le rapport
python scripts/generate_coverage_report.py && python scripts/reports/update_coverage_section.py --report docs/rapport_final.md
```

## Format des Rapports

Les rapports générés ou mis à jour par ces scripts suivent généralement une structure Markdown standard avec :

1. **En-tête** : Titre, date, auteur, etc.
2. **Résumé** : Synthèse des points clés.
3. **Sections détaillées** : Analyses, résultats, métriques, etc.
4. **Annexes** : Données supplémentaires, graphiques, etc.

## Bonnes Pratiques

1. **Automatisation** : Utilisez ces scripts dans des workflows automatisés pour maintenir les rapports à jour.
2. **Versionnement** : Conservez un historique des rapports pour suivre l'évolution du projet.
3. **Cohérence** : Assurez-vous que les rapports générés sont cohérents avec les autres documents du projet.
4. **Validation** : Vérifiez que les données incluses dans les rapports sont exactes et à jour.