# Audit C-08: Section III-B/C Applications + Lutte Désinformation + RÉCAP GLOBAL (14 sujets)

**Issue**: #786 (C-08) | **Epic**: #744 | **Date audit**: 2026-05-31

## Préambule — Table de correspondance

| Code sujet | Statut | Lien Epic A si traité |
|------------|--------|-----------------------|
| 3.2.1 Système débat IA | 🟢 Largement couvert | #778 (A-17) |
| 3.2.2 Plateforme éducation | 🟠 Angle mort utile | — |
| 3.2.3 Aide décision | 🟠 Angle mort utile | — |
| 3.2.4 Plateforme collaborative | ⚫ Abandonné légitimement | — |
| 3.2.5 Assistant écriture | 🟠 Angle mort utile | — |
| 3.2.6 Analyse débats politiques | 🟠 Angle mort utile (HIGH) | — |
| 3.2.7 Délibération citoyenne | 🟢 Traité (DemocraTech) | — |
| 3.2.8 Plateforme éducative avancée | 🔵 Doublon de 3.2.2 | — |
| 3.2.9 Applications commerciales | ⚫ Abandonné légitimement | — |
| 3.3.1 Fact-checking | 🔵 Doublon de 2.4.4 | — |
| 3.3.2 Sophismes focus | 🔵 Doublon de 2.3.2 | #753 (A-07) |
| 3.3.3 Protection IA | 🔵 Doublon de 2.5.6 | #774 (A-13) |
| 3.3.4 ArgumentuMind | ⚫ Abandonné légitimement | — |
| 3.3.5 ArgumentuShield | ⚫ Abandonné légitimement | — |

## Résultats détaillés

### 🟢 TRAITÉS (2)

**3.2.1 Système de débat assisté par IA** — Extensive existing coverage: `agents/core/debate/debate_agent.py` (7 personalities, Walton-Krabbe protocols), `workflows/debate_tournament.py` (6-phase adversarial tournament), `workflows/formal_debate.py` (ASPIC+ structured dialogue), `orchestration/collaborative_debate.py`. The debate *engine* is done; the missing piece is the interactive user-facing app.

**3.2.7 Plateforme de délibération citoyenne** — Substantially covered by DemocraTech umbrella (`workflows/democratech.py` — 9-phase pipeline: transcription → quality → fallacy → counter-args → debate → belief-tracking → vote → indexing → quality recheck). `DEMOCRATECH_UNIFIED_ANALYSIS.md` maps sectoral orchestrators. Deliberation engine + consensus mechanisms integrated.

### 🟠 ANGLE MORTS UTILES (4)

**3.2.6 Analyse de débats politiques** — ⭐ MOST CODE-READY gap. Existing: `agents/core/political/stakes_extractor.py` (stakes/stakeholders/rhetorical register), DemocraTech `political_monitoring_unified.py`, fallacy detection, `workflows/fact_check_pipeline.py`. Missing: real-time media monitoring, coordinated-campaign detection, propagation analysis. **Value: HIGH**.

**3.2.5 Assistant d'écriture argumentative** — Strong backend: counter-argument generation (5 strategies), fallacy detection, quality evaluation (9 virtues). Missing: writing-assistant UX (inline suggestions, reformulation). **Value: MEDIUM-HIGH**.

**3.2.2 Plateforme d'éducation** — Partial: `project_core/.../educational_showcase_system.py` (pedagogical demo), EPITA demos. Missing: interactive tutorials, exercises, gamification. **Value: MEDIUM-HIGH**.

**3.2.3 Système d'aide à la décision** — Partial: weighted frameworks + governance voting (7 methods). Missing: MCDM (multi-criteria decision making), weighted criteria, trade-off visualization. **Value: MEDIUM**.

### ⚫ ABANDONNÉS LÉGITIMENT (4)

**3.2.4 Plateforme collaborative** — Pure CSCW/frontend concerns (real-time collab, version control, document annotation). Negligible symbolic-AI content.

**3.2.9 Applications commerciales** — Business-modeling/market-study subject pointing to `modeles_affaires_ia.md`. Not a software deliverable.

**3.3.4 ArgumentuMind** — Calls for computational cognitive models, bias modeling, human-reasoning simulation — research-grade ⭐⭐⭐⭐⭐ far beyond student deliverable scope.

**3.3.5 ArgumentuShield** — Depends on 3.3.4 + educational platform + 2.5.6 — stacked ⭐⭐⭐⭐⭐ research subject.

### 🔵 DOUBLONS (4)

**3.3.1** = 2.4.4 (fact-checking) | **3.3.2** = 2.3.2 (sophismes) | **3.3.3** = 2.5.6 (protection IA) | **3.2.8** ≈ 3.2.2 (éducation, near-identical)

---

# RÉCAP GLOBAL — Epic C #744 (8 packets, ~72 sujets)

## Compte par classification

| Classification | Count | Pourcentage |
|---------------|-------|-------------|
| 🟢 Traité / De-facto couvert | ~26 | 36% |
| 🟡 Partiel (code exists / doc gap) | ~10 | 14% |
| 🟠 Angle mort utile | ~12 | 17% |
| ⚫ Abandonné légitimement | ~14 | 19% |
| 🔵 Doublon | ~10 | 14% |

## Top 5 angles morts les plus précieux à intégrer

1. **1.4.4 Mesures d'incohérence** (C-03) — HIGH value, LOW effort. Tweety `logics.pl.analysis` on classpath, focused handler extension. Best ROI.
2. **3.2.6 Analyse de débats politiques** (C-08) — HIGH value. `stakes_extractor.py` + DemocraTech + fact-check pipeline already exist. Most code-ready gap.
3. **2.4.4 Fact-checking** (C-06) — RICHEST undocumented capability. Full pipeline exists but no sujet. Warrants Epic A audit issue.
4. **1.2.5 VAF** (C-02) — Only genuine gap in argumentation frameworks. Native Python engine feasible. Bridges symbolic AF with value extraction.
5. **3.1.4 Visualisation graphes** (C-07) — Strong scattered code (D3/vis.js/networkx). Highest-value consolidation target.

## Fichiers sources
- `argumentation_analysis/agents/core/debate/debate_agent.py`
- `argumentation_analysis/workflows/debate_tournament.py`, `democratech.py`, `fact_check_pipeline.py`
- `argumentation_analysis/agents/core/political/stakes_extractor.py`
- `argumentation_analysis/agents/core/governance/social_choice.py`
- `project_core/rhetorical_analysis_from_scripts/educational_showcase_system.py`
- `docs/projets/experience_utilisateur.md` (§3.2–3.3 catalogue source)
- `docs/projets/SUIVI_PROJETS_ETUDIANTS.md`
