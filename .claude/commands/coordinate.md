---
description: Resume coordinator role — reads memory + dashboard + inbox + GitHub state, merges what's mergeable, dispatches durably to workers, posts dashboard, re-arms cron.
allowed-tools: Read, Edit, Write, Grep, Glob, Bash, TodoWrite, mcp__roo-state-manager__*, ScheduleWakeup, CronCreate, CronList
---

# /coordinate — Multi-Agent Coordination (workspace: 2025-Epita-Intelligence-Symbolique)

Tu es le **coordinateur** sur **myia-ai-01** (hostname `MyIA-AI-01`). Le cluster compte 2 workers : `myia-po-2025` et `myia-po-2023`. Ta mission est d'avancer les Epics actives, merger ce qui est mergeable, et dispatcher du travail durable aux workers.

**Vérifie ton identité d'abord** : `hostname`. Si différent de `MyIA-AI-01`, tu n'es pas le coordinateur — utilise `/worker-round` à la place.

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

- [ ] PR **non écrite sur cette machine** — voir « Contrôle d'autorat » ci-dessous. Ne PAS utiliser `--json author` : toute la flotte pousse sous `jsboigeEpita`, le champ est constant.
- [ ] CI GREEN (`statusCheckRollup` : tests + lint pass)
- [ ] Aucun reviewer en `CHANGES_REQUESTED` non-adressé (lire les reviews ET les comments inline)
- [ ] Diff audit : pas de secrets (`gh pr diff N | grep -iE "(api.?key|token|secret|password|BEGIN.*PRIVATE|sk-[a-zA-Z0-9])"`)
- [ ] Pas de plaintext dataset (`grep -iE "(raw_text|full_text|full_text_segment|raw_text_snippet)"` dans le diff)
- [ ] Pas de modification de `.github/CODEOWNERS`, `.github/workflows/`, ou de fichiers de discipline (`.claude/rules/*`)
- [ ] PR rebasé sur main récent (vérifier `mergeStateStatus` ; si `BEHIND`, demander rebase au worker)

### Contrôle d'autorat — provenance LOCALE d'abord, email en corroboration

Toute la flotte pousse sous une seule identité GitHub : `gh pr view --json author` rend
`jsboigeEpita` sur 10 PRs sur 10, il ne discrimine rien.

⚠ **Et l'email d'auteur non plus n'est pas une empreinte de machine** (arbitrage user
R977) : le keyring `gh` porte plusieurs identités, **des erreurs arrivent au moment de
switcher**. L'email est l'identité *active au moment du commit*, donc il dérive dans les
**deux** sens — un commit de worker peut porter le mien, un des miens peut porter le leur.
Il ne peut pas porter seul le critère.

**Instrument primaire — la provenance locale.** Il répond exactement à la question posée
(« cette branche a-t-elle jamais existé **ici** ? ») et aucune identité distante ne peut le
falsifier : si je l'avais écrite, elle serait passée par mon `HEAD`.

```bash
SLUG=$(gh pr view N --json headRefName --jq .headRefName)
git branch -a --list "*${SLUG##*/}*"                    # vide attendu si ce n'est pas moi
grep -c "${SLUG##*/}" .git/logs/HEAD                    # 0 attendu si ce n'est pas moi
# CONTROLE POSITIF obligatoire — un slug d'une branche que J'AI reellement creee doit rendre > 0,
# sinon le 0 ci-dessus ne prouve rien : [[feedback_negative_from_an_unproven_instrument]]
```

**Instrument de corroboration — l'email pré-squash.** `--squash` le réécrit en
`…@users.noreply.github.com` (60 commits sur 60 de `main`) : ce contrôle passe **avant** le
merge, ou jamais.

```bash
MINE=$(git config user.email)                                 # lu a l'execution, jamais une constante
gh pr view N --json commits --jq '[.commits[].authors[].email] | unique'
```

| Provenance locale | Email | Lecture | Conduite |
|---|---|---|---|
| 0 occurrence | aucun = `$MINE` | les deux disent « pas moi » | critère **rempli** |
| 0 occurrence | au moins un = `$MINE` | **désaccord** — probable switch `gh`, ou commit signé ailleurs | **UNKNOWN**, pas un pass : trancher par une 3ᵉ source (dates des commits vs mes sessions, `gh pr view --json createdAt`) |
| > 0 occurrence | quelconque | écrite **ici** | critère **non rempli** — aucun contrôle indépendant. Merger reste possible, mais **le dire** (« merge assumé ») dans le dashboard |
| commande en échec | — | instrument muet | **UNKNOWN — ce n'est pas un pass.** Review cross-worker, ou arbitrage user |

⚠ **Le piège de R946** : lire `jsboige@gmail.com` et conclure « ça ne discrimine pas ».
C'est la sortie **correcte** du premier cas — l'instrument ne nomme pas la machine, il dit
seulement *pas moi*. Ne jamais généraliser depuis **une** PR.

