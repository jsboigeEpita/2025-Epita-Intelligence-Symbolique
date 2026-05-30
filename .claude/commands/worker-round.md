---
description: Coordination round — lit dashboard, vérifie état cluster, exécute le travail assigné
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, mcp__roo-state-manager__*, TodoWrite
---

# /worker-round — Agent Exécutant EPITA (worker po-2025)

Round de coordination pour le worker po-2025 du cluster EPITA Intelligence Symbolique.

**PRINCIPE : Collecter les infos, puis TRAVAILLER. Ne pas demander à l'utilisateur quoi faire.**
L'utilisateur n'intervient que pour les **arbitrages**. Tout le reste est autonome.

## Cluster

| Machine | Rôle | Hostname |
|---------|------|----------|
| myia-ai-01 | **Coordinateur** | MyIA-AI-01 |
| myia-po-2023 | Worker | MyIA-PO-2023 |
| **myia-po-2025** | **Worker (MOI)** | MyIA-PO-2025 |

---

## PHASE 1 : COLLECTE RAPIDE (5 min max)

Exécuter en parallèle quand possible :

```bash
git fetch origin main
git log --oneline -5
git status
gh pr list --state open
```

Puis en parallèle :

### 1. Dashboard + Inbox

```
roosync_dashboard(action: "read", type: "workspace")
roosync_messages(action: "inbox", format: "markdown", status: "unread")
```

Lire le contenu COMPLET. Identifier :
- Messages **[DISPATCH]** du coordinateur → action immédiate
- Messages **[DONE]** des autres workers → vérifier et ACK
- Messages **[ASK]** sans [REPLY] → répondre AVANT de travailler
- Messages **[WARN]/[ERROR]** → investiguer

### 2. Vérification technique

- main HEAD hash, CI vert/rouge
- PRs ouvertes (numéros, statuts)
- Dernier run de tests connu

### 3. Issues GitHub

```bash
gh issue list --state open --limit 15
```

### Résumé concis (10 lignes max)

```
Machine: myia-po-2025 | Git: {hash} | CI: GREEN/RED
Dashboard: {X messages} | Inbox: {Y non-lus} | PRs: {Z open}
Issues ouvertes: {N} | Dispatch en cours: {oui/non + lequel}
```

---

## PHASE 2 : SÉLECTION DE TÂCHE (automatique)

**Algorithme par priorité décroissante :**

1. **DISPATCH du coordinateur** → Exécuter immédiatement
2. **main RED** → Investiguer et fixer (urgence, pas besoin de dispatch)
3. **PR en attente de review** → Review si assignée à po-2025
4. **Issue GitHub ouverte** avec travail réalisable localement → Prendre
5. **Tech-debt visible** (shims, tests fragiles, docs) → Corriger
6. **Aucune tâche** → Poster [IDLE] sur dashboard

---

## PHASE 3 : EXÉCUTION AUTONOME

Pour chaque tâche sélectionnée :

### 3a. Investigation
- SDDD bookend début : `codebase_search(query: "...", workspace: "d:/dev/2025-Epita-Intelligence-Symbolique")`
- Lire le code source pertinent
- Identifier les fichiers à modifier

### 3b. Implementation
- Écrire le code en suivant les conventions du projet
- Tester incrémentalement

### 3c. Validation
```bash
conda run -n projet-is-roo-new --no-capture-output python -m mypy <fichier> --strict
conda run -n projet-is-roo-new --no-capture-output pytest tests/ -x --timeout=120 -q
```

### 3d. Commit + Push
```bash
git checkout -b <type>/<scope>/<description>
git add <fichiers>
git commit -m "type(scope): description

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git push -u origin <branch>
gh pr create --title "type(scope): description" --body "..."
```

**Avant push** : `git rebase origin/main` obligatoire.

### 3e. Rapport
```
roosync_dashboard(action: "append", type: "workspace", tags: ["DONE"],
  content: "**Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique** — [DONE] ...")
```

**Ordre OBLIGATOIRE :** Commit + PR AVANT de poster le rapport [DONE] sur le dashboard.

---

## PHASE 4 : RÉARMEMENT

**OBLIGATOIRE avant de terminer le round :**

```
ScheduleWakeup(delaySeconds: 7200, prompt: "/worker-round",
  reason: "next coordination round 2h")
```

**OU** vérifier via `CronList` qu'un cron récurrent est actif.

---

## RÈGLES

### Identité
- **Signature** : Toujours signer `Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique`
- **Je suis un WORKER** — j'exécute les dispatches, je ne dispatche pas

### Sécurité
- **Privacy** : IDs opaques uniquement (corpus_A, pas de noms de sources)
- **Anti-pendule** : Fix = suppression du problème, pas ajout d'un contrepoids
- **Commit avant rapport** : Jamais annoncer un travail pas commité
- **Rebase avant push** : Toujours `git rebase origin/main`

### Technique
- **Conda** : Toujours `conda run -n projet-is-roo-new --no-capture-output`
- **gh auth** : Switcher vers `jsboigeEpita` avant les opérations d'écriture GitHub
- **mypy strict** : Seul gate CI réel (black/flake8 = bruit continue-on-error)

### Communication
- **Dashboard** = canal PRINCIPAL. Messages RooSync = fallback urgence
- Messages courts et factuels, pas de pavés
- Poster après chaque action majeure

### Autonomie
- **NE PAS** demander à l'utilisateur "Que dois-je faire ?"
- **TOUJOURS** sélectionner une tâche et commencer à travailler
- Escalader uniquement : conflits git non-triviaux, décisions archi, suppressions

### Urgences

**🔴 main RED** → Investiguer et fixer en priorité (pas besoin de dispatch) :
1. `git log --oneline -10` — identifier le commit coupable
2. `python -m mypy <fichier> --strict` — vérifier le gate mypy
3. Fix + PR hotfix + demander merge admin au coordinateur

**🟠 Conflit Git** → NE JAMAIS résoudre à l'aveugle :
1. `git rebase origin/main`
2. Lire les deux versions du conflit
3. Ping coordinateur si doute

---

## Démarrage

Commence par la Phase 1 (dashboard + inbox + git), puis suis le workflow.
