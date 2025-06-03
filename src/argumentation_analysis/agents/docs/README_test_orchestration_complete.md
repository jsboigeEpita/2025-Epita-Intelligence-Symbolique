# Test d'Orchestration Complète Multi-Agents

Ce projet permet de tester et d'analyser une orchestration complète du système d'analyse argumentative avec tous les agents (PM, Informel, PL, Extract), en mettant particulièrement l'accent sur l'impact des améliorations apportées à l'agent Informel.

## Contexte

Suite aux améliorations apportées à l'agent Informel et à la conversation agentique, nous devons tester l'ensemble du système en exécutant une orchestration complète avec tous les agents sur un texte exigeant. Cette tâche permet d'évaluer l'impact des améliorations sur la qualité globale de l'analyse argumentative.

## Structure du Projet

Le projet est composé de plusieurs scripts:

- `test_orchestration_complete.py`: Exécute l'orchestration complète avec tous les agents et capture la trace de conversation
- `analyse_trace_orchestration.py`: Analyse la trace de conversation générée et produit un rapport détaillé
- `run_complete_test_and_analysis.py`: Script principal qui orchestre l'exécution des deux scripts précédents

## Prérequis

- Python 3.8 ou supérieur
- Bibliothèques Python: asyncio, matplotlib, json, logging
- Accès aux agents d'analyse argumentative (PM, Informel, PL, Extract)
- Accès au texte du discours du Kremlin (ou autre texte complexe)

## Installation

1. Cloner le dépôt
2. Installer les dépendances:
   ```bash
   pip install -r requirements.txt
   ```

## Utilisation

### Exécution Complète

Pour exécuter l'ensemble du processus (test d'orchestration + analyse):

```bash
python run_complete_test_and_analysis.py
```

Ce script:
1. Exécute le test d'orchestration complète
2. Analyse la trace générée
3. Produit un rapport détaillé
4. Ouvre automatiquement le rapport

### Exécution Étape par Étape

#### 1. Test d'Orchestration

Pour exécuter uniquement le test d'orchestration:

```bash
python test_orchestration_complete.py
```

Ce script:
- Charge le texte du discours du Kremlin
- Initialise tous les agents (PM, Informel, PL, Extract)
- Exécute l'orchestration complète
- Capture la trace de conversation
- Sauvegarde la trace dans le répertoire `traces_orchestration_complete`

#### 2. Analyse de la Trace

Pour analyser une trace existante:

```bash
python analyse_trace_orchestration.py <chemin_vers_trace.json> --output-dir <répertoire_sortie>
```

Ce script:
- Charge la trace spécifiée
- Analyse les interactions entre agents
- Évalue la performance de l'agent Informel
- Évalue la qualité de l'analyse argumentative
- Génère des visualisations
- Produit un rapport détaillé dans le répertoire spécifié

## Structure des Traces

Les traces de conversation sont sauvegardées au format JSON avec la structure suivante:

```json
{
  "timestamp_debut": "2025-04-30T04:00:00.000000",
  "messages": [
    {
      "timestamp": "2025-04-30T04:00:01.000000",
      "agent": "ProjectManagerAgent",
      "type": "message",
      "content": "..."
    },
    ...
  ],
  "agents_utilises": ["ProjectManagerAgent", "InformalAnalysisAgent", "PropositionalLogicAgent", "ExtractAgent"],
  "timestamp_fin": "2025-04-30T04:10:00.000000",
  "duree_totale": 600.0,
  "statistiques": {
    "nombre_messages": 50,
    "messages_par_agent": {
      "ProjectManagerAgent": 15,
      "InformalAnalysisAgent": 12,
      "PropositionalLogicAgent": 10,
      "ExtractAgent": 13
    }
  }
}
```

## Structure du Rapport d'Analyse

Le rapport d'analyse est généré au format Markdown et contient:

1. **Résumé**: Vue d'ensemble du test et de ses résultats
2. **Configuration du Test**: Détails sur le texte analysé et les agents impliqués
3. **Résultats de l'Orchestration**: Performance temporelle et interactions entre agents
4. **Performance de l'Agent Informel**: Analyse détaillée des performances de l'agent Informel
5. **Analyse de la Qualité**: Évaluation de la qualité de l'analyse argumentative
6. **Impact des Améliorations**: Analyse de l'impact des améliorations apportées à l'agent Informel
7. **Recommandations**: Suggestions pour des améliorations futures
8. **Conclusion**: Synthèse des résultats et perspectives

## Visualisations

Le script d'analyse génère plusieurs visualisations:

1. **Séquence d'Agents**: Graphique montrant la séquence des interactions entre agents
2. **Messages par Agent**: Diagramme à barres du nombre de messages par agent

Ces visualisations sont sauvegardées dans le répertoire de sortie spécifié.

## Texte Utilisé

Le test utilise par défaut le discours du Kremlin du 21/02/2022, qui présente plusieurs caractéristiques intéressantes pour l'analyse argumentative:

- Texte long et complexe (plus de 46000 caractères)
- Arguments sophistiqués mêlant histoire, géopolitique et sécurité
- Structure argumentative non triviale
- Potentiels sophismes variés (appel à l'histoire, faux dilemme, etc.)

## Évaluation de la Qualité

L'évaluation de la qualité de l'analyse argumentative se base sur plusieurs critères:

1. **Identification des arguments**: Précision et pertinence des arguments identifiés
2. **Détection des sophismes**: Variété et pertinence des sophismes détectés
3. **Qualité des justifications**: Détail, citations et exemples dans les justifications
4. **Formalisation logique**: Qualité de la formalisation logique des arguments
5. **Cohérence globale**: Cohérence de l'analyse produite par l'ensemble des agents

## Résultats Attendus

L'exécution complète devrait produire:

1. Une trace de conversation au format JSON
2. Un rapport d'analyse au format Markdown
3. Des visualisations au format PNG

Ces fichiers permettent d'évaluer l'impact des améliorations apportées à l'agent Informel sur la qualité globale de l'analyse argumentative.

## Dépannage

### Problèmes Courants

1. **Erreur d'importation de modules**:
   - Vérifier que le répertoire parent est bien dans le PYTHONPATH
   - Vérifier que tous les modules requis sont installés

2. **Erreur de chargement du texte**:
   - Vérifier que le fichier cache du discours du Kremlin existe
   - Vérifier le chemin d'accès au fichier cache

3. **Erreur d'initialisation des agents**:
   - Vérifier que les fichiers de configuration des agents sont présents
   - Vérifier que le service LLM est correctement configuré

4. **Erreur d'analyse de la trace**:
   - Vérifier que la trace JSON est correctement formatée
   - Vérifier que matplotlib est installé pour les visualisations

## Contributeurs

- Équipe d'Intelligence Symbolique EPITA 2025

## Licence

Ce projet est sous licence MIT.