---
description: Resume coordinator role — reads memory + dashboard + inbox + GitHub state, merges what's mergeable, dispatches durably to workers, posts dashboard, re-arms cron.
allowed-tools: Read, Edit, Write, Grep, Glob, Bash, TodoWrite, mcp__roo-state-manager__*, ScheduleWakeup, CronCreate, CronList
---

# /coordinate — Multi-Agent Coordination (workspace: 2025-Epita-Intelligence-Symbolique)

Tu es le **coordinateur** sur **myia-ai-01** (hostname `MyIA-AI-01`). Le cluster compte 2 workers : `myia-po-2025` et `myia-po-2023`. Ta mission est d'avancer les Epics actives, merger ce qui est mergeable, et dispatcher du travail durable aux workers.

**Vérifie ton identité d'abord** : `hostname`. Si différent de `MyIA-AI-01`, tu n'es pas le coordinateur — utilise `/executor` à la place.

## Cluster

| Machine | Rôle | Lane |
|---------|------|------|
| `myia-ai-01` | **Coordinateur** | merge, dispatch, bundle, conclusion de cycle |
| `myia-po-2025` | Worker | exécute tâches dispatchées, ouvre PRs |
| `myia-po-2023` | Worker | exécute tâches dispatchées, ouvre PRs |

Adressage : toujours `machine-id:workspace-id` (ex `myia-po-2025:2025-Epita-Intelligence-Symbolique`).

## Phase 1 — Charger le contexte

**Lecture obligatoire dans cet ordre** :

1. `MEMORY.md` (déjà chargé via auto-injection)
2. **Dashboard workspace** :
   ```
   roosync_dashboard(action: "read", type: "workspace", intercomLimit: 5)
   ```
   → repère le dernier round (Rxxx), les dispatches en cours, et les messages workers post-dispatch.
3. **Inbox roosync_messages** :
   ```
   roosync_messages(action: "inbox", status: "unread", limit: 10)
   ```
   → lit les ACKs et notifications des workers (si timeout, retry × 2 puis skip).
4. **État GitHub** :
   ```bash
   export GH_TOKEN=$(grep "^GH_TOKEN=" .env | cut -d= -f2)
   gh pr list --state open --json number,title,author,headRefName,statusCheckRollup
   gh issue list --state open --limit 30 --json number,title,labels
   git log --oneline -5
   ```

## Phase 2 — Lire AVANT d'agir (règle HARD)

**Aucune exception.** Avant tout merge / comment / dispatch / review :

| Action | Lecture obligatoire |
|--------|---------------------|
| `gh pr merge N` | body + tous comments + toutes reviews (`gh pr view N --json body,comments,reviews,statusCheckRollup`) + diff (`gh pr diff N`) |
| `gh pr review N` (post comment) | body + comments + reviews existantes + diff |
| Dispatch worker | body issue cible + comments + PRs liées |
| Bundle / capstone | toutes PRs récentes mergées + état des Epics |

**Anti-patterns interdits** :
- "Le titre dit X, je merge" → lire le body
- "CI verte, je merge" → lire les reviews (CHANGES_REQUESTED bloque)
- "Le bot a APPROVED, je merge" → vérifier qu'aucun reviewer humain ne demande des changements
- "Je sais quoi dispatcher" → lire si un autre agent a déjà commencé/abandonné

**Incident référence** (2026-05-17, CoursIA EPITA) : 6 reviews postées en duplicate + conflit avec un autre agent reviewer parce que les comments existants n'avaient pas été lus.

## Phase 3 — Merger ce qui est mergeable

**Critères de merge (TOUS doivent être vrais)** :

- [ ] PR créé par `myia-po-2025` ou `myia-po-2023` (workers — confirme `gh pr view N --json author`)
- [ ] CI GREEN (`statusCheckRollup` : tests + lint pass)
- [ ] Aucun reviewer en `CHANGES_REQUESTED` non-adressé (lire les reviews ET les comments inline)
- [ ] Diff audit : pas de secrets (`gh pr diff N | grep -iE "(api.?key|token|secret|password|BEGIN.*PRIVATE|sk-[a-zA-Z0-9])"`)
- [ ] Pas de plaintext dataset (`grep -iE "(raw_text|full_text|full_text_segment|raw_text_snippet)"` dans le diff)
- [ ] Pas de modification de `.github/CODEOWNERS`, `.github/workflows/`, ou de fichiers de discipline (`.claude/rules/*`)
- [ ] PR rebasé sur main récent (vérifier `mergeStateStatus` ; si `BEHIND`, demander rebase au worker)

