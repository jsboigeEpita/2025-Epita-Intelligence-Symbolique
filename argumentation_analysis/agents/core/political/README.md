# `agents/core/political/` — extracteur d'enjeux, producteur unique du workflow spectacular

## Rôle et frontière

2 fichiers : `__init__.py` (0 octet, aucun ré-export) et `stakes_extractor.py` (**176 lignes**, mesuré `wc -l`). Le paquet n'expose **rien** par son `__init__` — le seul chemin d'accès est l'import direct du module (cf. *Points d'entrée*).

Le module porte un **spécialiste** unique (Track TT #723) : à partir des arguments déjà extraits et du texte source, il fait produire par LLM quatre éléments — enjeux, parties prenantes, registre rhétorique, arène discursive. Ce n'est pas un `BaseAgent` : pas de plugin SK, pas d'entrée `CapabilityRegistry` propre — il est invoqué par la couche orchestration.

**Frontière** : le module ne lit jamais l'état partagé et n'y écrit jamais. Il reçoit arguments + métadonnées + texte, retourne un dict. La persistance appartient à `_write_stakes_to_state` (`orchestration/state_writers.py:2244`), l'accès LLM/état à `_invoke_stakes_extractor` (`orchestration/invoke_callables.py:10231`).

## Composants publics

| Composant | `file:line` | Nature |
|---|---|---|
| `StakesExtractor` | `stakes_extractor.py:63` | classe ; unique méthode `async extract(...)` |
| `EXTRACTION_PROMPT` | `stakes_extractor.py:35` | prompt JSON strict (4 clés) |
| `_default_chat_completion` | `stakes_extractor.py:22` | appel LLM par défaut, *injectable* |
| `logger` | `stakes_extractor.py:19` | logger nommé `StakesExtractor` |

**Schéma de sortie** (clés et types seulement — aucun contenu, discipline dataset) :

- `stakes` : liste (≤ 10, tronquée l. 160) d'objets `{stake_type: str (11 valeurs), description: str, evidence_indices: list[int]}` ;
- `stakeholders` : liste (≤ 10, l. 161) d'objets `{name: str, role: str (6 valeurs), stance: str (4 valeurs), evidence_indices: list[int]}` ;
- `rhetorical_register` : `str` (8 valeurs) ;
- `discursive_arena` : `str` libre.

Toute erreur de parsing ou d'appel LLM est avalée en `logger.warning` et renvoie le dict vide (l. 171-174) — l'appelant ne peut pas distinguer « rien à extraire » de « panne » sur ce canal.

## Points d'entrée valides

**Un seul, et c'est la couche orchestration.** Aucun consommateur n'appelle `StakesExtractor` directement en production.

```python
# stakes_extractor.py:66-76 — signature réelle
async def extract(
    self,
    arguments: List[Dict[str, Any]],
    source_metadata: Dict[str, str],
    raw_text: str = "",
    llm_client: Optional[Any] = None,
    determinism_params: Optional[Dict[str, Any]] = None,
    deanonymized: bool = True,
    model_id: str = "",
    llm_call: Optional[Callable[..., Awaitable[Any]]] = None,
) -> Dict[str, Any]:
```

Le wrapper de production, lui, a la signature d'un invoke de phase : `_invoke_stakes_extractor(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]` (`invoke_callables.py:10231`). Il construit la liste d'arguments depuis `state.identified_arguments` (dict `{arg_id: description}` → `[{"text": desc}]`, l. 10261-10267), résout le client via `_get_openai_client()` en **dépaquetant le tuple** (l. 10285) et injecte `_guarded_chat_completion` (#708, plafond anti-emballement, l. 10304).

## Amont / aval

**Amont**
- `argumentation_analysis/core/reading_window.py:130` — `selected_text(raw_text, 3000, "stakes_extractor")` (`stakes_extractor.py:119`) : le texte est tronqué à 3000 caractères et la sélection est enregistrée sur l'état partagé (#1737) ;
- `UnifiedAnalysisState.identified_arguments` / `raw_text` / `source_metadata` (`core/shared_state.py`) — lus par le wrapper, pas par le module ;
- `_get_openai_client()` + `_get_determinism_params()` + `_guarded_chat_completion` — injectés par le wrapper.

**Aval — le producteur EST ce module.** Chaîne mesurée :

1. phase `stakes`, `capability="stakes_extraction"`, `depends_on=["quality"]`, `optional=True`, `timeout_seconds=120` — `orchestration/workflows.py:920-926`, dans `build_spectacular_workflow()` (**683-1066**) ;
2. résolution `find_for_capability(phase.capability)` puis `provider.invoke(...)` — `orchestration/workflow_dsl.py:806` et `:861/:887` ;
3. service `stakes_extractor_service`, `capabilities=["stakes_extraction", "stakeholder_analysis"]`, `invoke=_invoke_stakes_extractor` — `orchestration/registry_setup.py:721-730` ;
4. `_invoke_stakes_extractor` importe et instancie `StakesExtractor` — `invoke_callables.py:10245-10249`.

Clé écrite : **`state.stakes_and_stakeholders`** (4 clés, défaut vide `shared_state.py:604-609`) via `_write_stakes_to_state` (`state_writers.py:2244`), enregistrée sous `CAPABILITY_STATE_WRITERS["stakes_extraction"]` (`state_writers.py:2328`).

Lecteurs de cette clé (production) : `synthesis/deep_synthesis_agent.py:303` → sections 2 et 3 du rapport (`:1514`, `:1536`) ; `reporting/restitution/act1_framing_plugin.py:241` (arène/registre → genre) et `:324` ; `reporting/restitution/appendix.py:345` (ligne `enjeux`, cardinalité seule — privacy HARD) ; export : `evaluation/sanitize_state.py:298` (réduction en comptes).

**Deux sites d'appel production** : le chemin exécuteur (workflow) et le post-traitement conversationnel `orchestration/conversational_orchestrator.py:1574-1604` (gaté par `_budget_allows("stakes_extraction")`, appel direct de l'invoke).

## Statut d'intégration

**actif** (spécialisé, non critique).

Preuves : chaîne capability→service→callable→module complète et nommée ci-dessus ; **1** littéral `capability="stakes_extraction"` en production (`workflows.py:922`) ; **1** import production du module (`invoke_callables.py:10245`) contre **3** fichiers de test ; **1** entrée `CAPABILITY_STATE_WRITERS` (`state_writers.py:2328`) ; **4** lecteurs production de la clé d'état. Non `actif-critique` : la phase est `optional=True` (absence → `SKIPPED`, `workflow_dsl.py:822-833`) et le workflow spectacular est le seul à la porter.

Compte mesuré, méthode et périmètre : `grep -rn` sur `stakes_extractor`, `StakesExtractor`, `stakes_extraction`, `stakes_and_stakeholders` sur tout le dépôt (`--include=*.py`, `__pycache__` exclu), puis `awk`/`grep` pour localiser le `def build_*` encadrant la ligne 921.

## Artefacts et lecteurs

Aucun fichier produit. L'artefact est la clé d'état `stakes_and_stakeholders` (dict 4 clés). Lecteurs : la synthèse profonde (sections 2/3), le cadrage d'Acte I, la table de couverture (`enjeux`, cardinalité) et le sanitizer d'export. Le `to_dict()` du rapport de synthèse (`deep_synthesis_models.py:168`) **ne porte pas** les données d'enjeux brutes — la clé transite par un attribut transitoire (cf. Limites).

## Tests représentatifs

- `tests/unit/argumentation_analysis/test_stakes_extractor.py` (**378 l**) — 4 volets annoncés en tête : unité avec client LLM mocké (`AsyncMock`, voir le piège documenté l. 30-36), initialisation du champ d'état, câblage de l'invoke, intégration `DeepSynthesisAgent` ;
- `tests/unit/argumentation_analysis/orchestration/test_state_writers_stakes_extraction.py` (**112 l**) — l'enregistrement du writer (l. 35-37) et le contrat de forme dict-of-strings → list-of-dicts ;
- `tests/unit/argumentation_analysis/orchestration/test_mute_capabilities_b02.py:123-205` — chemin invoke et forme des arguments ;
- `tests/integration/triage/test_conversational_orchestration_integration.py:62-78` — patch de `_invoke_stakes_extractor` dans le chemin conversationnel.

## Frères et parent

Parent : `agents/core/` — son `README.md` existe mais sa section `## Structure` ne liste que `pm`, `informal`, `pl`, `extract` : elle **omet** `political` (et 9 autres sous-répertoires). Frères du même lot A7 (Epic #2088) : `abc`, `counter_argument`, `debate`, `governance`, `oracle`, `quality`, `synthesis`. `README.md` déjà présents à date : `extract`, `informal`, `logic`, `pl`, `pm`.

## Limites connues

- **La docstring de module contredit le défaut du code, sur un sujet de privacy.** `stakes_extractor.py:10` annonce « outputs pseudonymised references (Speaker_A, Group_X), never raw text », alors que `deanonymized: bool = True` (l. 73) est le défaut et que l'instruction de nommage bascule alors vers les **noms réels** (l. 124-129). Le défaut est cohérent avec l'état de travail déanonymisé (`shared_state.py:598`) et le garde-fou d'export est ailleurs (`sanitize_state.py:298`) — c'est la docstring de ce module qui est périmée, pas le câblage.
- **`_raw_stakes` n'est pas un champ déclaré** de `DeepSynthesisReport` (`deep_synthesis_models.py:126-166`) : il est posé dynamiquement (`deep_synthesis_agent.py:308/310`) et lu par `getattr` (`:1514`). Runtime sain (`@dataclass` sans `__slots__`), mais `to_dict()` l'ignore — toute sérialisation du rapport perd les enjeux silencieusement.
- **La capacité `stakeholder_analysis` n'a aucun demandeur.** Déclarée `registry_setup.py:724`, elle n'apparaît dans aucun littéral `capability=` de production, et le garde #1842 ne couvre pas les services (sa constante `IN_SCOPE_COMPONENTS` liste 5 composants). Orphelinat non gardé (esprit #1604).
- **`depends_on=["quality"]` (`workflows.py:923`) ne correspond à aucune entrée réelle** : le producteur lit `identified_arguments` et `raw_text` (produits par `extract`), jamais la qualité. L'ordre reste correct par transitivité (`quality` dépend de `extract`, `workflows.py:154/216`) — c'est une déclaration inexacte, pas une course — mais c'est le motif que `workflows.py:940-946` a corrigé sur `atms`.
- Toute panne LLM devient un enjeu vide indistinguishable d'un « rien à extraire » (l. 171-174) ; seul le log porte la distinction (`logger.warning` / `logger.info`).
