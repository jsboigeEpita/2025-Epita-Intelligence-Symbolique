# `agents/core/reading/` — la première lecture : le zéro-shot devenu producteur (#3395)

Parent : `agents/core/` ([`../README.md`](../README.md)). Enregistrement : [`../../../orchestration/registry_setup.py`](../../../orchestration/registry_setup.py). Consommateurs de production : la sélection par argument ([`../../../orchestration/selection.py`](../../../orchestration/selection.py), `priority_spans=`), le briefing de synthèse ([`../synthesis/deep_synthesis_agent.py`](../synthesis/deep_synthesis_agent.py)) et les **actes II–III** ([`../../../reporting/restitution/act2_narrative_plugin.py`](../../../reporting/restitution/act2_narrative_plugin.py), [`act3_conclusion_plugin.py`](../../../reporting/restitution/act3_conclusion_plugin.py) — tranche actes de #3395). Gardes : `tests/unit/argumentation_analysis/test_first_reading_3395.py` (22 témoins) et `test_first_reading_acts_3395.py` (10).

## Rôle et frontière

2 modules (482 lignes) — l'axe **« ce que le texte fait »**, dit par la même lecture entière que le zéro-shot de référence : sur le panel v1 (`#2841`), ce lecteur porte le geste définisseur du document sur 8 documents sur 10 où aucune ligne du rendu ne le porte. Le producteur écrit `state.defining_moves` **avant** la descente, et trois consommateurs de production le lisent : les unités qui recouvrent un geste passent d'abord dans le budget d'examen (`select_for_budget(priority_spans=…)`), le briefing de synthèse porte les gestes ou **dit l'absence**, et les **actes II–III** reçoivent le même bloc étiqueté dans leur prompt (`first_reading` sur le bundle d'evidence, rendu par `first_reading_note` — jamais reformulé par l'acte).

Ce n'est **pas** un `BaseAgent` : la logique vit dans un module à LLM injectable, exposé par le seam standard — `_invoke_first_reading` (`orchestration/invoke_callables.py`), enregistré une fois (`first_reading_service`, `registry_setup.py`), écrit par `CAPABILITY_STATE_WRITERS` (`state_writers.py`), demandé par la phase **racine** `first_reading` des workflows standard **et spectacular** (le panel tourne spectacular — `run_corpus_batch.py` — donc le producteur vit là aussi, R1142), dont `hierarchical_fallacy` dépend. La phase est `optional` : absente, la sélection est octet-identique.

## La ligne que le paquet garde : des gestes, jamais des verdicts

- **`basis="first_reading"`** sur chaque geste — étiquette **distincte** de `model_knowledge` (#3377) : ce que le TEXTE fait, pas ce que le modèle sait. Les deux producteurs ne sont pas interchangeables.
- **Citation verbatim, vérifiée** : chaque geste porte une citation du document, contrôlée en mémoire par la règle de #3389 (`normalised_quote_in`) ; une citation que le document ne porte pas est **écartée et comptée** (`dropped_quotes`). Rien n'est gardé « parce que le modèle a probablement copié ».
- **Aucun verdict** : pas de sophisme, pas de score, pas de jugement de stratégie — le prompt le dit, pour qu'aucune ligne ne puisse se lire comme le verdict d'une lunette.
- **Portée mesurée, pas déclarée** : `read_scope.whole_document` n'est vrai que si la fenêtre couvre tout le texte, et les rédacteurs impriment la portée réelle.

## Composants publics

**`first_reading.py`** (442 l.) — le producteur de `state.defining_moves`

- `build_first_reading(state, llm_callable=None)` : **UN** appel, **texte entier sans coupe** (`FIRST_READING_WINDOW = 0` : la coupe du bras zéro-shot, `max_chars=0`, règle 4 de #2841 — les quatre documents les plus longs du panel, 47 644 à 179 139 caractères, dépassaient l'ancienne borne de 30 000), statut discriminé `ok` / `no_llm` / `parse_error` / `llm_error` — un échec **atteint l'état** (R1142 : le rédacteur persiste le statut discriminé au lieu de le sauter) ;
- `DefiningMove` : `kind` en **vocabulaire fermé** (8 valeurs, synonymes français projetés, inconnu → `other`), `reading` d'une ligne, `quote` verbatim, `offset` (position calculée, jamais affirmée) ;
- `defining_moves(state)` / `defining_move_spans(state)` : les gestes triés par offset (non positionnés en fin), et leurs intervalles — ce que la sélection consomme sous la règle de recouvrement R1142 : **intersection d'intervalles** quand l'étendue de l'unité est connue (`source_quote`), sinon le **départ le plus proche avant la citation** (le passage où elle se trouve) — jamais « le départ tombe dans la citation » seul, qui laissait le consommateur inerte sur quatre gestes sur cinq dans les documents longs ;
- `first_reading_note(state)` : **le** producteur de la formulation du briefing — synthèse **et actes II–III** (le champ `first_reading` du bundle d'evidence de chaque acte porte ce bloc tel quel), avec **trois absences distinctes** (`no_llm` → « non enregistrée », `ok` sans geste → « aucun geste » **en suivant `read_scope.whole_document`**, échec → « lecture en échec ») — un rédacteur n'a jamais à deviner dans quel cas il est. La nature s'imprime en **français** dans la note (la clé anglaise reste dans l'état). Un état sans enregistrement rend la chaîne vide : l'acte omet la section, il n'invente pas de vocabulaire de producteur.

**`__init__.py`** (40 l.) — ré-exportations.

## Frontière d'export

`sanitize_state` réduit `defining_moves` à un résumé en comptes (`_STRUCT_LIST_SCRUB`) : les citations sont des spans verbatim du document, aucun libellé ne franchit la frontière.
