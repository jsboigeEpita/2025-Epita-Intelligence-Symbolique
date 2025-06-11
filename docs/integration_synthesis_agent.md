# Intégration SynthesisAgent - Documentation d'Usage

## Vue d'ensemble

Le script de démonstration principal `scripts/demo/run_rhetorical_analysis_demo.py` a été enrichi avec l'intégration du SynthesisAgent Core, offrant maintenant deux modes d'analyse :

1. **Mode Logic** (traditionnel) : Analyse logique seule avec agents spécialisés
2. **Mode Unified** (nouveau) : Analyse unifiée combinant analyses formelles et informelles via le SynthesisAgent

## Nouvelles Options de Ligne de Commande

### `--analysis-type`
- **Valeurs acceptées** : `logic`, `unified`
- **Défaut** : `logic`
- **Description** : Détermine le type d'analyse à effectuer

### `--logic-type` (existant, amélioré)
- **Valeurs acceptées** : `propositional`, `first_order`, `modal`
- **Défaut** : `propositional`
- **Description** : Type de logique à utiliser (applicable aux deux modes d'analyse)

## Exemples d'Usage

### Analyse Traditionnelle (Mode Logic)

```bash
# Analyse logique propositionnelle (comportement par défaut)
python scripts/demo/run_rhetorical_analysis_demo.py

# Analyse logique modale
python scripts/demo/run_rhetorical_analysis_demo.py --analysis-type logic --logic-type modal

# Analyse logique de premier ordre
python scripts/demo/run_rhetorical_analysis_demo.py --logic-type first_order
```

### Analyse Unifiée (Mode Unified avec SynthesisAgent)

```bash
# Analyse unifiée avec logique propositionnelle
python scripts/demo/run_rhetorical_analysis_demo.py --analysis-type unified

# Analyse unifiée avec logique modale
python scripts/demo/run_rhetorical_analysis_demo.py --analysis-type unified --logic-type modal

# Analyse unifiée avec logique de premier ordre
python scripts/demo/run_rhetorical_analysis_demo.py --analysis-type unified --logic-type first_order
```

## Différences entre les Modes

### Mode Logic (Traditionnel)
- Exécute les analyses informelles et formelles séparément
- Utilise l'orchestration existante (`run_full_analysis_demo`)
- Rapport structuré selon le format traditionnel
- Compatible avec toute la logique existante

### Mode Unified (SynthesisAgent)
- Coordination unifiée des analyses via le SynthesisAgent Core
- Synthèse intelligente des résultats formels et informels
- Rapport de synthèse unifié avec évaluation globale
- Détection automatique de contradictions
- Recommandations basées sur l'analyse complète
- Phase 1 : Fonctionnalités de base (enable_advanced_features=False)

## Structure du Rapport Unifié

Le mode unified produit un rapport enrichi contenant :

### 1. Résumé Exécutif
- Synthèse des analyses formelles et informelles
- Évaluation globale de la validité

### 2. Statistiques Détaillées
- Longueur du texte analysé
- Nombre de formules logiques extraites
- Nombre de sophismes détectés
- Contradictions identifiées

### 3. Évaluation Globale
- Validité globale (True/False)
- Niveau de confiance (0.0 à 1.0)

### 4. Détections et Recommandations
- Contradictions identifiées automatiquement
- Recommandations d'amélioration
- Suggestions d'analyse complémentaire

### 5. Détails Techniques
- Résultats détaillés par type de logique
- Analyse informelle complète
- Métadonnées de traitement

## Configuration SynthesisAgent

Le SynthesisAgent est configuré en **Phase 1** :
- `enable_advanced_features = False`
- Mode de synthèse simple et robuste
- Compatible avec tous les types de logique
- Prêt pour extension vers les phases avancées

## Fichiers de Sortie

Les deux modes génèrent :
- **Log détaillé** : `logs/rhetorical_analysis_demo_conversation.log`
- **Rapport JSON** : `logs/rhetorical_analysis_report.json`

Le mode unified ajoute :
- **Rapport de synthèse textuel** affiché directement dans la console
- **Métriques unifiées** dans le rapport JSON

## Compatibilité

✅ **Compatible** avec toutes les options existantes
✅ **Rétrocompatible** : comportement par défaut inchangé
✅ **Extensible** : prêt pour les phases avancées du SynthesisAgent

## Validation des Tests

Les commandes suivantes ont été validées avec succès :

```bash
# Tests de compatibilité
python scripts/demo/run_rhetorical_analysis_demo.py --analysis-type logic --logic-type modal
python scripts/demo/run_rhetorical_analysis_demo.py --analysis-type unified
python scripts/demo/run_rhetorical_analysis_demo.py --analysis-type unified --logic-type modal
```

## Évolutions Futures

Le SynthesisAgent étant conçu avec une architecture progressive, les phases futures apporteront :

- **Phase 2** : Fusion avancée des résultats
- **Phase 3** : Résolution de conflits et gestion de la qualité
- **Phase 4** : Évaluation de preuves et métriques avancées

L'intégration actuelle est prête pour ces évolutions sans modification du script principal.