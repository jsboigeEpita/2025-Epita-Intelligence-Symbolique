# Audit C-07: Section III-A Interfaces Utilisateurs (7 sujets)

**Issue**: #785 (C-07) | **Epic**: #744 | **Date audit**: 2026-05-31

## Préambule — Table de correspondance

| Code sujet | Statut | Lien Epic A si traité |
|------------|--------|-----------------------|
| 3.1.1 Interface web | 🟢 Treated | #775 (A-14) |
| 3.1.2 Dashboard monitoring | 🟠 Angle mort partiel | — |
| 3.1.3 Éditeur visuel arguments | 🔴 Angle mort | — |
| 3.1.4 Visualisation graphes | 🟠 Angle mort partiel (strong code) | — |
| 3.1.5 Interface mobile | 🟢 Treated | #776 (A-15) |
| 3.1.6 Accessibilité | 🔴 Angle mort | — |
| 3.1.7 Collaboration temps réel | 🟠 Angle mort partiel | — |

## Résultats détaillés

### 🟢 TRAITÉS (2)

**3.1.1 Interface web** — Student project (erwin.rodrigues, robin.de-bastos, score 65%). Code: `interface_web/app.py` (Starlette ASGI), React frontend `services/web_api/interface-web-argumentative/`. Cross-ref → Epic A #775 (A-14).

**3.1.5 Interface mobile** — Student project (3 students, score 70%). Code: `3.1.5_Interface_Mobile/` (React Native + Expo), `api/mobile_endpoints.py` (4 endpoints). Cross-ref → Epic A #776 (A-15).

### 🟠 ANGLE MORTS PARTIELS (3)

**3.1.4 Visualisation graphes** — Strong scattered code:
- `services/web_api/.../spectacular/DungGraph.js` + `useDungGraphRenderer.js` — interactive D3.js force-directed graph
- `argumentation_analysis/visualization/dung_viz.py` + `reporting/graph_generator.py` — backend graph generation
- `1.4.1-JTMS/jtms_graph.html` + `lib/vis-9.1.2/vis-network.min.js` — vis.js for JTMS belief graphs
- **Assessment**: Substantial visualization code exists but fragmented across frontend (D3), JTMS (vis.js), Python backends (networkx/matplotlib). Never scoped as a tracked subject. **Value: HIGH** for consolidation.

**3.1.2 Dashboard monitoring** — `interface_web/templates/dashboard.html` (529 LOC) exists but is a **feature-launcher dashboard** (navigation to analysis/debate/logic capabilities + API status heartbeat), NOT operational monitoring. No Grafana/Prometheus, no agent-health telemetry, no latency/cost/token dashboards. **Value: MEDIUM** — operational utility given tight API quota.

**3.1.7 Collaboration temps réel** — WebSocket infra exists: `interface_web/services/jtms_websocket.py` (448 LOC, live JTMS belief-network updates), `api/websocket_routes.py` (FastAPI streaming). But **multi-user collaborative editing** (presence, shared cursors, conflict resolution, OT/CRDT) does not exist. **Value: MEDIUM-LOW** for a research project.

### 🔴 ANGLE MORTS (2)

**3.1.3 Éditeur visuel d'arguments** — Only `FrameworkBuilder.js` exists (form-based argument builder — add by text field, declare attacks via dropdowns). No drag-and-drop / canvas-based node-edge editor. DungGraph is render-only (D3 force layout, no editing). **Value: MEDIUM-LOW** for research focus.

**3.1.6 Accessibilité (WCAG)** — Near-zero implementation. Only ~16 incidental `aria-` hits in templates (Bootstrap spinner `role="status"`). No WCAG audit, no keyboard navigation, no screen-reader support, no color-contrast system. **Value: MEDIUM** — well-bounded future subject.

## Synthèse C-07

- **2/7 🟢 Treated** (student projects)
- **3/7 🟠 Partial** (3.1.4 visualization has strongest scattered code, 3.1.2 dashboard is wrong type, 3.1.7 WebSocket infra only)
- **2/7 🔴 Angle mort** (visual editor, accessibility)

**Key finding**: 3.1.4 (Visualization) is the highest-value finding of the packet — substantial D3/vis.js/networkx code exists but was never scoped as a subject. Recommend consolidation rather than treating as a true gap.

## Fichiers sources
- `interface_web/templates/dashboard.html` (3.1.2 — launcher dashboard)
- `interface_web/services/jtms_websocket.py` (3.1.7 — WebSocket infra)
- `services/web_api/.../spectacular/DungGraph.js`, `useDungGraphRenderer.js` (3.1.4 — D3 viz)
- `services/web_api/.../components/FrameworkBuilder.js` (3.1.3 — form-based builder)
- `argumentation_analysis/visualization/dung_viz.py`, `reporting/graph_generator.py` (3.1.4 — backend viz)
- `1.4.1-JTMS/jtms_graph.html` + `lib/vis-9.1.2/` (3.1.4 — vis.js)
- `3.1.5_Interface_Mobile/` + `api/mobile_endpoints.py` (3.1.5)
