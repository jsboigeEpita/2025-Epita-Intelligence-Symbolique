# Plan d'Analyse Ciblée des Commits Post-Refactorisation

**Date :** 22/06/2025
**Auteur :** Roo, Architecte

## 1. Objectif de l'Analyse

Suite à la phase intensive de refactorisation décrite dans le `diagnostic_report.md`, cette analyse vise à évaluer l'état actuel du système de manière ciblée. Nous ne cherchons pas à refaire un diagnostic global, mais à répondre à des questions précises pour guider les prochaines actions :

*   **Validation :** Valider que les corrections apportées n'ont pas introduit de régressions ou d'effets de bord inattendus dans les zones critiques.
*   **Prévention :** S'assurer que des dettes techniques connues et critiques (ex: `KMP_DUPLICATE_LIB_OK=TRUE`) n'ont pas été réintroduites. Identifier l'émergence de nouveaux "signaux faibles" de dette technique.
*   **Prospective :** Détecter les prochains chantiers de refactorisation ou de stabilisation qui semblent logiques au vu de l'évolution récente du code.

## 2. Périmètre de l'Analyse

L'analyse portera sur les **50 derniers commits** à partir du `HEAD` de la branche principale. Ce périmètre est suffisant pour couvrir la période post-stabilisation sans être pollué par le bruit des refactorisations massives précédentes.

## 3. Méthodologie

Actuellement, il n'existe pas de script dédié à l'analyse de commits. Nous proposons donc la création d'un nouvel outil pour automatiser ce processus.

### 3.1. Création du Script `analyze_commits.ps1`

Un script PowerShell nommé `analyze_commits.ps1` sera créé dans le répertoire `scripts/reporting/`. Ce script aura pour responsabilité de :

1.  Prendre en paramètre le nombre de commits à analyser (par défaut : 50).
2.  Itérer sur chaque commit du périmètre défini.
3.  Pour chaque commit, extraire :
    *   Le hash du commit.
    *   Le message du commit.
    *   La liste des fichiers modifiés.
    *   Le `diff` complet des modifications.
4.  Analyser ces informations à la recherche de patterns spécifiques (détaillés ci-dessous).
5.  Générer un rapport synthétique en sortie (format Markdown ou texte).

### 3.2. Patterns et Mots-clés à Surveiller

Le script recherchera activement les éléments suivants, qui sont directement dérivés des risques identifiés dans le rapport de diagnostic :

*   **Réapparition de dettes techniques connues :**
    *   Toute mention de `KMP_DUPLICATE_LIB_OK=TRUE` dans les diffs.
    *   Toute modification du fichier `environment.yml`, en particulier sur les versions de `python` ou des bibliothèques critiques.
    *   Toute modification concernant la version de `typescript` dans les `package.json` ou `package-lock.json`.

*   **Points de fragilité de l'architecture :**
    *   Toute modification sur le script `activate_project_env.ps1`.
    *   Toute modification touchant au mécanisme de communication de l'URL du frontend pour les tests E2E (ex: `logs/frontend_url.txt`).
    *   Toute modification dans les fichiers de configuration des tests E2E (`playwright.config.js`, `run_functional_tests.ps1`).

*   **Indicateurs d'instabilité potentielle :**
    *   **Mots-clés dans les messages de commit :** `fix`, `bug`, `revert`, `hotfix`, `crash`, `error`, `instability`, `regression`.
    *   **Mots-clés dans les diffs :** Surveillance des modifications sur les zones récemment refactorisées : `agent`, `orchestrator`, `uvicorn`, `ASGI`, `JVM`, `semantic-kernel`.

## 4. Livrables Attendus

Le livrable principal sera un **rapport de synthèse** généré par le script. Ce rapport mettra en évidence, pour chaque commit suspect, le hash, le message et la raison pour laquelle il a été signalé (ex: "Modification de environment.yml").

Ce rapport servira de base pour une discussion technique afin de prioriser les éventuelles actions correctives ou les prochaines étapes de refactorisation.