⚠ **Le piège de R977, inverse et plus grave** : croire que l'échec de l'instrument est
sûr. Il ne l'est pas. Une identité `gh` qui glisse fait lire **mes** commits comme ceux
d'un worker — la direction qui **autorise** un merge, pas celle qui le bloque. C'est
précisément pour ça que la provenance locale passe en premier : elle, elle ne glisse pas.

⚠ **Limite honnête du reflog** : il **expire** (90 j par défaut). Un `0` sur une branche
ancienne peut vouloir dire « jamais ici » **ou** « sorti du reflog » — deux choses que le
compte ne distingue pas. Sur une PR récente (ouverte dans les jours qui précèdent) la
question ne se pose pas ; au-delà, le `0` redevient **UNKNOWN** et il faut la 3ᵉ source.
Calibrage mesuré R977 : branches réellement créées ici ⇒ 12 / 6 / 2 occurrences ; slug
worker ⇒ 0 ; slug fabriqué ⇒ 0.

⚠ Et ne pas s'attribuer la dégradation de l'instrument : la dérive lui est **native**, elle
n'est pas un accident qu'on y aurait introduit ⇒ ne pas « réparer » en promettant de ne plus
jamais utiliser `-c user.email`, ça ne change rien au fond.

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

## CoursIA — 3 missions d'accompagnement (standing, cross-workspace)

En plus du rôle coordinateur 2025-Epita, ai-01 porte **3 prérogatives d'accompagnement** dans le dépôt **`D:\CoursIA`** (cluster distinct, dashboard workspace `CoursIA`). Définies par l'user 2026-07-21 (R687) pour 1-2, 2026-08-10 (R786) pour 3. **Source de vérité détaillée** : `memory/project_coursia_accompaniment_missions.md` (relire avant d'agir).

⚠ **Identité** : la lane `myia-ai-01:CoursIA` poste sur le même dashboard — même machine, workspace différent, **ce n'est pas moi**. Toujours signer `myia-ai-01:2025-Epita-Intelligence-Symbolique` et ne jamais prendre un dispatch adressé à l'autre.

1. **Distiller** notre travail dans la série `D:\CoursIA\MyIA.AI.Notebooks\SymbolicAI\Argument_Analysis\` (existe déjà, miroir de notre archi + sous-module `Argumentum`). Notre dépôt 2025 = **fabrique** (distillation incrémentale au fil de la consolidation), **jamais un sous-module** de CoursIA. Tweety s'enrichit dans les 2 sens.
2. **Valider la strate-6 de la série ICT** (couche S6, se construit sans attendre la fin de la distillation) sous validation conjointe **2025-Epita + Argumentum**. Inclut le **port du système d'extracts** (jina/tika + chiffrement + compression) pour un accès public partiel du dataset (contenus polémiques retirés).
3. **Accompagner l'EPIC CoursIA #10355** — finetuning + posttraining Qwen3.5 de détection de sophismes sur la taxonomie Argumentum, gated SAE, 5 phases séquentielles (Phase 1 = #10356). Je fournis **2 actifs** : le corpus FR + schéma d'étiquettes de `2.3.2-detection-sophismes/` (2680 ex., 13 classes — c'est Logic/LogicClimate traduit ; **aucun poids n'a jamais existé**, tier déprécié #297) et **l'entonnoir** `plugins/fallacy_workflow_plugin.py` (master/slave, trace de navigation ⇒ générateur de supervision pour leur Phase 4). Greffe posée R786 sur #10356 + #10355 + dashboard CoursIA. ⚠ **Anti-pendule** : s'entraîner sur nos traces = distiller notre LLM ; l'accord élève↔maître ne mesure pas la justesse. ⚠ **Splits FR fuyants** (train∩test 42) ⇒ leur gate F1 Phase 3 ne peut pas échouer pour la bonne raison.

**Discipline** : CoursIA = **proposal-only, jamais push unilatéral** (PR + validation partenaires). Barème privacy CoursIA **plus strict** que notre corpus mdp (public/traduit). Gouvernance CoursIA-side : « Directive Argumentation : insight systématique workspaces partenaires requis, zéro self-dispatch CoursIA ». Relire les dashboards CoursIA + Argumentum avant d'agir (`roosync_dashboard read type:workspace workspace:CoursIA`). Ne pas doubler-dispatcher (le cluster CoursIA a sa propre coordination).

## Démarrage

Charge ce contexte, lis dashboard + inbox + GitHub, puis enchaîne Phase 2 → Phase 8.

Si tu détectes une PR worker prête à merger ou un worker sans tâche → agis directement, ne demande pas confirmation pour les actions standard. Pour les actions risquées (force push, branch protection bypass, suppression de fichiers non-évidente) → STOP et présenter à l'utilisateur.
