# Chronologie de la fonctionnalité MCP

Ce document retrace l'historique Git des fichiers clés liés au serveur MCP pour comprendre son introduction et son évolution dans le projet.

---

## 1. Fiche Sujet

**Fichier :** [`docs/projets/sujets/2.5.3_Developpement_Serveur_MCP_Analyse_Argumentative.md`](docs/projets/sujets/2.5.3_Developpement_Serveur_MCP_Analyse_Argumentative.md)

| Date | Commit | Message | Analyse |
|---|---|---|---|
| 2025-05-27 | `0ff106d` | `feat: Ajout des guides pédagogiques détaillés...` | **Création du document.** |
| 2025-05-29 | `1037e9d` | `MAJ et création des fiches sujets...` | **Mise à jour majeure** du contenu. |

---

## 2. Code Source du Serveur

**Fichier :** [`services/mcp_server/main.py`](services/mcp_server/main.py)

| Date | Commit | Message | Analyse |
|---|---|---|---|
| 2025-06-19 | `7d48c91` | `feat: Integrate MCP server from student PR` | **Création du fichier** à partir d'une Pull Request étudiante. |
| 2025-06-26 | `2df1259` | `feat(mcp): rework to use new project architecture` | **Modification majeure** pour adapter le serveur à la nouvelle architecture. |
| 2025-06-27 | `857be18` | `improve all endpoints from API` | **Modification majeure** avec amélioration des points de terminaison. |

---

## 3. README du Serveur

**Fichier :** [`services/mcp_server/README.md`](services/mcp_server/README.md)

| Date | Commit | Message | Analyse |
|---|---|---|---|
| 2025-05-30 | `6433455` | `readme base` | **Création du fichier.** |
| 2025-06-19 | `7d48c91` | `feat: Integrate MCP server from student PR` | **Modification majeure** lors de l'intégration de la PR. |
| 2025-06-26 | `bc7e20c` | `feat(mcp): updated readme` | **Modification majeure** avec mise à jour du contenu. |

---

## 4. Tests d'Intégration

**Fichier :** [`tests/integration/services/test_mcp_server_integration.py`](tests/integration/services/test_mcp_server_integration.py)

| Date | Commit | Message | Analyse |
|---|---|---|---|
| 2025-06-19 | `7d48c91` | `feat: Integrate MCP server from student PR` | **Création des tests** en même temps que le code source. |
| 2025-06-24 | `b6aeba3` | `fix(tests): Resolve multiple test failures...` | **Modification majeure** pour corriger les tests défaillants. |
| 2025-07-16 | `31044dc` | `refactor(tests): Convert async tests to sync...` | **Modification majeure** avec un refactoring des tests asynchrones. |

---

## 5. Tests Unitaires

**Fichier :** [`tests/unit/services/test_mcp_server.py`](tests/unit/services/test_mcp_server.py)

| Date | Commit | Message | Analyse |
|---|---|---|---|
| 2025-06-19 | `7d48c91` | `feat: Integrate MCP server from student PR` | **Création des tests** en même temps que le code source. |
| 2025-06-29 | `93aeec5` | `fix(tests): Réparation complète de la suite de tests...` | **Modification majeure** pour réparer la suite de tests. |
| 2025-06-29 | `64ff3dc` | `feat: Intégration des corrections et améliorations critiques...` | **Modification majeure** apportant des améliorations critiques. |

---
## 6. Analyse et Hypothèse

### Analyse de la chronologie

1.  **Introduction (mi-juin 2025) :** La fonctionnalité MCP a été intégrée le **19 juin 2025** via le commit `7d48c91`. Le message explicite (`feat: Integrate MCP server from student PR`) indique que le code provient d'une Pull Request externe (probablement d'un fork étudiant).

2.  **Origine externe :** Le code a été développé dans un environnement distinct. Il est courant dans ce contexte que la gestion des dépendances soit différente (ex: chemins locaux, paquets non publiés).

3.  **Refactoring post-intégration (fin juin 2025) :** Une série de modifications majeures a suivi rapidement l'intégration, notamment un `rework to use new project architecture` (`2df1259`). Cette phase de réorganisation est un moment critique où des liens vers des dépendances locales peuvent être cassés.

### Hypothèse sur la dépendance manquante (`mcp`/`FastMCP`)

L'hypothèse la plus probable est que la dépendance `mcp` (ou `FastMCP`) était une **librairie locale** présente dans le projet de l'étudiant.

Lors de l'intégration de la Pull Request, ce répertoire contenant la librairie a été **omis ou mal référencé**. L'absence de cette dépendance dans les fichiers de configuration centraux (comme `requirements.txt` ou `pyproject.toml`) suggère fortement qu'elle n'a jamais été traitée comme un paquet standard (PyPI), mais plutôt comme un module local.

La cause racine est donc probablement une **erreur humaine lors du merge de la PR**, où seule une partie du code source a été transférée, laissant la dépendance critique orpheline.