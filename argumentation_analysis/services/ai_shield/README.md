# `argumentation_analysis/services/ai_shield/` — un bouclier adversarial de filtrage en profondeur, à trois voies d'activation toutes opt-in et sans lecteur aval

Paquet de 7 modules `.py` (774 lignes) plus un unique README de sous-dossier (99 lignes), soit 873 lignes sur 8 fichiers. `shield.py` porte le contrat commun (`ShieldLayer`, `LayerResult`, l'agrégateur `Shield` en politique `fail_open`) ; `presets.py` compose trois couches en 4 profils nommés ; `layers/` ne contient que les trois couches. L'assemblage est branché sur **deux routes REST** et sur une phase de workflow — mais les **trois** voies sont inertes par défaut (`--shield-preset off` côté CLI, `shield_preset="off"` côté REST), et le champ d'état qu'il écrit n'a **aucun lecteur de production**.

## Rôle et frontière

Le paquet est un **filtre en profondeur** : `Shield.validate_input` (`shield.py:112`) fait passer un texte dans une liste ordonnée de couches, chacune rendant un score 0.0–1.0, et **s'arrête à la première couche qui dépasse son seuil** (`shield.py:134-144` — `return` anticipé). Conséquence structurelle : `layer_results` est **partiel**, les couches suivantes n'ont pas tourné. `Shield.validate_output` (`shield.py:170`) réemprunte le même chemin en passant `direction="output"`, seule différence.

**Ce qu'il ne fait pas** — c'est la frontière :

- il ne **stoppe rien** : `_invoke_ai_shield` retourne un dict et ne lève pas (`invoke_callables.py:10339-10406`) ; la phase est `optional=True` (`unified_pipeline.py:317`) ; côté REST la réponse *décrit* le blocage, c'est l'appelant qui décide ;
- il n'écrit **aucun fichier sur disque** ;
- il n'est pas un composant du registre de capacités « Lego » au sens d'un agent : `service_class=type("AIShieldService", (), {})` est une **classe vide** (`registry_setup.py:742`), toute l'exécution passe par `invoke=_invoke_ai_shield` (`:752`).

Frontière interne nette : `layers/` ne contient que les trois couches ; la composition (`Shield`, `load_preset`, `LayerResult`, `ShieldLayer`) vit à la racine. Le paquet est **isolé** : il n'importe rien d'autre de `services/` et rien de `services/` ne l'importe.

Origine : « Recreated from project 2.5.6 soutenance description » (`__init__.py:6`) — **réimplémentation**, pas une intégration d'un projet étudiant.

## Composants publics

`__init__.py` : **984 octets**, 29 lignes. Il ré-exporte 4 noms (`__init__.py:29`) — `Shield`, `ShieldResult`, `ShieldLayer`, `load_preset`.

| Composant | Fichier:ligne | Rôle | Statut mesuré |
|---|---|---|---|
| `Shield` | `shield.py:76` | agrégateur multi-couches, politique `fail_open` | **vivant, opt-in** — 2 appelants de production (`invoke_callables.py:10362`, `api/shield_endpoints.py:98`) |
| `ShieldLayer` | `shield.py:41` | ABC : `validate(text, **kw) -> LayerResult` + `_make_result` (`:62`) | **surface interne** — 0 usage hors paquet/tests |
| `LayerResult` | `shield.py:16` | dataclass d'une couche (`score`, `passed`, `details`, `reason`) | **surface interne**, et **absent de `__all__`** alors que c'est le type de retour de tout `ShieldLayer.validate` |
| `ShieldResult` | `shield.py:27` | dataclass agrégée + propriété `passed` (`:36`) | **surface interne** — 0 usage hors paquet/tests |
| `load_preset` | `presets.py:21` | fabrique de profils | **vivant, opt-in** — 2 appelants de production (mêmes sites) |
| `HeuristicLayer` | `layers/heuristic.py:59` | regex/mots-clés, coût nul ; scores injection +0.4 (`:105`), biais +0.3 (`:113`), manipulation +0.5 (`:125`), motifs custom +0.3 (`:133`), plafond 1.0 (`:135`) | composé dans `basic`/`advanced`/`strict`, jamais instancié hors paquet/tests |
| `LLMValidatorLayer` | `layers/llm_validator.py:22` | classification sécurité par LLM ; entrée plafonnée à 2000 car. (`:101`), `max_completion_tokens=200` (`:104`) | composé dans `advanced`/`strict`, jamais instancié hors paquet/tests |
| `OutputFilterLayer` | `layers/output_filter.py:55` | filtre de **sortie** ; fuite de prompt système +0.5 (`:100`), identifiants +0.6 (`:115`), PII +0.3/match (`:128`), chemins +0.2 (`:137`) | composé dans `advanced`/`output_only`/`strict`, jamais instancié hors paquet/tests |

`layers/__init__.py` (11 lignes) ré-exporte les trois couches (`layers/__init__.py:11`).

## Points d'entrée valides

Il y a **trois** voies d'activation de production, pas deux — dont **deux routes REST**.

1. **Phase de workflow via CLI (opt-in).** `run_orchestration.py:447-451` déclare `--shield-preset` avec `choices=["off","basic","advanced","output_only","strict"]`, défaut `off` (`:451`). Le `shield_config` n'est construit que si le preset diffère de `off` (`:214-218`), avec `"fail_open": shield_preset != "strict"` (`:217`). `unified_pipeline.py:311` teste `context.get("shield_config")` et injecte alors une phase `shield` **en tête de DAG** (`:313-318`, `optional=True` à `:317`), résolue par capacité `input_validation` vers `ai_shield_service` (`registry_setup.py:740-753`) et exécutée par `_invoke_ai_shield` (`invoke_callables.py:10339`). La valeur est réellement transmise par `run_orchestration.py:879`.
   ```bash
   python argumentation_analysis/run_orchestration.py --file <f> --shield-preset advanced
   ```
2. **Route REST directe.** `POST /api/shield/validate` — `@shield_router.post("/validate", ...)` (`api/shield_endpoints.py:71`) sur `APIRouter(prefix="/shield")` (`:25`), monté `app.include_router(shield_router, prefix="/api")` (`api/main.py:102`). Elle appelle `load_preset` (`:98`) puis `validate_output` (`:112`) ou `validate_input` (`:114`) et rend un `ShieldValidateResponse` (`:59-65`). C'est la **seule** voie qui exerce `validate_output`.
3. **Route REST indirecte : `POST /api/workflow/custom`** — `@proposal_router.post("/workflow/custom", ...)` (`api/proposal_endpoints.py:200`), monté `app.include_router(proposal_router, prefix="/api")` (`api/main.py:100`). Le corps porte `shield_preset` (`api/proposal_models.py:63`, `Literal["off","basic","advanced","output_only","strict"]`) ; si le preset diffère de `off`, la route construit `context["shield_config"] = {"preset": request.shield_preset}` (`api/proposal_endpoints.py:222-223`) et le passe à `run_unified_analysis(..., context=context or None)` (`:273-277`, signature `unified_pipeline.py:138-143`). C'est la **même** phase qu'en (1), atteinte par HTTP et non par le CLI.

Aucun exécutable propre au paquet : `grep __main__` sur `ai_shield/` = 0.

## Amont / aval

- **Amont (dépendances inter-paquets)** — deux, toutes deux seulement dans `LLMValidatorLayer` : `core/reading_window.py:130` (`selected_text`, importé `llm_validator.py:13`, appelé `:101`) et `core/utils/llm_completion_guard.py:26` (`assert_not_reasoning_starved`, importé `:14-17`, appelé `:111`). Le client `openai` est importé **au moment de l'appel** (`llm_validator.py:79`). Les couches `heuristic` et `output_filter` n'ont **aucune** dépendance hors `re`/`typing` — elles sont hermétiques.
- **Amont (assemblage)** : `registry_setup.py:736-753` (déclaration du service), `registry_setup.py:67` (import de `_invoke_ai_shield`), `invoke_callables.py:178` (liste de noms exportés), `unified_pipeline.py:311-330` (injection de phase), `api/main.py:100,102` (montage des deux routeurs), `api/proposal_endpoints.py:222-223` (construction du contexte REST).
- **Aval écrit** : `state.ai_shield_results` (`core/shared_state.py:613`), alimenté par `invoke_callables.py:10390` sous garde `hasattr` (`:10389`), plus une entrée de trace `phase="shield"` / `agent="AIShield"` (`:10391-10399`).
- **Aval lu** : **personne en production.** Les seules lectures de `ai_shield_results` sont `tests/unit/api/test_shield_endpoints.py:127,130-131` et une liste de champs tolérés dans `tests/unit/argumentation_analysis/evaluation/test_sanitize_coverage_guard_1702.py:575`. Le champ est sérialisé dans les dumps d'état — **9 fichiers `analysis_kb/state_dumps/state_full_*.json` le portent, les 9 avec la valeur `[]`** : jamais alimenté dans ces runs.

## Statut d'intégration

Question décisive — *est-il traversé par du trafic de production, ou seulement appelable ?* **Seulement appelable.** Les trois voies existent et sont correctement câblées, mais chacune exige une activation explicite, et aucune n'a de trace d'exécution dans les artefacts disponibles.

| Surface | Statut mesuré | Ancrage |
|---|---|---|
| `Shield` / `load_preset` | **vivant, opt-in** — 2 appelants production | `invoke_callables.py:10362`, `api/shield_endpoints.py:98` |
| `HeuristicLayer` | **câblé** dans `basic`, `advanced`, `strict` | `presets.py:41,50,70` |
| `LLMValidatorLayer` | **câblé, mais silencieusement inerte sans clé** | `presets.py:51,71` ; repli score 0.0 `llm_validator.py:70-75` |
| `OutputFilterLayer` | **câblé** dans `advanced`, `output_only`, `strict` | `presets.py:52,61,72` ; seule voie REST qui l'exerce : `api/shield_endpoints.py:112` |
| capacité `input_validation` | **demandée** (1 demandeur) | `unified_pipeline.py:316` |
| capacités `output_filtering`, `adversarial_protection` | **déclarées sans demandeur de production** | déclarées `registry_setup.py:745-746` ; seuls demandeurs = `tests/unit/api/test_shield_endpoints.py:50-64` |
| `Shield.get_config` | **déclaré sans consommateur** | `shield.py:178` — 0 site hors paquet/tests |
| `Shield.add_layer` | **déclaré sans consommateur** | `shield.py:107` — seul appelant `tests/unit/argumentation_analysis/test_ai_shield.py:252` |
| `ShieldLayer` / `ShieldResult` / `LayerResult` | **surface interne** | 0 usage hors paquet et tests |
| `ai_shield_results` | **écrit, jamais lu en production** | écrit `invoke_callables.py:10390`, déclaré `core/shared_state.py:613` |
| 9 présets d'état | **tous vides** | `analysis_kb/state_dumps/state_full_*.json` — `"ai_shield_results": []` |

Défauts inactifs : `--shield-preset off` (`run_orchestration.py:451`) et `shield_preset="off"` (`api/proposal_models.py:63`) — **aucun run standard n'exécute le bouclier**, et un run explicite n'en laisse pas de trace lisible (voir `ai_shield_results` ci-dessus). Le verdict est donc « intégré et exécutable, jamais exécuté par défaut ».

## Artefacts et lecteurs

- **Artefact produit (phase)** : le dict de verdict — `shield_available`, `blocked`, `overall_score`, `passed`, `reason`, `layer_results` (`invoke_callables.py:10370-10385`) — empilé dans `state.ai_shield_results` **sans lecteur de production**.
- **Artefact produit (REST)** : `ShieldValidateResponse` (`api/shield_endpoints.py:59-65`), rendu au client HTTP. C'est le seul « consommateur » effectif du score, et il est hors du dépôt.
- **Trace d'état** : entrée `phase="shield"`, `agent="AIShield"`, résumé `BLOCKED|PASSED (score=…, N layers)` (`invoke_callables.py:10391-10399`) — c'est la seule lecture humaine possible d'un blocage, dans l'analyse d'état.
- **Aucun fichier produit par le paquet.** Les dumps d'état qui portent le champ sont écrits par l'orchestration, pas par le service.

## Tests représentatifs

**55 tests ciblant le paquet, sur 4 fichiers** (la fiche de départ n'en comptait que 2 sur 51 et manquait deux files de régression qui visent explicitement les couches).

| Fichier | Tests | Couverture | Nature |
|---|---|---|---|
| `tests/unit/argumentation_analysis/test_ai_shield.py` | 33 | les 3 couches, les 4 presets (`:280-303`, dont `load_preset("nonexistent")` → `ValueError` `:296-299`), API fluente `add_layer` (`:249-252`), `get_config` (`:257-262`) | contrat des feuilles |
| `tests/unit/api/test_shield_endpoints.py` | 18 | résolution des 3 capacités (`:38-66`), `_invoke_ai_shield` (`:73-124`), écriture d'état (`:124-131`) | contrat d'assemblage — **n'exerce pas la route HTTP**, seulement le callable et le registre |
| `tests/unit/argumentation_analysis/core/utils/test_llm_completion_guard_1929.py` | 2 (`:84`, `:108`) | le site `ai_shield/llm_validator` : budget « starved » → exception nommée, et complétion vide légitime → passe | régression du mode de panne |
| `tests/unit/argumentation_analysis/test_str_as_sequence_family_2041.py` | 2 (`:46`, `:65`) | normalisation d'un `categories` scalaire en liste à un élément, et non-régression du cas liste | régression du mode de panne |

Contrat vs chemin réel : **aucun test de bout en bout d'une voie d'activation**. La propagation du contexte CLI n'est vérifiée que par la reconstruction du `context` dans le test (`tests/unit/argumentation_analysis/test_fallacy_tier_selector.py:158`, classe `TestShieldPresetContext`) — il **rejoue la logique** au lieu d'appeler la route ou la CLI. Aucune route HTTP (`/api/shield/validate`, `/api/workflow/custom`) n'est exercée par un `TestClient` : `api/shield_endpoints.py` est importé mais ses fonctions ne sont jamais appelées par les tests.

## Frères et parent

- **Parent** : `argumentation_analysis/services/` — son README (`services/README.md`, **324 lignes**) ne contient **aucune** occurrence mot-entier de `ai_shield` ni de « AI Shield » (seul `grep -i shield` remonte 1 hit, le badge `img.shields.io` de la ligne 286 — faux positif).
- **README du paquet** : **créé avec ce fichier** ; avant lui, seul `layers/README.md` (99 lignes) existait, et il ne couvrait que les couches.
- **Frères directs** (mêmes couches de service) : `jtms/` + `jtms_service.py`, `mcp_server/`, `web_api/`, `fetch_service.py`, `cache_service.py`, `local_llm_service.py`, `semantic_index_service.py`, `speech_transcription_service.py`.
- **Consommateur dans un autre paquet** : `core/utils/llm_completion_guard.py` est importé par `llm_validator.py:14` — le seul lien `core/utils` ↔ `ai_shield`. `core/reading_window.py` en est un second (`:13`).
- **Absent** de tout autre paquet de `services/` et de `interface_web/` (0 occurrence de `shield` utile dans `interface_web/`).

## Limites connues

Anomalies **relevées, non corrigées**, chacune ancrée.

**Suivi** : les items **1, 2, 3, 5, 8, 9** sont portés par **#2144** (divergence CLI↔REST sur
`strict`, paramètre `fail_open` perdu, `ReasoningStarvedError` dégradée en chaîne, route
directe non authentifiée par défaut, auth lue une fois). Les items **4, 7, 10, 11**
recouvrent **#2095** (repli interne masquant une panne, appel LLM synchrone, verdict sans
effet, `ai_shield_results` sans lecteur). Les items **6, 12, 13** restent locaux.

