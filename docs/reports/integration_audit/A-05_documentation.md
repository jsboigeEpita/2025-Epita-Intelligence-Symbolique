# Audit A-05: Projet 2.1.4 — Documentation et Transfert de Connaissances

**Issue**: #750 (A-05) | **Epic**: #742 | **Date audit**: 2026-06-01
**Auditeur**: Claude Code @ myia-po-2023

---

## 0. Synthèse en 1 phrase

Le projet 2.1.4 (4 étudiants) n'a produit **aucun PR mergeable** — mais les 5 livrables spécifiés dans le sujet sont **entièrement couverts** par des artifacts créés par le professeur (735 fichiers docs/, 425+ commits).

**Verdict**: 🟢 **COUVERT par le professeur** — aucun gap d'intégration, pas de répertoire code à archiver. Score soutenance 30% = templates seuls (jamais remplis par les étudiants).

---

## 1. Cadrage R281c — 4 étapes

### 1.1 Localiser la version consolidée

Pas de répertoire code étudiant. Le sujet spécifiait 5 livrables transversaux:

| # | Livrable spécifié | Artifact consolidé | Auteur | LOC/Fichiers |
|---|-------------------|-------------------|--------|-------------|
| L1 | Portail documentation centralisé | `docs/guides/README.md` + `docs/architecture/README.md` | Professeur | 141 fichiers |
| L2 | Guides installation/développement | `docs/guides/` (74 fichiers) | Professeur | guide_developpeur, ENVIRONMENT_SETUP, GETTING_STARTED, etc. |
| L3 | Documentation architecture | `docs/architecture/` (67 fichiers) | Professeur | architecture_globale, INTEGRATION_STRATEGY, ORCHESTRATION_MODES |
| L4 | Plan coordination + comptes-rendus | `docs/projets/matrice_interdependances.md` + `SUIVI_PROJETS_ETUDIANTS.md` | Professeur | ~300 LOC |
| L5 | Base de connaissances / FAQ | `docs/projets/sujets/aide/FAQ_DEVELOPPEMENT.md` (664 LOC) | Professeur | 7 sections, code examples |

### 1.2 Préservation fonctionnelle

| Fonctionnalité | Préservée ? | Où | Notes |
|---------------|-------------|-----|-------|
| Portail unique | ✅ Complet | `docs/guides/` + `docs/architecture/` | 141 fichiers |
| Guides développement | ✅ Complet | `docs/guides/` | 74 fichiers couvrant installation, utilisation, contribution |
| Documentation architecture | ✅ Complet | `docs/architecture/` | 67 fichiers, INTEGRATION_STRATEGY, ORCHESTRATION_MODES |
| Tracking projets | ⚠️ Partiel | `SUIVI_PROJETS_ETUDIANTS.md` | Snapshot statique, pas de mise à jour continue |
| FAQ | ✅ Complet | `aide/FAQ_DEVELOPPEMENT.md` | 664 LOC, 7 sections, code examples |
| Standards documentation | ✅ Complet | `docs/guides/standards_documentation.md` | Template README 12 sections |
| Templates intégration | ✅ Complet | `aide/GUIDE_INTEGRATION_PROJETS.md` | 770 LOC avec exemples React/MCP |

**Score de préservation**: 7/7 fonctionnalités couvertes. Les étudiants n'ont rien livré, mais le professeur a tout produit.

### 1.3 Dilutions / Régressions

#### Dilution 1: SUIVI_PROJETS_ETUDIANTS.md est statique

**Localisation**: `docs/projets/SUIVI_PROJETS_ETUDIANTS.md`
**Impact**: LOW — Le fichier de suivi est un snapshot, pas un document vivant. Les pourcentages reflètent l'état à la soutenance, pas l'état actuel (plusieurs projets ont été intégrés depuis).
**Fix-intent**: Aucun — ce fichier est un artefact pédagogique, pas un outil de production.

#### Dilution 2: 5 répertoires "Futurs Sujets" jamais créés

**Localisation**: `docs/projets/sujets/aide/README.md` section "Futurs Sujets (A Venir)"
**Impact**: NONE — les 5 répertoires listés (detection-sophismes, frameworks-argumentation, analyse-semantique, visualisation-donnees, integration-llm) étaient des plans qui n'ont pas été poursuivis. Les sujets correspondants ont été traités via d'autres canaux.
**Fix-intent**: Aucun.

### 1.4 Statut — pas de répertoire racine

Ce projet n'a jamais eu de répertoire code. C'était un projet de coordination/documentation transversal. **Pas de décision d'archivage nécessaire**.

---

## 2. Analyse des templates `docs/projets/sujets/aide/`

| Fichier | LOC | Qualité | Rôle |
|---------|-----|---------|------|
| `README.md` | 176 | HIGH | Portail templates, usage instructions |
| `FAQ_DEVELOPPEMENT.md` | 664 | HIGH | 7 sections, API/engine/tests/deploy, code examples |
| `GUIDE_INTEGRATION_PROJETS.md` | 770 | HIGH | Intégration React/MCP complète avec exemples code |
| `PRESENTATION_KICKOFF.md` | 237 | MEDIUM | Overview architecture, ASCII diagrams. Référence Flask (obsolète → Starlette) |
| `interface-web/` | 21 fichiers | HIGH | Composants React, hooks, CSS, utils |

**Note**: `PRESENTATION_KICKOFF.md` référence encore "Flask" comme stack web — le projet a migré vers Starlette. C'est la seule inexactitude dans les templates.

---

## 3. Fix-intents

| # | Issue proposée | Priorité | Action |
|---|---------------|----------|--------|
| F1 | `fix(a-05): update PRESENTATION_KICKOFF.md Flask→Starlette reference` | **LOW** | Une seule ligne obsolète dans un template pédagogique |

**1 seul fix-intent LOW** — le seul artefact obsolète identifié.

---

## 4. Conclusion

Le projet 2.1.4 est un cas unique dans l'audit: **zéro livraison étudiante** (0 PR, 0 commit), mais **couverture fonctionnelle complète** des 5 livrables par le professeur. La documentation du projet est mature (735 fichiers, 425+ commits, intégration workflow via CLAUDE.md et standards_documentation.md).

Le score soutenance de 30% reflète fidèlement la contribution étudiante (templates seuls, jamais remplis). Le seul fix-intent est mineur (1 référence Flask obsolète dans un template).

**Pas d'action d'archivage nécessaire** — pas de répertoire code.
