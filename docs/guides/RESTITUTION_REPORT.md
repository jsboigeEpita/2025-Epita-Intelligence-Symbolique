# Guide — Rapport de restitution (générer & lire)

**Epic #1134** (Restitution). Guide utilisateur / handoff pour le livrable central
du dépôt : le **rapport de restitution lisible** (3 actes), qui remplace le dump
dimensionnel illisible que l'owner appelait « très difficile à lire ».

> Ce guide dit **comment générer et lire** le rapport. Le **design** (pourquoi 3
> actes, le contrat de tissage §4, les portes G1–G4, la bande de verdict) vit dans
> le spec architecture :
> [`docs/architecture/RESTITUTION_REPORT_SPEC.md`](../architecture/RESTITUTION_REPORT_SPEC.md).
> On y renvoie plutôt que de le dupliquer.

---

## 1. Générer le rapport

Le rapport est produit par le pipeline unifié quand on active le rendu de
restitution :

```python
from argumentation_analysis.orchestration.unified_pipeline import run_unified_analysis

result = run_unified_analysis(
    text=mon_texte,
    workflow_name="full",        # "light" | "standard" | "full"
    render_restitution=True,     # ← assemble le rapport 3-actes
)

rapport = result["restitution_report"]   # RenderedReport | None
```

- `render_restitution=True` (défaut `False`) assemble le rapport **après** que le
  pipeline a peuplé le `state`. Câblage R6-final (#1140) : il remplace le dump
  dimensionnel comme premier rapport que rencontre le lecteur.
- `result["restitution_report"]` est un `RenderedReport` avec deux champs :
  - **`.markdown`** — le rapport en Markdown lisible (les 3 actes) ;
  - **`.verdict`** — le verdict de la porte de lisibilité (§3 ci-dessous).
- Renvoie `None` (et logge un avertissement) si le rendu échoue — le rendu
  n'échoue jamais le run (fail-loud non-fatal, #1019/#369).

### Workflow « spectacular »

Pour l'analyse pleine (chaîne complète, descente de taxonomie agentic, formel
Tweety, qualité) : `build_spectacular_workflow()` compose toutes les capacités.
Le rapport hérite de la richesse réelle du run — un run dégradé produit un
rapport honnêtement dégradé, jamais gonflé.

### Sortie fichier

Le rendu bas-niveau `render_spectacular_restitution(state, output_path=...)`
(`pipeline_adapter.py`) peut écrire directement le Markdown. Les sorties sur du
corpus réel sont **gitignored** par défaut (voir §5 Privacy).

---

## 2. Lire le rapport — structure en 3 actes

Le rapport suit le **mouvement argumentatif**, pas l'énumération des dimensions.
Les dimensions analytiques (sophismes, formel, qualité) deviennent des **notes de
preuve** qui appuient des battements narratifs — elles ne sont plus les chapitres.

### Acte I — Mise en situation (le cadrage, avant le microscope)
Ce que l'auditeur doit savoir **avant** d'entrer dans le texte : le genre de
discours, les enjeux (pour qui, quelle asymétrie), le **spectre des sophismes
attendus** pour ce genre (anticipation dérivée de la taxonomie, pas de la
détection), et la lecture game-theoretic (joueurs, intérêts, coups probables).
C'est le seul acte qui **anticipe** (spec §1.1).

