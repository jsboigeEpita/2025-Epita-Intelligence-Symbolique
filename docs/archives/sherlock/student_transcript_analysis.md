# Sherlock Student Project — Transcript Analysis (Issue #346)

## Source

Soutenance orale 2025 d'un projet étudiant **standalone** (n'a pas commité sur ce dépôt — d'où l'absence de code source ici). Le transcript audio (`.vtt`) et la session ChatGPT associée sont stockés hors-dépôt dans le drive du professeur (`G:/Mon Drive/MyIA/Formation/Epita/2025/Soutenances/`, non versionné).

L'équipe a explicitement raconté pourquoi : *« au début, on a eu beaucoup de mal à s'intégrer dans le repo, donc on a décidé de partir sur quelque chose d'à côté »*. Le projet a été déployé en standalone sur GitHub Pages (frontend statique).

Pour cette analyse, l'équipe est désignée **Team-T** (transcript-only) et le projet **« Kaiza Hay »** (nom public donné en soutenance).

## Contexte d'inspiration

L'équipe s'est explicitement inspirée du Sherlock/Watson/Moriarty initial du dépôt, mais a inversé le paradigme UX :

| Rôle | Initial (notre dépôt) | Kaiza Hay (Team-T) |
|---|---|---|
| **Sherlock** | Agent IA (moteur d'inférence + génération hypothèses) | **L'utilisateur humain** (joueur) |
| **Watson** | Agent IA (Tweety + JTMS, vérif logique) | Agent IA **concurrent** au joueur (extrait alibis/observations en parallèle, maintient KB) |
| **Moriarty** | Oracle qui donne des coups de pouce | **Générateur de scénario** : ajoute descriptions, ambiance, fausses pistes |
| **Suspects** | (n/a — Cluedo-style cards) | **4 agents LLM** avec personnalité, alibi propre, observations propres, comportements (timide / menteur / coopératif) |

Le joueur (= Sherlock) interroge les suspects, Watson tente de résoudre l'enquête en parallèle, le joueur essaie d'être plus rapide.

## Architecture technique

### Stack

- Frontend : JS + HTML/CSS pur (statique → GitHub Pages gratuit)
- Moteur 2D : **Phaser** (interface carte interactive, tableau mental drag-and-drop)
- Logique formelle : **tau-prolog** (Prolog dans le navigateur)
- LLM : OpenAI GPT-4o, requêtes manuelles via API
- Coût mesuré : ~0.05 €/partie, durée ~10-15 min
- Sound design (musique d'ambiance, sons d'action)

### Pipeline de génération de scénario (étape symbolique d'abord)

1. **Tirage de variables aléatoires** : professions des suspects + de la victime, mode de mort, dates, lieux
2. **Application de règles logiques** :
   - *Une seule personne ment sur son alibi*
   - *La personne qui ment = meurtrier*
   - *Chaque suspect a 1+ observations qui corrèlent les alibis des autres*
   - L'inconsistence entre alibis force la résolution déductive
3. **Pré-scénario obtenu** (squelette logique cohérent)
4. **Enrichissement par Moriarty (LLM)** : ajout de descriptions, ambiance, fausses pistes pour rendre l'enquête non-triviale

### Pipeline d'interrogation (en jeu)

1. Joueur interroge un suspect via interface
2. Le suspect (agent LLM avec personnalité) répond — peut être réticent, mentir, refuser de parler
3. Joueur doit **argumenter** pour le faire parler (mécanique de pression sociale)
4. Watson observe en parallèle, extrait alibis + observations en langage naturel, maintient une base de connaissances logique
5. Joueur peut accuser à tout moment via un bouton dédié
6. Verdict + explication détaillée + retour au tableau pour post-mortem

## Capabilities-clés à reprendre pour le Track 3 (Sherlock revisité)

Listées par ordre d'utilité pour notre rebuild moderne (Track 3 = #357-#360) :

### P0 — Adopter directement
1. **Inversion UX Sherlock = utilisateur, Watson = concurrent IA** — c'est le twist narratif qui rend le truc spectaculaire. Notre rebuild doit garder cette inversion.
2. **Suspects-as-agents avec personnalité** — chaque suspect est un agent LLM avec :
   - alibi propre
   - observations propres
   - comportement (timide / menteur / coopératif)
   - règles d'argumentation pour passer la barrière
3. **Pipeline scénario : symbolique d'abord, LLM après** — tirage aléatoire de variables → règles logiques pour cohérence → enrichissement LLM. Notre Track 3 doit faire pareil pour générer des cas reproductibles + variés.
4. **Une règle logique simple cible** : « une seule personne ment » — donne au moteur de raisonnement une cible déductive nette. Compatible avec **JTMS retraction cascade** (#350) et **ATMS multi-context** (#349) qui sont déjà dans Track 1.

### P1 — À adapter
5. **Watson concurrent qui maintient une KB en parallèle** — chez nous, ce sera l'agent JTMS+ATMS branché sur les agents disponibles via `CapabilityRegistry`. Watson devient un orchestrateur de plusieurs sous-agents (Tweety, Dung, taxonomy fallacies, etc.) plutôt qu'un agent unique.
6. **Moriarty = générateur scénario + fausses pistes** — chez nous, Moriarty peut devenir un agent de **counter-arguments** + **debate adversarial** (capabilities #1.5 + counter-argument 5 stratégies déjà disponibles).
7. **Sound design + Phaser carte** — purement UX, *peut* inspirer Track 2 (Web UI) si on veut du gamified rendering, mais hors-scope strict du Track 3.

### Hors P0/P1 (pas pour le Track 3)
- tau-prolog → on a Tweety (plus puissant)
- Phaser → on a React + D3.js dans Track 2
- GitHub Pages → on a Starlette + React build dans `interface_web/`

## Mapping vers les issues du Track 3

| Issue Epic | Idée du transcript Team-T |
|---|---|
| #357 [3.1] Modern Sherlock orchestrator | User-as-Sherlock + Watson concurrent IA composé via CapabilityRegistry (5+ agents : extraction, fallacy, JTMS, ATMS, counter-arg). Pas seul agent monolithique. |
| #358 [3.2] Open-domain investigation | Adapter pipeline scénario → input texte du dataset chiffré : tirer "variables" depuis arguments extraits, appliquer "règles" depuis fallacies/JTMS/ATMS, générer enquête sur "qui dit la vérité, qui ment". |
| #359 [3.3] ATMS hypothesis branching | Pour chaque suspect = une hypothèse (« il est le meurtrier »). ATMS maintient cohérence par hypothèse en parallèle, retracte quand contradiction avec nouvelle observation. |
| #360 [3.4] Sherlock scenarios on dataset | Curation de 2-3 scénarios générés par notre pipeline ; opaque IDs (`doc_A`, `doc_B`, `doc_C`) ; chacun documente l'inversion UX + résultat Watson. |

## Différences avec notre rebuild (à expliciter dans le PR)

Le projet Team-T était un *jeu* (UX-first, ludique). Notre Track 3 est une *capability d'analyse* (analytique-first). Donc :

- ✅ On garde : pipeline symbolique-first, inversion Sherlock=user, agents-suspects, retraction logique
- ❌ On ne fait pas : sound design, Phaser, drag-and-drop tableau, GitHub Pages standalone
- 🔀 On modernise : Tweety > tau-prolog ; CapabilityRegistry > orchestrateur ad-hoc ; ATMS multi-context > toggle ouvert/fermé

## Privacy

Cette analyse n'inclut **aucun extrait littéral** du transcript audio ni du log ChatGPT. Les noms des étudiants ont été anonymisés en "Team-T" pour respecter la discipline de privacy du dépôt (cf. `CLAUDE.md` § Dataset Privacy). Le projet « Kaiza Hay » est nommé car il a été présenté publiquement en soutenance.

Les fichiers source (`G:/Mon Drive/.../Soutenances/Intelligence Symbolique - Argumentation-3.vtt` lignes ~10800-11781, et `ChatGPT-IASY-2.md` lignes ~1797-1968) restent hors-dépôt.

## Validation

Cette analyse débloque le Track 3 (issues #357-#360). Le coordinator peut maintenant :
1. Confirmer avec l'utilisateur que Team-T = bonne identification (vs autre transcript)
2. Communiquer ces P0/P1 à l'agent qui prendra les issues du Track 3
3. Fermer #346 après merge de ce doc
