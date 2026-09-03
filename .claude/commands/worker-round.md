---
description: Coordination round — lit dashboard, vérifie état cluster, exécute le travail assigné
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, mcp__roo-state-manager__*, TodoWrite
---

# /worker-round — Agent Exécutant EPITA

Round de coordination pour un worker du cluster EPITA Intelligence Symbolique.

## Identité — dérivée, jamais supposée

Ce fichier est **partagé par les deux workers**. Commence par `hostname` et déduis :

| hostname | machine-id | signature |
|---|---|---|
| `MyIA-PO-2025` | `myia-po-2025` | `Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique` |
| `MyIA-PO-2023` | `myia-po-2023` | `Claude Code @ myia-po-2023:2025-Epita-Intelligence-Symbolique` |
| `MyIA-AI-01` | — | tu n'es **pas** un worker → utilise `/coordinate` |

Partout où ce fichier écrit `<MOI>`, substitue ton machine-id. Ne signe jamais du nom de l'autre worker : le dashboard est commun, et une signature fausse attribue le travail à la mauvaise lane.

**PRINCIPE : Collecter les infos, puis TRAVAILLER. Ne pas demander à l'utilisateur quoi faire.**
L'utilisateur n'intervient que pour les **arbitrages**. Tout le reste est autonome.

## Cluster

| Machine | Rôle | Hostname |
|---------|------|----------|
| myia-ai-01 | **Coordinateur** | MyIA-AI-01 |
| myia-po-2023 | Worker | MyIA-PO-2023 |
| myia-po-2025 | Worker | MyIA-PO-2025 |

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
Machine: <MOI> | Git: {hash} | CI: GREEN/RED
Dashboard: {X messages} | Inbox: {Y non-lus} | PRs: {Z open}
Issues ouvertes: {N} | Dispatch en cours: {oui/non + lequel}
```

---

## PHASE 2 : SÉLECTION DE TÂCHE (automatique)

**Algorithme par priorité décroissante :**

1. **DISPATCH du coordinateur** → Exécuter immédiatement
2. **main RED** → Investiguer et fixer (urgence, pas besoin de dispatch)
3. **PR en attente de review** → Review si assignée à `<MOI>`
4. **Aucun dispatch** → **dépiler la file** selon le PROTOCOLE IDLE ci-dessous
5. **Tech-debt visible** (shims, tests fragiles, docs) → Corriger, en ouvrant l'issue d'abord
6. **Rien d'éligible** → IDLE **énuméré** (cf. protocole), jamais un IDLE nu

---

## PROTOCOLE IDLE — dépiler la file sans steering

**L'absence de dispatch n'est pas un signal d'arrêt, c'est le cas normal.** Le coordinateur
tourne à une cadence lente (plusieurs heures) : un worker qui livre puis attend le prochain
réveil gaspille l'essentiel de sa disponibilité. Entre deux dispatches, la file d'issues est
le travail. Ce protocole existe pour que ce dépilage soit **sûr** — pas pour autoriser
l'improvisation.

### 1. Éligibilité — filtrer AVANT de choisir

Une issue est prenable si **toutes** ces conditions tiennent :

- ce n'est pas un **Epic** (un Epic se décompose, il ne s'exécute pas) ;
- **aucun commentaire ne la gèle** — chercher dans les commentaires : `arbitrage`,
  `do NOT engage`, `garée`, `gated`, `décision utilisateur`, `en attente de` ;
- elle ne dépend pas d'une **décision utilisateur** (secret de dépôt, périmètre du gate,
  contenu de `.github/workflows/`) ;
- **aucune PR ouverte ne la référence** (`gh pr list --search "#N"`) ;
- **personne ne l'a revendiquée** (cf. §2) ;
- son périmètre ne touche ni `.github/workflows/`, ni `.github/CODEOWNERS`, ni `.claude/rules/`.

**Un doute sur un seul critère suffit à passer à la suivante.** Sauter une issue prenable ne
coûte rien — elle sera là au tour d'après. Reprendre une issue délibérément gelée détruit un
arbitrage et fait travailler deux agents l'un contre l'autre.

### 2. Revendication — avant d'écrire la première ligne de code

1. Relire le dashboard workspace et repérer les `[CLAIMED]` récents.
2. `roosync_dashboard(action:"append", type:"workspace", tags:["CLAIMED"], …)` — l'issue et
   l'horizon que tu te donnes.
3. Commenter l'issue en **une ligne** : c'est la surface que l'autre worker et le
   coordinateur lisent sans passer par le dashboard.
4. **Relire le dashboard.** En cas de revendication simultanée sur la même issue, le
   **machine-id le plus petit dans l'ordre alphabétique garde**, l'autre libère et passe à la
   suivante. Règle déterministe : ni négociation, ni attente, ni message.

### 3. Ordre de choix

1. Une issue qui en **débloque** une autre (référencée par une autre issue ou PR ouverte).
2. Une issue dont la **DoD est déjà écrite** — exécutable sans phase de conception.
3. Une issue de **ta lane** : `po-2025` plomberie et runs lourds ; `po-2023` travail
   conceptuel ciblé.
4. À valeur égale, **la plus petite** : livrer vaut mieux qu'entamer.

Si l'issue n'a **pas** de DoD, écris-la en commentaire d'abord, puis exécute celle-là. Un
travail sans critère d'arrêt n'est pas vérifiable, et ne sera pas mergeable.

### 4. Ce que le travail idle ne fait jamais

- **Ne merge pas sa propre PR** — le merge appartient au coordinateur.
- **Ne supprime rien** hors du Cleanup Gate (justification par fichier ; table obligatoire
  au-delà de 5 suppressions). Déplacer vers `_archives/` sans preuve de préservation n'est
  pas une consolidation.
- **N'élargit pas le périmètre** de l'issue prise. Autre chose trouvé en chemin → une issue
  séparée, nommée, et on continue.
- **Ne re-litige pas un arbitrage** déjà posé, même en désaccord : commenter, pas défaire.
- **Ne pousse jamais sur `main`.**

### 5. Quand rien n'est éligible

Poster l'IDLE **avec l'énumération** : les issues examinées et, pour chacune, le motif de
rejet en une ligne. Un IDLE nu ne transmet rien ; un IDLE énuméré dit au coordinateur si la
file est réellement vide ou si le filtre est trop serré — et c'est lui qui peut desserrer.

**Cap : après 3 IDLE consécutifs, ne pas ré-armer.** Attendre un steering explicite. Trois
tours vides mesurent une file vide, pas un incident à répéter.

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

**Avant push — scan privacy des surfaces indexées (HARD, aucune exception)** :

```bash
# 1. les messages de commit que tu t'apprêtes à pousser
python scripts/security/scan_indexed_surfaces.py --commits origin/main..HEAD

