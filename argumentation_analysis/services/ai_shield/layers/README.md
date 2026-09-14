# ai_shield/layers/ — les trois couches de validation du bouclier IA

## Rôle et frontière

Couches de défense en profondeur du bouclier IA : chaque classe hérite de
`ShieldLayer` (définie dans le fichier parent `../shield.py`) et expose une
méthode unique `validate(text, **kwargs) -> LayerResult`. Ce répertoire ne
contient **que** les couches — la composition en bouclier (`Shield`), les
presets et la politique `fail_open` vivent dans le parent
(`../shield.py`, `../presets.py`).

## Composants publics

| Composant | Fichier | Ce qu'il fait |
|---|---|---|
| `HeuristicLayer` | `heuristic.py:59` | scan regex/mots-clés à coût nul : injection (+0,4/match), biais (+0,3), manipulation (+0,5), motifs custom (+0,3), score plafonné à 1,0 |
| `LLMValidatorLayer` | `llm_validator.py:30` | classification de sécurité par LLM (jailbreak, injection, biais, manipulation, ingénierie sociale) ; entrée plafonnée à 2000 caractères, `max_completion_tokens=200` ; **lève** quand l'analyse est impossible (`LLMValidatorUnavailable`, `:18`) |
| `OutputFilterLayer` | `output_filter.py:55` | filtre de **sortie** LLM : fuites de prompt système (+0,5), identifiants (+0,6), PII (+0,3/match), chemins de fichiers (+0,2) |

`__init__.py` ré-exporte les trois classes.

## Points d'entrée valides

Aucun point d'entrée exécutable propre. La voie d'entrée unique est l'import
par le compositeur parent : `../presets.py:12-17` importe les trois couches et
`load_preset` (`presets.py:23`) les assemble :

| Preset | Couches | Lignes |
|---|---|---|
| `basic` | heuristic seule | `presets.py:36-44` |
| `advanced` | heuristic + LLM + output | `presets.py:45-55` |
| `output_only` | output seule | `presets.py:56-64` |
| `strict` | les trois, seuils abaissés, `fail_open=False` | `presets.py:65-77` |

Activation production : CLI `run_orchestration.py --shield-preset`
(défaut **`off`** — `run_orchestration.py:180` ; construction du
`shield_config` seulement si le preset diffère de `off`, `:214-217`), puis
exécution par `_invoke_ai_shield`
(`orchestration/invoke_callables.py:10339`). Le bouclier est donc
**opt-in**, inactif par défaut.

## Amont / aval

- **Amont** : `../presets.py` (composition), `../shield.py` (base
  `ShieldLayer` + agrégation), `orchestration/invoke_callables.py:10339`
  (invocation).
- **Aval** : résultats agrégés dans `state.ai_shield_results`
  (`core/shared_state.py:613`, append `invoke_callables.py:10439-10440`).
  Depuis #2095 ce champ a un **lecteur de production** :
  `unified_pipeline._shield_verdict` (`unified_pipeline.py:55`) le relit sans
  jamais y ajouter, et le verdict sort du pipeline sous la clé
  `shield_verdict` (`:437`).

## Statut d'intégration

| Famille | Statut | Preuve |
|---|---|---|
| `HeuristicLayer` | **actif** (opt-in) | composé dans les 3 presets le mobilisant (`presets.py:38,48-49,69-70`), exécution production `_invoke_ai_shield` (`invoke_callables.py:10339`) |
| `LLMValidatorLayer` | **actif** (opt-in) | composé dans `advanced` et `strict` (`presets.py:49,70`) ; sans `api_key` il **lève** au lieu de rendre un score (`llm_validator.py:87-91`) — c'est la politique `fail_open` du `Shield` qui décide ensuite (#2095) |
| `OutputFilterLayer` | **actif** (opt-in) | composé dans `advanced`, `output_only` et `strict` (`presets.py:50,58,71`) |

« Actif » signifie câblé et exécutable en production via `--shield-preset` ;
le défaut `off` fait qu'aucun run standard n'exécute ces couches.

## Artefacts et lecteurs

`LayerResult` (score, matches détaillés, raison, `error_type`) retourné à
`Shield` qui agrège ; trace et résultats poussés dans
`state.ai_shield_results` et l'entrée de trace du pipeline
(`invoke_callables.py:10439-10449`). Ces mêmes `LayerResult` sont ensuite
relus par `unified_pipeline._shield_verdict` (`unified_pipeline.py:55`) —
en lecture seule.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest \
  tests/unit/argumentation_analysis/test_ai_shield.py -v
```

## Frères et parent

- Parent : [ai_shield/](../) — son README ([`../README.md`](../README.md)) a
  été écrit depuis (2026-09-11, #2093) ; cette ligne le disait encore « sans
  README ». Fichiers frères directs : `../shield.py` (base `ShieldLayer` +
  `Shield`), `../presets.py` (composition).

## Limites connues

> **État au 2026-09-14 — les quatre limites ci-dessous sont fermées par #2095.**
> Le relevé qui suit est conservé comme mesure datée (2026-09-11) ; ces entrées
> ne décrivent plus l'état courant.
>
> - **Repli `score=0.0`** : la couche **lève** désormais. Sans clé →
>   `LLMValidatorUnavailable` (`llm_validator.py:87-91`) ; panne du provider →
>   l'exception d'origine remonte avec son type (aucun `except` dans la couche).
>   C'est `Shield.validate_input` qui décide selon `fail_open`, et le nom de
>   l'erreur est porté par `LayerResult.error_type` (`shield.py:32`).
> - **Sans `api_key`** : plus de score silencieux — même exception nommée.
> - **Appel synchrone** : `_invoke_ai_shield` déporte l'appel hors de la boucle
>   d'événements (`invoke_callables.py:10416`). L'ABC `ShieldLayer.validate`
>   reste synchrone — c'est le **seul** point frontière async de production qui
>   est déporté, pas les 41 autres sites du même fichier qui suivent déjà ce
>   motif.
> - **Verdict sans effet** : un verdict `blocked` rend la phase **terminale**
>   (`workflow_dsl.py:987`, helper `:730`) ; les phases dépendantes sont
>   SKIPPED et le motif nomme le bouclier (`:541`), pas la classification
>   #1909 qui emprunte le même chemin.

- Repli « propre » sur erreur générique : une exception du validateur LLM
  retourne `score=0.0` (`llm_validator.py:159-165` d'alors) alors que le preset
  `strict` pose `fail_open=False` (`presets.py:65`) — une panne du LLM fait
  passer un texte non analysé. Seul l'épuisement de budget lève nommément
  (#1929).
- Sans `api_key`, `LLMValidatorLayer` retournait systématiquement score 0,0
  — même conséquence silencieuse.
- Appel LLM **synchrone** dans `validate` (client `openai.OpenAI` bloquant)
  invoqué depuis le pipeline async — bloquait la boucle d'événements pendant
  la classification.
- Un texte bloqué par le bouclier n'interrompait pas le pipeline :
  `_invoke_ai_shield` enregistrait le verdict et poursuivait.

**Résidu hors #2095** : le double import des deux portes (`ImportError` non
capturé à la frontière REST) reste réel et n'est pas traité ici ; il est nommé
dans la PR #2095 pour un suivi coordinateur.