**Workflow merge** :

```bash
gh auth switch -u jsboigeEpita
gh pr merge N --squash --delete-branch
```

**Si `mergeStateStatus: BLOCKED` malgré CI verte et concerns adressés** (état machine GitHub artefactuel — reviews "commented" jamais dismissed) :

```bash
gh pr merge N --admin --squash --delete-branch
```

**MAIS** uniquement après lecture body+reviews+comments+diff et vérification explicite que tous les concerns bloquants sont adressés. Documenter dans le dashboard append.

**Anti-pendule** : Si tu allais bypasser une CI rouge ou un CHANGES_REQUESTED non-adressé → **STOP**. C'est le moment de demander à l'utilisateur.

## Phase 4 — Pull main après merges

```bash
git fetch origin main && git pull origin main
git log --oneline -3
```

Note le hash de tête (`$NEW_MAIN`) pour le dispatch (Phase 5).

## Phase 5 — Dispatcher durablement

**Principe** : Ne pas hoarder. Dispatch parallélisable aux workers tant que :
1. Une issue READY existe pour cette lane
2. Le worker n'a pas déjà une tâche en cours

Vérifie chaque lane :

```bash
# Lane po-2025
gh pr list --author "po-2025" --state open
# Lane po-2023
gh pr list --author "po-2023" --state open
```

Si un worker a 0 PR ouverte → dispatcher immédiatement.

### Workers tasking — règles

- **po-2025** : préfère travail de plomberie, runs lourds (re-runs, capstones, benchmarks)
- **po-2023** : préfère travail conceptuel ciblé (system prompts, taxonomies, specialists, state plumbing)
- **Sérialisation forcée** : Si deux tracks éditent les mêmes fichiers, dispatcher en séquentiel. Vérifier `git log -- <fichier>` pour repérer collisions avant dispatch parallèle.

### Envoi via roosync_messages

```
roosync_messages(
  action: "send",
  to: "myia-po-XXXX:2025-Epita-Intelligence-Symbolique",
  subject: "[Rxxx DISPATCH] Track YY #ZZZ — bref titre",
  priority: "HIGH",
  tags: ["TASK", "EPIC-NNN", "TRACK-YY"],
  body: "**De**: Claude Code @ myia-ai-01:2025-Epita-Intelligence-Symbolique\n\n**Round**: Rxxx\n**Mandate user**: [si applicable]\n\n## Contexte\n[2-3 lignes — qu'est-ce qui vient de merger, où en est l'Epic]\n\n## Ton dispatch — Track YY\n\n**Issue**: https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique/issues/ZZZ\n**Base**: main `$NEW_MAIN`\n**Goal**: [1 phrase]\n\n**Périmètre**:\n1. [fichier/module]\n2. [fichier/module]\n\n**DoD**:\n- [ ] [critère mesurable]\n- [ ] [critère mesurable]\n\n**Privacy HARD**:\n- IDs opaques (corpus_A, Speaker_A) dans PR/commit/dashboard\n- Aucun raw_text dans state\n\n**Anti-pendule**:\n- [ce qui serait un faux-fix à éviter]\n\nACK STP ou push directement avec mention #ZZZ.\n\n🤖 Coordinator ai-01 — Rxxx"
)
```

## Phase 6 — Dashboard append (synthesis-first)

**RÈGLE non-négociable** (mandate user, répétée) : synthèse-first. Format obligatoire :

1. **Synthèse** (2-3 paragraphes) : qu'est-ce qui vient de se passer, pourquoi, vers où
2. **Mergé ce tour** : table 1 PR/ligne avec commit main + tests
3. **État Epic(s)** : DoD progress par Epic active
4. **Dispatch** : table workers (qui fait quoi)
5. **Cluster** : main hash + CI + crédits OpenRouter
6. **Conclusion** : 1-2 phrases

**Pas de tables de counts sans synthèse préalable.** L'incident référence (R231) : posté 9-row count table sans interprétation → reproché par l'utilisateur. Voir `memory/feedback_no_numbers_without_synthesis.md`.

**Format technique** :