1. **Docstring contredisant le code (presets)** — l'en-tête `presets.py:3-7` annonce 3 profils (`basic`, `advanced`, `output_only`) et la docstring de `load_preset` en cite 3 (`presets.py:29`) ; le code en implémente **4**, `strict` existant (`presets.py:65-74`) et étant un choix CLI valide (`run_orchestration.py:450`).
2. **Paramètre ignoré** — `load_preset(preset_name, api_key, fail_open)` propage `fail_open` dans `basic`/`advanced`/`output_only` (`presets.py:38,47,58`) mais écrit le **littéral `False`** pour `strict` (`presets.py:68`) : l'appelant ne peut pas rendre `strict` tolérant, l'argument est silencieusement perdu.
3. **Divergence CLI ↔ REST sur `strict`** — le CLI pose `"fail_open": shield_preset != "strict"` (`run_orchestration.py:217`), donc `strict` arrive **fail-closed** ; la route `/api/workflow/custom` ne pose **que** `{"preset": ...}` (`api/proposal_endpoints.py:223`), si bien que `_invoke_ai_shield` retombe sur son défaut `fail_open=True` (`invoke_callables.py:10357`) : le même preset `strict` est **fail-open via REST** et fail-closed via CLI.
4. **Repli « propre » qui masque une panne** — sans clé API, `LLMValidatorLayer` retourne `score=0.0` (`llm_validator.py:70-75`) ; sur exception générique, idem (`:159-165`). Ces replis sont **internes à la couche** et ne passent pas par le `fail_open` du `Shield` : ils rendent un `LayerResult` avec `passed=True`, donc **passent**. Une panne LLM fait traverser un texte non analysé — y compris sous `strict`, dont le `fail_open=False` (`presets.py:68`) ne s'applique qu'aux exceptions remontant au `Shield`.
5. **Exception nommée rattrapée à l'étage au-dessus** — `ReasoningStarvedError` est bien re-levée (`llm_validator.py:154-158`) mais `Shield.validate_input` attrape `Exception` (`shield.py:146`) et la convertit en `LayerResult(details={"error": ...})` (`:148-154`) ; le nom survit comme **chaîne**, pas comme exception. Un appelant qui n'inspecte pas `details` ne peut pas distinguer « starved » de « pas de menace ».
6. **Non-export de `LayerResult`** — `__init__.py:29` liste 4 noms sans `LayerResult`, alors que c'est le type de retour de tout `ShieldLayer.validate` et l'élément de `ShieldResult.layer_results` : un consommateur externe doit importer `...ai_shield.shield.LayerResult`.
7. **Appel LLM synchrone dans une voie async** — `llm_validator.py:79-104` instancie un client `openai.OpenAI` bloquant ; la phase est appelée depuis `async def _invoke_ai_shield` (`invoke_callables.py:10339`) — la boucle d'événements est bloquée pendant la classification.
8. **Auth de la route directe lue une seule fois** — `api/shield_endpoints.py:29` capture `SHIELD_ENDPOINT_TOKEN` au niveau module, alors que le commentaire adjacent (`:30-31`) justifie la re-lecture **par requête** de `OPENAI_API_KEY` (« the key may rotate at runtime without restart », appliqué `:95`). Le fichier se contredit dans le même bloc ; le token, lui, exige un redémarrage.
9. **Route directe ouverte par défaut** — si `SHIELD_ENDPOINT_TOKEN` est absent, `_verify_token` retourne sans lever (`api/shield_endpoints.py:36-37`) ; et `fail_open` vaut `True` par défaut côté requête (`:49`) : un appelant qui ne remplit rien obtient un 200 non bloquant.
10. **Verdict sans effet** — un texte bloqué n'interrompt ni le pipeline (phase `optional=True`, `unified_pipeline.py:317`) ni le flux REST (la réponse décrit le blocage, l'appelant décide).
11. **`ai_shield_results` déclaré-jamais-lu** (`core/shared_state.py:613`) — le rapport d'exécution ne peut pas relire un blocage depuis l'état ; les 9 dumps qui portent le champ le portent vide.
12. **Docs d'intégration périmées ou incomplètes** :
    - `layers/README.md:35-40` présente la CLI comme **la** voie d'activation (« Activation production : CLI `run_orchestration.py --shield-preset` ») sans mentionner **aucune** des deux routes REST. Recence vérifiée : la route directe a été câblée par `5f460c54` (2026-06-02, « wire ai_shield service into pipeline + REST endpoint (#841, #842) »), ce README écrit par `5e98b6dc` (2026-09-11, #2093) — trois mois plus tard, et il omet encore la seconde voie **et** la route indirecte.
    - `docs/architecture/design_specs/TRACK-03_shield_preset_selector.md:41` ne recense que `POST /api/shield/validate` comme surface REST ; la route `/api/workflow/custom` n'y apparaît pas non plus.
    - `docs/architecture/NORTHSTAR_GAP_ANALYSIS.md:124` et `:290`, ainsi que `docs/architecture/design_specs/TRACK-03_shield_preset_selector.md:38-40`, citent des **ancres de ligne périmées** (`invoke_callables.py:6393` et `:6118` pour un callable qui est à `:10339` ; `registry_setup.py:660` pour une déclaration à `:740` ; `shared_state.py:452` pour un champ à `:613`). Dérive préexistante, non introduite ici.
    - `docs/reports/integration_audit/A-13_ai_shield.md:69` affirme le service « complètement inutilisable dans le pipeline normal » — démenti par `unified_pipeline.py:311-318` et `run_orchestration.py:447-451`.
13. **Pas de test de bout en bout des voies d'activation** — voir « Tests représentatifs » : la couverture s'arrête au contrat des feuilles et du callable, jamais au chemin HTTP réel.

*Provenance : 2026-09-11, branche `docs/readme/2088-parents`. Écrit par mesure directe du dépôt (lecture de `argumentation_analysis/services/ai_shield/**`, `api/shield_endpoints.py`, `api/proposal_endpoints.py`, `api/proposal_models.py`, `api/main.py`, `argumentation_analysis/orchestration/{registry_setup,invoke_callables,unified_pipeline}.py`, `argumentation_analysis/run_orchestration.py`, `argumentation_analysis/core/{shared_state,reading_window}.py`, `argumentation_analysis/core/utils/llm_completion_guard.py`, `grep` ciblés, `git log`, et comptage `pytest --collect-only`) ; la fiche de départ a été traitée comme hypothèse et quatre de ses affirmations ont été corrigées. Aucun fichier du dépôt modifié hors ce README.*
