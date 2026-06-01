#!/usr/bin/env python3
"""Helper script to write the C-07 audit report."""
import os

content = """# C-07: Audit Sujets — Section III-A Interfaces Utilisateurs

**Track**: C-07 #785 (Epic C #744)
**Date**: 2026-06-01
**Author**: Claude Code @ myia-po-2023:2025-Epita-Intelligence-Symbolique
**Scope**: 7 sujets (interfaces utilisateurs)

---

## Table préalable — Status des sujets

| Code | Sujet | Statut | Lien Epic A | Pipeline wiring |
|------|-------|--------|-------------|-----------------|
| 3.1.1 | Interface web analyse argumentative | 🟢 Traité | A-14 #775 | COMPLETE (React SPA 5815 LOC, 39 fichiers, 9 tabs) |
| 3.1.2 | Dashboard de monitoring | À auditer | — | NONE (pas de stack monitoring) |
| 3.1.3 | Éditeur visuel d'arguments | À auditer | — | NONE (LogicGraph = stub placeholder) |
| 3.1.4 | Visualisation graphes argumentation | À auditer | — | PARTIAL (D3.js force-directed, manque features avancées) |
| 3.1.5 | Interface mobile | 🟢 Traité | A-15 #776 | PARTIAL (React Native 6 écrans + 4 endpoints, bugs critiques) |
| 3.1.6 | Accessibilité | À auditer | — | NONE (0 attribut ARIA sur 65+ fichiers) |
| 3.1.7 | Collaboration temps réel | À auditer | — | PARTIAL (WebSocket streaming, pas co-édition) |

**Bilan** : 2 traités (🟢), 5 à auditer.

---

## Audit détaillé

### 🟢 3.1.1 Interface web pour l'analyse argumentative

**Statut** : Intégré partiellement (dual-serveur fragmenté)
**Epic A** : A-14 #775 — 🟡 dual-serveur (PR #839). Stack A-14 exécuté : FastAPI = API unique, Starlette = frontend-only proxy (PRs #850/#851/#852 mergés).
**Pipeline wiring** : React SPA (5815 LOC JS, 39 fichiers, 9 tabs). Components pour tous les agents (Sherlock, Watson, débat, gouvernance, qualité, Dung, sophismes). 3 fix-intents (#843/#844/#845 → mergés).

---

### 🟢 3.1.5 Interface mobile

**Statut** : Intégré partiellement (backend câblé, bugs critiques)
**Epic A** : A-15 #776 — 🟡 backend câblé, bugs (PR #840). React Native/Expo (36 fichiers, 6 écrans) + 4 endpoints FastAPI.
**Pipeline wiring** : 2 bugs runtime critiques (/chat TypeError HIGH, /validate type mismatch MEDIUM). 3 fix-intents (#846 HIGH, #847 MEDIUM, #848 MEDIUM).

---

### 3.1.2 Dashboard de monitoring

**Sujet** : Grafana/Tableau/Kibana, Plotly/ECharts, streaming metrics, observabilité opérationnelle.
**Pipeline** : **AUCUN WIRING** :
- Aucune référence à Grafana, Kibana, Plotly, ECharts
- `GovernanceDashboard.js` et `SpectacularDashboard.js` sont des composants applicatifs (affichage résultats analyse/gouvernance), pas des dashboards opérationnels
- Pas de métriques temps réel (latence, throughput, erreurs)
- Pas de streaming de données de monitoring

**Valeur potentielle** : LOW — un dashboard de monitoring opérationnel (Grafana-like) serait utile pour un déploiement multi-utilisateurs en production. Pour un pipeline de recherche mono-utilisateur, les structured logs + `PipelineMetrics` + trace entries suffisent.
**Classification** : ⚫ **Abandonné légitimement** — monitoring ops hors scope pipeline recherche.

---

### 3.1.3 Éditeur visuel d'arguments

**Sujet** : JointJS/mxGraph/GoJS, éditeur de graphes interactif, drag-and-drop, construction d'arguments visuelle.
**Pipeline** : **AUCUN WIRING** :
- `LogicGraph.js` = placeholder stub avec un SVG basique (cercle + labels)
- Commentaire explicite dans le code : *"In a real application, this would render a proper graph (e.g., using D3, vis.js, or a library)"*
- Pas de JointJS, mxGraph, GoJS
- Pas de drag-and-drop, pas d'édition interactive

**Valeur potentielle** : MEDIUM — un éditeur visuel d'arguments permettrait aux utilisateurs de construire des frameworks de Dung interactivement (ajouter/supprimer des arguments et attaques visuellement) au lieu de passer par JSON/texte. Cas d'usage concret :
- Construire un AF de Dung pour tester des sémantiques
- Visualiser l'impact d'une attaque sur les extensions
- Prototypage pédagogique (étudiants construisant des AF)

Cependant : c'est un **enhancement UI**, pas un gap pipeline. Le backend expose déjà `build_framework` MCP tool + `analyze_dung_framework` API. L'éditeur visuel serait un frontend-only.

**Classification** : 🟠 **Angle mort utile** — complément naturel du DungGraph existant. Backend câblé, seul le frontend interactif manque. Priorité MEDIUM ( pédagogique, pas pipeline-critical).

---

### 3.1.4 Visualisation avancée de graphes d'argumentation

**Sujet** : Sigma.js/vis.js/Cytoscape, layouts avancés, visualisation cognitive, multi-layer.
**Pipeline** : **PARTIELLEMENT COUVERT** :
- **D3.js force-directed graph** : `DungGraph.js` + `useDungGraphRenderer.js` (force simulation, drag, zoom/pan 0.3x-3x, tooltips, sélection avec detail panel, extension color coding : grounded=green, preferred=blue, stable=yellow)
- **Styling** : `DungGraph.css` (dark theme, node/edge styles)
- **Tests** : `DungGraph.test.js`

Manquent : pas de Sigma.js/vis.js/Cytoscape, pas de sélection de layout algorithm, pas d'édition d'edges, pas de multi-layer graph (Dung + ASPIC stacked), pas d'export.

**Valeur potentielle** : LOW — D3.js force-directed couvre le use case principal (visualiser un AF de Dung avec extensions). Les features avancées (layout custom, multi-layer, export) sont des **enhancements** pour un cas d'usage de publication/recherche.
**Classification** : 🟡 **Partiellement couvert** — D3.js fonctionnel, features avancées manquantes mais non critiques.

---

### 3.1.6 Accessibilité

**Sujet** : WCAG 2.1 AA, ARIA, axe-core/pa11y, lecteurs d'écran, navigation clavier.
**Pipeline** : **AUCUN WIRING** :
- **0 attribut ARIA** sur l'ensemble des 65+ fichiers source React
- Aucun `role=`, `aria-*`, ou `tabindex` dans aucun composant
- Le DungGraph SVG est totalement inaccessible au clavier
- Les formulaires (ArgumentAnalyzer, FallacyDetector, FrameworkBuilder, ValidationForm, DebateArena) n'ont pas de labels associés
- Pas d'axe-core/pa11y dans les dépendances

**Valeur potentielle** : MEDIUM — l'accessibilité est un requirement légal dans certains contextes (éducation publique, gouvernement). Pour EPITA (école privée), c'est un **nice-to-have** pédagogique. Cependant, l'absence totale d'ARIA est un signal de dette technique UI.

**Classification** : 🟠 **Angle mort utile** — non bloquant pipeline, mais important pour la qualité pédagogique du frontend. MEDIUM (pas HIGH car le système est un outil de recherche, pas un service public).

---

### 3.1.7 Système de collaboration en temps réel

**Sujet** : Socket.io/Yjs/ShareDB, awareness, co-édition simultanée, résolution de conflits.
**Pipeline** : **PARTIELLEMENT COUVERT** :
- **Frontend** : `useWebSocket.js` — hook React WebSocket (3 channels : analysis, debate, deliberation), auto-reconnect (3s), ping/pong keepalive (30s), message buffering
- **Backend** : `api/websocket_routes.py` — 3 endpoints FastAPI WebSocket (`/ws/analysis/{session_id}`, `/ws/debate/{session_id}`, `/ws/deliberation/{session_id}`), `WebSocketManager`
- **Wiring** : `ws_router` monté dans `api/main.py`

Manquent : pas de co-édition (Yjs/ShareDB/CRDT), pas d'awareness (cursor presence, typing indicators), pas de résolution de conflits. Le WebSocket est **streaming-oriented** (push serveur→client) pas **collaborative** (bidirectional state sync).

**Valeur potentielle** : LOW — la co-édition temps réel est un cas d'usage **multi-utilisateurs** qui ne s'applique pas au pipeline mono-utilisateur actuel. Le streaming WebSocket existant couvre le besoin pipeline (push résultats d'analyse en temps réel).
**Classification** : 🟡 **Partiellement couvert** — WebSocket streaming complet, co-édition hors scope (mono-utilisateur).

---

## Récapitulatif

| Code | Sujet | Classification | Pipeline wiring | Valeur potentielle |
|------|-------|----------------|-----------------|-------------------|
| 3.1.1 | Interface web | 🟢 Traité (A-14) | COMPLETE (React SPA) | — |
| 3.1.5 | Interface mobile | 🟢 Traité (A-15, partiel) | PARTIAL (bugs critiques) | — |
| 3.1.2 | Dashboard monitoring | ⚫ Abandonné | NONE | LOW |
| 3.1.3 | Éditeur visuel arguments | 🟠 Angle mort utile | NONE (stub) | MEDIUM |
| 3.1.4 | Visualisation graphes | 🟡 Partiel | D3.js fonctionnel | LOW |
| 3.1.6 | Accessibilité | 🟠 Angle mort utile | NONE (0 ARIA) | MEDIUM |
| 3.1.7 | Collaboration temps réel | 🟡 Partiel | WebSocket streaming | LOW |

### Décompte

| Classification | Count | Sujets |
|----------------|-------|--------|
| 🟢 Traité | 2 | 3.1.1, 3.1.5 |
| 🟠 Angle mort utile | 2 | 3.1.3 (éditeur visuel), 3.1.6 (accessibilité) |
| 🟡 Partiel | 2 | 3.1.4 (D3.js), 3.1.7 (WebSocket streaming) |
| ⚫ Abandonné | 1 | 3.1.2 (monitoring ops) |

**Angles morts utiles** : 2 sujets MEDIUM — l'éditeur visuel d'arguments (3.1.3) et l'accessibilité (3.1.6). Les deux sont des **enhancements frontend** (pas pipeline-critical) mais amélioreraient significativement la qualité pédagogique.

---

## Issues enhancement proposées

| # | Issue proposée | Priorité | Action |
|---|----------------|----------|--------|
| E1 | `enhancement(c-07): add interactive argument graph editor (DungFramework builder)` | **MEDIUM** | Transformer le `LogicGraph.js` placeholder en éditeur interactif : drag-and-drop nodes/edges, ajout/suppression d'arguments et attaques, visualisation des extensions en temps réel. Backend déjà câblé (`build_framework` MCP tool + `analyze_dung_framework` API). Frontend-only. |
| E2 | `enhancement(c-07): add basic ARIA accessibility to React frontend` | **MEDIUM** | Ajouter aria-labels aux formulaires, role attributes aux composants interactifs, tabindex au DungGraph SVG, axe-core dans les tests. Minimum viable : WCAG 2.1 A (pas AA complet). |

### À valider par l'utilisateur

- RAS — audit read-only. Les 2 angles morts (éditeur visuel + accessibilité) sont des enhancements frontend MEDIUM, pas pipeline-critical. Aucun arbitrage architectural en suspens.
"""

path = os.path.join('docs', 'reports', 'subjects_audit', 'C-07_interfaces_utilisateurs.md')
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print(f'Written {len(content)} chars to {path}')