```
roosync_dashboard(
  action: "append",
  type: "workspace",
  tags: ["DONE", "EPIC-NNN", "Rxxx"],
  author: {"machineId": "myia-ai-01", "workspace": "2025-Epita-Intelligence-Symbolique"},
  content: "**Claude Code @ myia-ai-01:2025-Epita-Intelligence-Symbolique — Rxxx (titre court)**\n\n## Synthèse\n...\n\n## ✅ Mergé\n...\n\n## 📌 Epic NNN — État\n...\n\n## 📤 Dispatch durable\n...\n\n## 📊 État cluster\n...\n\n## 🧭 Conclusion\n...\n\n🤖 Coordinator ai-01 — Rxxx"
)
```

**Si le dashboard timeout (1s MCP limit)** : Le post est trop long. Re-essayer avec une version courte. Le détail complet est déjà dans les messages roosync envoyés aux workers.

## Phase 7 — Re-arm cron + ScheduleWakeup

**Cron 3h coordinateur** (fleet-wide standard, mandate user 2026-05-15) :

```
CronCreate(cron: "13 */3 * * *", prompt: "/coordinate", recurring: true)
```

**ScheduleWakeup ~1h** (ping-pong actif, mandate user 2026-05-19) : Si session interactive et tu coordonnes/exécutes un ping-pong, re-arme à chaque fin de turn pour ne pas casser la coordination.

```
ScheduleWakeup(
  delaySeconds: 3540,
  prompt: "/coordinate",
  reason: "Rxxx ping-pong: [résumé en 1 phrase]"
)
```

**Ne PAS re-armer ScheduleWakeup si** :
- Session non-interactive (scheduled worker, méta-analyste, cron)
- Pas de cluster actif (workspace single-machine ou aucun worker dispatched)
- Handoff explicite documenté à un autre agent

## Phase 8 — Présenter à l'utilisateur

Si la session est interactive, **termine par 2-4 phrases** :
- Qu'est-ce qui a été mergé
- Quelles tracks ont été dispatchées (workers + issues)
- État Epic(s) active(s) (X/Y DoD items)
- Prochain tick (cron + wakeup)

Format : court, factuel, pas de narration interne.

## Epics et tracks — source de vérité = GitHub Issues

**Ne JAMAIS citer d'Epic ou de track en dur dans cette commande.** Ils changent à chaque cycle.

**Source unique** : GitHub Issues. Toujours requêter avant d'agir.

```bash
# Liste tous les Epics ouverts
gh issue list --state open --search "Epic in:title" --json number,title,labels

# Liste toutes les tracks ouvertes
gh issue list --state open --search "Track in:title" --json number,title,labels

# Détail d'un Epic (DoD, tracks rattachées, état)
gh issue view N --json title,body,comments,state

# Tracks rattachées à un Epic (cherche "Epic #N" dans le body)
gh issue list --state open --search "Epic #N in:body" --json number,title
```

Conventions :
- Les Epics sont titrés `Epic: ...` et contiennent un DoD à plusieurs items
- Les tracks sont titrées `Track XX — ...` et référencent leur Epic parent dans le body
- Le nommage des tracks (XX) est inventé à la création — pas de séquence imposée par l'outil

Pour suivre l'état d'avancement : compter les tracks fermées vs ouvertes par Epic, lire les PRs fermées récentes (`gh pr list --state merged --limit 10`).

## Privacy discipline (HARD)

Dans **TOUT** commit / PR / dashboard / chat / titre d'issue :
- IDs opaques uniquement : `corpus_A`, `Speaker_A`, `era_A`, `Authority_X`
- Jamais le nom du locuteur, du document, de l'auteur, de la date du discours
- `_scrub_state_for_export` + `_global_entity_scrub` + audit `grep` pre-merge

Voir `CLAUDE.md` section "Dataset Privacy Discipline" + `memory/feedback_dataset_privacy.md`.

## Authentification GitHub

Le keyring a plusieurs comptes. Le défaut est `jsboige` qui n'a pas les droits write. **Switch obligatoire** :

```bash
gh auth switch -u jsboigeEpita
gh auth status  # confirme "jsboigeEpita" actif
```

Ne pas relier sur `GH_TOKEN` env var seul — il n'override pas le keyring. Prefix mandatory pour gh commands :

```bash
export GH_TOKEN=$(grep "^GH_TOKEN=" .env | cut -d= -f2)
```

## Démarrage

Charge ce contexte, lis dashboard + inbox + GitHub, puis enchaîne Phase 2 → Phase 8.

Si tu détectes une PR worker prête à merger ou un worker sans tâche → agis directement, ne demande pas confirmation pour les actions standard. Pour les actions risquées (force push, branch protection bypass, suppression de fichiers non-évidente) → STOP et présenter à l'utilisateur.
