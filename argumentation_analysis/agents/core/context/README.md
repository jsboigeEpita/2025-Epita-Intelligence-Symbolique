# `agents/core/context/` — les deux personas : historien et stratège (#3377)

Parent : `agents/core/` ([`../README.md`](../README.md)). Enregistrement : [`../../../orchestration/registry_setup.py`](../../../orchestration/registry_setup.py). Consommateurs : `nl_to_logic` et `act1_framing` ([`../../../reporting/restitution/act1_framing_plugin.py`](../../../reporting/restitution/act1_framing_plugin.py)). Garde d'invariant : `tests/unit/argumentation_analysis/orchestration/test_one_capability_surface_1842.py`.

## Rôle et frontière

3 modules (667 lignes) — l'axe **« ce que le modèle sait du monde, dit avant l'analyse »** : un **historien** situe le document (période, lieu, acteurs, enjeux d'alors), un **stratège** énonce la configuration du jeu (joueurs, options, ordres de préférence). Ils écrivent dans l'état **avant** l'analyse, chacun avec **un consommateur de production** — un producteur que personne ne lit est le défaut `act1_framing` que l'issue nomme.

Ce ne sont **pas** des `BaseAgent` : la logique vit dans des modules à LLM injectable, exposés par le seam standard — `_invoke_historical_context` / `_invoke_strategic_read` (`orchestration/invoke_callables.py`), enregistrés une fois dans `registry_setup.py`, écrits par `CAPABILITY_STATE_WRITERS` (`state_writers.py`), demandés par les phases `historian` et `strategist` (`workflows.py`).

## La ligne que le paquet garde : `basis="model_knowledge"`

Tout ce qu'une persona écrit porte l'étiquette `basis="model_knowledge"`, et elle est posée par `stamp_basis` (`__init__.py`) **après** la réponse du modèle : un modèle qui répond `"basis": "text"` ne peut pas blanchir une déduction en citation. Le rendu dit les mêmes mots partout — `historian.context_note` produit **une** formulation (« SITUATION HISTORIQUE — SAVOIR DU MODÈLE, jamais le contenu du texte ») que le traducteur NL→KB et le prompt de l'Acte I partagent : deux lecteurs ne peuvent pas diverger sur ce que ça couvre.

## Composants publics

**`historian.py`** (276 l.) — le producteur de `state.historical_context`

- Prompt anglais, sortie JSON française : `situation` + `items[{claim, confidence, supports}]` ;
- `MAX_ITEMS` (8), `_PROMPT_MAX_STAKES` (6), `_clamp_confidence` (illisible ⇒ 0,0) ;
- `build_historical_context(state, llm_callable=None)` : lit via le sélecteur #1737 (`selected_text`, `LLM_EXTRACTION_WINDOW`, site `"historian"`), statut discriminé `ok` / `no_llm` / `parse_error` / `llm_error` ;
- `context_note(state)` : la note que le consommateur lit — `""` quand il n'y a rien (une note vide qui afficherait un en-tête annoncerait une provenance qu'elle n'a pas).

**`strategist.py`** (321 l.) — le producteur de `state.strategic_read`

- Le modèle **énonce** la configuration (joueurs, options, classements complets) ; l'issue du jeu est **calculée**, jamais affirmée ;
- `compute_manipulability(preferences, options)` : gagnant de Condorcet, pivots d'un joueur (« vote stratégique »), coalitions de deux (« fausse coalition ») — via `governance.social_choice.condorcet_winner`, la forme adaptée du prototype étudiant 2.1.6 (aléa numpy retiré) ;
- Le **bribery** n'est pas implémenté : il exige un budget que le profil ne porte pas, et en inventer un serait la fabrication que l'issue interdit ;
- `_normalise_ballot` : un classement partiel est complété **déterministement** (options nommées d'abord, le reste dans l'ordre déclaré).

**`__init__.py`** (70 l.) — `MODEL_KNOWLEDGE_BASIS`, `MODEL_KNOWLEDGE_LABEL_FR`, `TEXT_BASIS`, `stamp_basis` (jamais de mutation de l'item de l'appelant).

## Consommateurs (le paquet n'existe que par eux)

| producteur | consommateur | ce qu'il en fait |
|---|---|---|
| `historian` → `historical_context` | phase `nl_to_logic` | `context_note` ajoutée au prompt SYSTEM après le contrat logique ; note vide ⇒ **aucun ajout** (prompt octet-identique) |
| `strategist` → `strategic_read` | phase `act1_framing` | l'acte **reprend** la lecture calculée (« tu la REPRENDS et la rends lisible ; tu n'en produis pas une autre ») ; lignes étiquetées `Gagnant CALCULÉ (Condorcet)` / `Pivot d'un joueur` / `Coalition` |

## Privacy

Les deux lectures sont de l'analyse aval : `sanitize_state._STRUCT_LIST_SCRUB` les réduit à des comptes (`items`, `players`, `options`), avec canaris plantés dans la garde de couverture. Les deux sites de fenêtre portent des labels français dans le relevé de lecture (`reading_record.SITE_LABELS_FR` : « historien — situation du document », « stratège — lecture stratégique ») et sont inscrits au registre de la garde de recensement #2850.