### Acte II — Le récit dialectique (par mouvement)
Le texte découpé par **mouvement argumentatif** (un cluster d'arguments partageant
un sort rhétorique : attaqués par la même famille de sophismes, ou les soutiens qui
tiennent). Chaque battement tisse en une prose : l'argument, son **caractère**
(vertus de qualité), ses **dérapages** (sophisme localisé + descente + contre),
et sa **tenue formelle** citée comme preuve (« le solveur Tweety confirme
l'inconsistance », « le cadre de Dung isole cette attaque comme défaillante »).

### Acte III — La conclusion actionnable (ce que le lecteur en FAIT)
1. **Synthèse honnête** — le verdict, **gated** sur les portes G1–G4 et la bande
   de verdict (calculée depuis la couverture analytique réelle). Pas de sur-claim.
2. **Appréciations** — forces **et** faiblesses du discours (les deux, honnêtement).
3. **Que faire** — comment **contrer** (contre-arguments générés), les **points
   faibles à viser** (sophismes structurants + inférences Tweety-invalidees +
   attaques Dung-rejetées), et **à quoi s'attendre ensuite** (boucle sur le cadrage
   game-theoretic de l'Acte I).

> Détail design (contrat anti-énumération §4, portes G1–G4, bande
> EXCEEDED/MATCH/PARTIAL/BELOW) : voir le **spec** §2–§4.

---

## 3. La porte de lisibilité (PASS / WARN / FAIL)

Chaque rapport porte un `verdict` (`GateVerdict.band`) — un **self-check honnête,
jamais truqué** (#1019) :

| Bande | Sens | Lisible ? |
|-------|------|-----------|
| **PASS** | Chaque acte est présent, non-trivial, aucune odeur d'énumération. | ✅ |
| **WARN** | Présent et lisible, mais quelques références framework « nues » résiduelles (1–2). | ✅ (lisible, résidu signalé) |
| **FAIL** | Problème structurel : un acte manquant, ou une énumération manifeste (≥3 refs nues, ou dump). | ❌ |

`verdict.passed` est `True` pour PASS/WARN. Le verdict ne note **jamais** la courbe :
un rapport FAIL reste FAIL même si c'est tout ce qu'on a — l'honnêteté prime sur la
mise en scène. Un `markdown` est toujours produit (même FAIL), pour audit, mais la
bande dit s'il faut le lire comme fiable.

---

## 4. Mode vertueux — quand le texte n'est pas truffé de sophismes

Le moteur **tourne aussi sur des textes vertueux** (mandate user : « le positif est
le titre »). Sur un tel texte, l'Acte III **titre sur les vertus** au lieu des
points faibles, l'Acte I anticipe « ce qui *pourrait* déraper mais ne dérape pas »,
et l'Acte II mène avec **pourquoi l'argumentation tient**.

Le basculement est **dérivé, jamais asserté** (spec §5.1) :
`detect_virtuous_mode(state)` flag le texte vertueux **depuis la sortie du pipeline**
(0 sophisme localisé **ET** vertus qualité mesurées). Anti-pendule : un run vide
(rien produit) n'est **pas** lu comme vertueux ; un sophisme localisé disqualifie
le titrage vertueux ; **rien n'est fabriqué** pour remplir un battement.

### Le dataset contient-il des textes vertueux ?
Scan du corpus chiffré (#1159, [`scan_virtuous_corpus.py`](../../scripts/scan_virtuous_corpus.py)) :
verdict de rareté **ADEQUATE** — 11 candidats sur 45 extraits (18 sources), dont 4
à signal lexical zéro. **Ce sont des candidats** (screen lexical recall-oriented,
PAS un classifieur) — le flag vertueux réel se dérive au run pipeline.

> **État honnête** : la validation **end-to-end** d'un rapport vertueux réel
> (capstone #1160) est **en cours**. Le mode vertueux est prouvé sur tests
> synthétiques ; le run sur corpus réel reste à capturer. Ne pas sur-claim avant.

---

## 5. Privacy — ce qui sort, ce qui reste sur la machine

- **Sortie sur corpus réel = gitignored** par défaut (`argumentation_analysis/evaluation/results/`).
  Un résumé agrégé opaque (counts + verdict) seul peut être committé.
- **IDs opaques uniquement** (`arg_1`, `src_0_ext_2`, `corpus_A`) — jamais de nom
  de source, d'auteur, de date, de lieu. Le dépôt est indexé par GitHub Search.
- **Dataset chiffré en mémoire** : le corpus canonical est `extract_sources.json.gz.enc`
  (Fernet + gzip), chargé + déchiffré en mémoire, jamais persisté en clair.
- Le rapport paraphrase le corpus (les prompts portent la directive opaque FB-34) ;
  un scrub final (spec §6) est la garde en aval.

---

## Reproduction & références

- **Spec design** : [`docs/architecture/RESTITUTION_REPORT_SPEC.md`](../architecture/RESTITUTION_REPORT_SPEC.md)
  (absorbe `#1008` : verdict→prose, portes G1–G4, traçabilité capability→state-key).
- **Scan corpus vertueux** : [`scripts/scan_virtuous_corpus.py`](../../scripts/scan_virtuous_corpus.py)
  (verdict rareté, IDs candidats opaques).
- **Code** : package `argumentation_analysis/reporting/restitution/`
  (`renderer.py`, `act1_framing_plugin.py`, `act2_narrative_plugin.py`,
  `act3_conclusion_plugin.py`, `virtuous_identification.py`, `readability_gate.py`).
