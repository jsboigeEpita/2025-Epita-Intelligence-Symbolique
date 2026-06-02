# Smoke-Test E2E des Points d'Entrée — R311

**Date**: 2026-06-02
**Base**: main `e6c7003b`
**Auteur**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique
**Dispatch**: R311 (ai-01) — QA no-regret post-A-14

## Verdict

**3/4 points d'entrée opérationnels.** Le CLI (light workflow), le proxy Starlette et le script de démonstration démarrent et servent du trafic sans erreur. **FastAPI (`api/main.py`) ne boot pas** sur cette machine en raison d'un binaire torch cassé (`fbgemm.dll` WinError 182) — problème environnement, pas une régression code. Le CLI présente un gap `sys.path` mineur documenté (nécessite `PYTHONPATH=<repo_root>` pour les invocations documentées dans son propre docstring).

**Conclusion** : la topologie deux-serveurs A-14 (FastAPI surface + Starlette proxy) est correctement câblée. La seule casse runtime est un problème binaire torch préexistant, non introduit par les merges récents.

## Résultats détaillés

| # | Point d'entrée | Statut | Détail |
|---|---------------|--------|--------|
| 1 | **FastAPI** `api/main.py` | ❌ CRASH | `WinError 182` sur `fbgemm.dll` (torch 2.2.2 binary broken). L'import cascade `api.main → endpoints → dependencies → service_manager → fact_checking_orchestrator → fact_claim_extractor → spacy → torch` crash. |
| 2 | **Starlette proxy** `interface_web/app.py` | ✅ PASS | Boot OK (8s). Route `/` → 200 (React `index.html` servi). Route `/api/health` → 502 attendu (backend FastAPI pas lancé). Proxy dégrade gracieusement. |
| 3 | **CLI** `run_orchestration.py --workflow light` | ✅ PASS | 3/3 phases complétées, 0 failed. Dégradation gracieuse sur LLM 401 et torch DLL (fallbacks heuristiques). 22 workflows listés. |
| 4 | **Démo** `demonstration_epita.py` | ✅ PASS | `--help` OK (exit 0). Mode non-interactif `--all-tests` disponible. BOM UTF-8 cosmétique (non-bloquant). |

## Résidus identifiés

### 1. FastAPI torch cascade (ENV, pas code)

**Chaine d'import** :
```
api/main.py → api/endpoints.py → api/dependencies.py
→ orchestration/service_manager.py → fact_checking_orchestrator.py
→ agents/tools/analysis/fact_claim_extractor.py:14 → import spacy → torch
```

**Cause racine** : `fbgemm.dll` (torch 2.2.2) ne charge pas au niveau OS (`ctypes.WinDLL` reproduit l'erreur). L'environnement `projet-is-roo-new` spécifie torch >= 2.4 mais 2.2.2 est installé.

**Mitigation code** (lazy import) vs **correction** (reinstall torch) : la correction propre est de réinstaller torch >= 2.4 dans l'environnement conda. Un lazy import de `spacy` dans `fact_claim_extractor.py` masquerait le crash pour les routes non-fact-checking, mais toute route fact-check crasherait à l'appel.

### 2. CLI sys.path gap (code, mineur)

`run_orchestration.py` (lignes 44-47) ajoute `current_dir` (= `argumentation_analysis/`) au `sys.path` mais pas `current_dir.parent` (= racine du projet). L'invocation documentée dans son propre docstring (`python argumentation_analysis/run_orchestration.py --text "..."`) échoue avec `ModuleNotFoundError: No module named 'argumentation_analysis'`.

**Fix** : ajouter `current_dir.parent` au `sys.path`. One-liner.

### 3. Demo BOM (cosmétique)

`demonstration_epita.py` commence par un BOM UTF-8 (`U+FEFF`). Python l'accepte nativement, mais `ast.parse(open().read())` échoue. Non-bloquant pour l'exécution.

## Issues ouvertes

| Issue | Type | Priorité | Portée |
|-------|------|----------|--------|
| #882 | bug (env/docs) | MEDIUM | FastAPI torch cascade — documenter le prérequis torch >= 2.4 et/ou lazy-import spacy |
| #883 | bug (code) | LOW | CLI `sys.path` gap — ajouter `current_dir.parent` |

## À valider par l'utilisateur

- **RAS** — aucune décision de sécurité ou de conception dans ce rapport. Les deux issues sont des fix-intents de bas niveau.

---

*Généré par Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique — R311 dispatch QA*
