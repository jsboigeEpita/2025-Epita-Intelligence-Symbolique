# Générateur de Rapports de Narration Stratégique

Ce document décrit le fonctionnement et l'utilisation du script d'automatisation de la narration, un outil conçu pour générer des rapports stratégiques à partir de l'historique des commits Git.

## 🎯 Objectif du Script

L'objectif principal de ce script est de générer automatiquement des rapports de narration stratégique qui synthétisent l'évolution d'un projet. En analysant les commits Git, il produit des analyses cohérentes qui aident à comprendre la dynamique de développement et les décisions techniques sur le long terme.

## ✨ Fonctionnalités Clés

### Ton et Style

Le script est configuré pour produire des analyses au ton **professionnel et stratégique**. Il ne se contente pas de lister des changements, mais les interprète pour en extraire des insights pertinents pour une revue de projet.

### 🧠 Grounding Historique et Continuité Narrative

Pour garantir une narration fluide et cohérente, le script utilise un mécanisme de **chaînage de contexte**. Chaque nouveau chapitre est généré en se basant sur le contenu du rapport le plus récent. Cette approche assure que chaque nouvelle analyse s'inscrit dans la continuité de la précédente, créant ainsi un récit évolutif et non une série de rapports déconnectés.

### 📜 Contexte Stratégique : Le Préambule "Guerre des Agents"

Afin de guider l'IA dans son analyse, le script injecte un préambule thématique nommé `"Guerre des Agents"`. Ce contexte initial standardisé aide à cadrer l'analyse sous un angle stratégique, assurant une plus grande pertinence et une meilleure qualité des rapports générés.

### 📚 Structure des Rapports

Le script traite l'historique des commits par lots pour créer des rapports structurés :

1.  **Rapports Globaux :** Un rapport global est généré pour chaque bloc de **200 commits**.
2.  **Chapitres :** Chaque rapport global est lui-même décomposé en chapitres, chacun analysant **20 commits**.

Cette structure modulaire permet de générer des analyses détaillées tout en conservant une vue d'ensemble sur des périodes de développement plus longues.

## 🚀 Usage

Le script est conçu pour être simple à utiliser. Pour le lancer, exécutez la commande suivante depuis la racine du projet :

```bash
python scripts/narrative_reporting/run_narrative_automation.py
```

Le script gère automatiquement l'état de la narration : il identifie le dernier commit traité et enchaîne avec les suivants, assurant ainsi une mise à jour continue des rapports sans intervention manuelle.

## ⚙️ Configuration

La configuration principale (comme les chemins de sortie et les paramètres du modèle) est gérée en interne par le script et n'exige généralement pas de modification manuelle pour une utilisation standard.