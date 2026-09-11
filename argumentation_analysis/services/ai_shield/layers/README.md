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
| `LLMValidatorLayer` | `llm_validator.py:22` | classification de sécurité par LLM (jailbreak, injection, biais, manipulation, ingénierie sociale) ; entrée plafonnée à 2000 caractères, `max_completion_tokens=200` |
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
  (`core/shared_state.py:613`, append `invoke_callables.py:10389-10390`) —
  champ écrit mais **jamais lu en production** (aucun lecteur hors tests).

## Statut d'intégration

| Famille | Statut | Preuve |
|---|---|---|
| `HeuristicLayer` | **actif** (opt-in) | composé dans les 3 presets le mobilisant (`presets.py:38,48-49,69-70`), exécution production `_invoke_ai_shield` (`invoke_callables.py:10339`) |
| `LLMValidatorLayer` | **actif** (opt-in) | composé dans `advanced` et `strict` (`presets.py:49,70`) ; nécessite `api_key` sinon repli score 0,0 (`llm_validator.py:71-75`) |
| `OutputFilterLayer` | **actif** (opt-in) | composé dans `advanced`, `output_only` et `strict` (`presets.py:50,58,71`) |

« Actif » signifie câblé et exécutable en production via `--shield-preset` ;
le défaut `off` fait qu'aucun run standard n'exécute ces couches.

## Artefacts et lecteurs

`LayerResult` (score, matches détaillés, raison) retourné à `Shield` qui
agrège ; trace et résultats poussés dans `state.ai_shield_results` et
l'entrée de trace du pipeline (`invoke_callables.py:10346,10389-10390`).
Lecteurs : tests uniquement — aucun lecteur production de
`ai_shield_results`.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest \
  tests/unit/argumentation_analysis/test_ai_shield.py -v
```

## Frères et parent

- Parent : [ai_shield/](../) — **sans README** ; fichiers frères directs :
  `../shield.py` (base `ShieldLayer` + `Shield`), `../presets.py`
  (composition).
- Le README parent est prévu par les vagues de rénovation #2088 ; ce fichier
  ne l'anticipe pas.

## Limites connues

- Repli « propre » sur erreur générique : une exception du validateur LLM
  retourne `score=0.0` (`llm_validator.py:159-165`) alors que le preset
  `strict` pose `fail_open=False` (`presets.py:65`) — une panne du LLM fait
  passer un texte non analysé. Seul l'épuisement de budget lève nommément
  (#1929, `llm_validator.py:155-158`).
- Sans `api_key`, `LLMValidatorLayer` retourne systématiquement score 0,0
  (`llm_validator.py:71-75`) — même conséquence silencieuse.
- Appel LLM **synchrone** dans `validate` (`llm_validator.py:79-104`,
  client `openai.OpenAI` bloquant) invoqué depuis le pipeline async —
  bloque la boucle d'événements pendant la classification.
- Un texte bloqué par le bouclier n'interrompt pas le pipeline :
  `_invoke_ai_shield` enregistre le verdict et poursuit
  (`invoke_callables.py:10370-10399`).
