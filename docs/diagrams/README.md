# Diagrammes du Système d'Analyse Argumentative

Ce dossier contient les diagrammes illustrant l'architecture, les flux de données et les interactions entre les composants du système d'analyse argumentative.

## Table des Matières

- [Diagrammes du Système d'Analyse Argumentative](#diagrammes-du-système-danalyse-argumentative)
  - [Table des Matières](#table-des-matières)
  - [Vue d'ensemble](#vue-densemble)
  - [Liste des diagrammes](#liste-des-diagrammes)
    - [1. Flux de Données](#1-flux-de-données)
    - [2. Interactions entre Composants](#2-interactions-entre-composants)
  - [Comment visualiser les diagrammes](#comment-visualiser-les-diagrammes)
    - [Options de visualisation :](#options-de-visualisation-)
  - [Comment contribuer](#comment-contribuer)
  - [Description détaillée](#description-détaillée)
    - [Bonnes pratiques pour les diagrammes](#bonnes-pratiques-pour-les-diagrammes)
  - [Ressources associées](#ressources-associées)

## Vue d'ensemble

Les diagrammes fournis dans ce dossier ont pour objectif de faciliter la compréhension du système d'analyse argumentative en visualisant :
- Les flux de données entre les différents composants
- Les interactions et dépendances entre les modules
- L'architecture globale du système
- Les processus d'analyse et de traitement

Ces diagrammes sont particulièrement utiles pour :
- Les nouveaux développeurs qui rejoignent le projet
- La documentation technique du système
- La planification de nouvelles fonctionnalités
- L'identification de goulots d'étranglement potentiels

## Liste des diagrammes

### 1. [Flux de Données](flux_donnees.md)

Ce diagramme illustre comment les données circulent à travers le système, depuis l'entrée du texte jusqu'à la génération des rapports d'analyse. Il montre les différentes étapes de traitement et les transformations appliquées aux données.

**Cas d'utilisation** : Comprendre le parcours des données et les transformations qu'elles subissent.

### 2. [Interactions entre Composants](interactions_composants.md)

Ce diagramme montre comment les différents composants du système interagissent entre eux, mettant en évidence l'architecture hiérarchique à trois niveaux (stratégique, tactique, opérationnel) et les services partagés.

**Cas d'utilisation** : Comprendre les dépendances entre composants et l'architecture globale du système.

## Comment visualiser les diagrammes

Les diagrammes sont créés en utilisant la syntaxe [Mermaid](https://mermaid-js.github.io/), qui permet de définir des diagrammes en texte et de les rendre visuellement.

### Options de visualisation :

1. **GitHub** : Les diagrammes Mermaid sont automatiquement rendus sur GitHub lorsque vous visualisez les fichiers .md.

2. **VSCode** : Installez l'extension "Mermaid Preview" pour visualiser les diagrammes directement dans VSCode.

3. **Mermaid Live Editor** : Vous pouvez copier le code Mermaid dans l'[éditeur en ligne Mermaid](https://mermaid-js.github.io/mermaid-live-editor/) pour le visualiser et l'éditer.

4. **Navigateur** : Utilisez des extensions comme "Markdown Viewer" pour Chrome ou Firefox pour visualiser les fichiers Markdown avec rendu Mermaid.

## Comment contribuer

Pour ajouter ou modifier des diagrammes :

1. **Créez un nouveau fichier** avec l'extension `.md` pour chaque nouveau diagramme.

2. **Suivez la structure** :
   ```markdown
   # Titre du Diagramme
   
   Description brève du diagramme.
   
   ```mermaid
   // Votre code Mermaid ici
   ```
   
   ## Description détaillée
   
   Explication des éléments du diagramme...
   ```

3. **Mettez à jour ce README.md** pour référencer votre nouveau diagramme.

4. **Testez le rendu** de votre diagramme avant de soumettre votre contribution.

### Bonnes pratiques pour les diagrammes

- Gardez les diagrammes simples et lisibles
- Utilisez des couleurs cohérentes pour les différents types de composants
- Ajoutez des descriptions détaillées pour expliquer les éléments complexes
- Privilégiez plusieurs diagrammes simples plutôt qu'un seul diagramme complexe

## Ressources associées

- [Documentation Mermaid](https://mermaid-js.github.io/mermaid/#/)
- [Architecture du système](../architecture/architecture_globale.md)
- [Documentation des composants](../composants/README.md)
- [Guide du développeur](../guides/guide_developpeur.md)