# 2. le corps de PR que tu t'apprêtes à écrire
python scripts/security/scan_indexed_surfaces.py --text-file <ton_body.md>
```

Les deux doivent sortir `clean`. Un message de commit poussé est **permanent** : le dépôt est
public et forké, donc une réécriture d'historique ne le retire même pas des forks. Il n'existe
aucun garde CI sur ces surfaces — le scan manuel est la seule barrière.

⚠ **Ne scanne pas à la main avec `grep`** : les 19 motifs partagés portent ``, qui est une
frontière de *mot*, et `_` est un caractère de mot. `Nom` **ne peut pas** matcher `nom_only`
(#2012) — exactement la forme qu'un nom prend en entrant dans du code. Le script applique une
frontière-lettre et voit les deux formes. Une case DoD « aucun nom de source » cochée contre un
`grep -w` est fausse par construction.

### 3e. Rapport
```
roosync_dashboard(action: "append", type: "workspace", tags: ["DONE"],
  content: "**Claude Code @ <MOI>:2025-Epita-Intelligence-Symbolique** — [DONE] ...")
```

**Ordre OBLIGATOIRE :** Commit + PR AVANT de poster le rapport [DONE] sur le dashboard.

---

## PHASE 4 : RÉARMEMENT

**`CronList` D'ABORD — toujours, avant toute création.**

1. `CronList`
2. Un job récurrent `/worker-round` existe déjà → **ne rien créer**, le round est fini.
3. Aucun → en créer **exactement un** :
   `CronCreate(cron: "<minute hors :00 et :30> */<N ≥ 2> * * *", prompt: "/worker-round", recurring: true)`

**Ne pas utiliser `ScheduleWakeup` pour porter la cadence** : il est clampé à 3600 s. Un
`delaySeconds: 7200` ne donne pas deux heures, il en donne une — sous le plancher de cadence
de la flotte, sans que rien ne le signale.

**Jamais deux crons sur une lane.** Un cron vit en mémoire de session : il meurt avec le REPL
et avec une mise à jour de VS Code. Mais la restauration de fenêtre ressuscite **la session
sans son cron** — donc un ré-armement réflexe après restauration crée un doublon qui tire deux
fois. Le seul état lisible est celui que `CronList` rend, jamais celui dont on se souvient.

**Changer de cadence = `CronDelete` puis `CronCreate`**, jamais créer à côté.

Après 3 IDLE consécutifs (cf. protocole idle) : **ne pas ré-armer**.

---

## RÈGLES

### Identité
- **Signature** : Toujours signer `Claude Code @ <MOI>:2025-Epita-Intelligence-Symbolique` (`<MOI>` dérivé du `hostname`, cf. section Identité)
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
