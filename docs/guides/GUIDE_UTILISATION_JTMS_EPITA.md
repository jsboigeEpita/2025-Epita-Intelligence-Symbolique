# Guide d'Utilisation : Système d'Analyse d'Argumentation JTMS

**Version :** 1.0  
**Date :** 11 Juin 2025  
**Public Cible :** Étudiants et Enseignants d'EPITA

---

## 1. Introduction : Qu'allez-vous découvrir ?

Bienvenue dans le guide d'utilisation du système d'analyse d'argumentation d'EPITA. Cet outil unique combine un **Justification-based Truth Maintenance System (JTMS)** pour la logique symbolique et un **Grand Modèle de Langage (LLM)** pour la compréhension et la génération de texte.

Ce guide vous montrera comment :
- **Explorer** les concepts de croyances et de justifications logiques.
- **Interagir** avec des agents d'intelligence artificielle qui débattent.
- **Utiliser** l'IA pour analyser des arguments complexes.
- **Construire** vos propres scénarios d'investigation.

---

## 2. Démarrage Rapide : 5 minutes pour votre première analyse

L'interface web est le moyen le plus simple de commencer.

1.  **Accédez à l'application web :** Ouvrez votre navigateur et allez à l'URL fournie par votre enseignant.
2.  **Le Dashboard JTMS :** Vous verrez un panneau de contrôle. C'est ici que vous pouvez créer des croyances.
3.  **Créez votre première croyance :**
    - Dans le champ "Contenu de la croyance", tapez `Le soleil est une étoile`.
    - Cliquez sur `Ajouter Croyance`.
    - Observez le graphe : un nouveau nœud vert (IN) représentant votre croyance apparaît.
4.  **Créez une justification :**
    - Ajoutez deux nouvelles croyances : `Le soleil brille` et `Les étoiles brillent`.
    - Dans la section "Ajouter Justification", sélectionnez `Le soleil est une étoile` comme "Croyance justifiée".
    - Cochez `Le soleil brille` et `Les étoiles brillent` comme "Croyances justificatives".
    - Cliquez sur `Ajouter Justification`.
    - Le graphe se met à jour pour montrer les liens logiques que vous venez de créer.

Félicitations, vous avez créé votre premier réseau de croyances !

---

## 3. Scénarios d'Apprentissage Guidés

Ce système offre plusieurs niveaux d'interaction. Nous vous recommandons de suivre cette progression.

### Scénario 1 : Le Playground Logique (Interface Web)

**Objectif :** Maîtriser les concepts de base du JTMS.
1.  Passez 15-20 minutes à ajouter diverses croyances (vraies, fausses, contradictoires).
2.  Créez des justifications complexes liant plusieurs croyances.
3.  Utilisez la fonctionnalité "Contradiction" pour observer comment le JTMS propage les changements et résout les conflits logiques (les nœuds passent de vert `IN` à rouge `OUT`).
    - *Exemple :* Ajoutez la croyance `La Terre est plate`, puis marquez-la comme une `contradiction`. Observez quelles autres croyances deviennent `OUT`.

### Scénario 2 : L'Enquête de Sherlock & Watson (Démo en ligne de commande)

**Objectif :** Observer une collaboration entre deux agents IA pour résoudre un cas.
1.  Ouvrez un terminal dans le projet.
2.  Exécutez le script de démo :
    ```bash
    python -m demos.sherlock_watson_jtms_demo
    ```
3.  Suivez le dialogue entre Sherlock et Watson. Observez comment ils ajoutent des croyances à leurs JTMS respectifs en fonction des informations qu'ils découvrent.
4.  À la fin de l'exécution, examinez les fichiers de log générés dans le dossier `traces/` pour voir le "raisonnement" final de chaque agent.

### Scénario 3 : Le Débat sur Mesure (Plugin Semantic Kernel)

**Objectif :** Utiliser le plugin d'IA pour orchestrer votre propre débat.
Ce scénario plus avancé nécessite des bases en Python.
1.  Inspirez-vous des scripts dans le dossier `examples/`.
2.  Écrivez un script qui :
    - Importe le `JTMSSemanticKernelPlugin`.
    - Pose une question à un agent (ex: `Quelle est la meilleure approche pour lutter contre le changement climatique ?`).
    - Utilise les fonctions du plugin (`create_belief`, `add_justification`) pour analyser la réponse de l'agent et la structurer dans un JTMS.
    - Demande à un second agent de critiquer la réponse du premier.
    - Analyse la critique pour identifier les contradictions.

---

## 4. Foire Aux Questions (FAQ)

**Q : Que signifie un nœud vert (IN) ou rouge (OUT) ?**  
**R :** Un nœud vert (`IN`) représente une croyance actuellement considérée comme "vraie" dans l'état actuel du système. Un nœud rouge (`OUT`) est une croyance considérée comme "fausse", soit parce qu'elle est contredite, soit parce que ses justifications ne sont plus valides.

**Q : Puis-je sauvegarder mon réseau de croyances ?**  
**R :** Oui, le système gère des sessions. Tant que vous utilisez la même session (généralement via un cookie de navigateur), votre travail est conservé entre les visites.

**Q : Le LLM est-il toujours objectif ?**  
**R :** Non. Le LLM peut avoir des biais. Le but du JTMS est précisément d'apporter une couche de rigueur logique pour analyser et potentiellement corriger les affirmations générées par le LLM. C'est le cœur de l'approche "hybride" de ce système.

---

Ce guide n'est qu'un point de départ. L'outil est puissant et flexible. N'hésitez pas à expérimenter, à créer vos propres scénarios d'enquête et à repousser les limites du raisonnement machine.