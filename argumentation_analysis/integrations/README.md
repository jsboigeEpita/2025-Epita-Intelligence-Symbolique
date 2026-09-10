# `integrations/` — intégration SK/JTMS résiduelle sans consommateur

## Rôle et frontière

Un seul module : `semantic_kernel_integration.py` (677 lignes) — intégration **JTMS** à Semantic Kernel. **Sans `__init__.py`** (namespace package implicite) — donc **exclu du packaging** d'un build du package `argumentation_analysis` (répertoires sans `__init__` non collectés par setuptools).

N'est **pas** l'intégration Semantic Kernel réelle du dépôt : celle-ci vit dans `core/bootstrap.py` (assemblage kernel), `agents/factory.py` (câblage agents), `plugins/semantic_kernel/jtms_plugin.py` (surface SK du JTMS utilisée par l'API) — aucun ne passe par ici.

## Composants publics

- `JTMSKernelIntegration` (`semantic_kernel_integration.py:43`) — classe d'intégration ;
- `create_jtms_kernel(...)` (:555) — fabrique de kernel SK configuré pour le JTMS ;
- `create_minimal_jtms_integration()` (:587) — variante minimale.

## Points d'entrée valides

**Aucun.** Grep `argumentation_analysis.integrations` / `argumentation_analysis/integrations` sur tout le dépôt (production et tests) : **0 importeur**.

## Amont / aval

- Amont : `semantic_kernel`, services JTMS (`services/jtms/`).
- Aval : personne.

## Statut d'intégration

**résiduel intégral** — zéro importeur, zéro test, sans `__init__.py` (invisible au packaging). Rôle historiquement couvert aujourd'hui par `plugins/semantic_kernel/jtms_plugin.py` (la surface SK du JTMS réellement montée, cf. [`api/`](../api/README.md) routes `sk_*`). Sort à trancher par le coordinateur (précédent #1574) ; aucune suppression faite ici (mandat documentaire #2088).

## Artefacts et lecteurs

Aucun.

## Tests représentatifs

Aucun test n'existe (grep plein dépôt).

## Frères et parent

Parent : [`../README.md`](../README.md) — ne mentionne pas `integrations/`. Remplacé fonctionnellement par : [`kernel/`](../kernel/README.md) (builder simple), [`core/bootstrap.py`](../core/README.md) (chemin production), `plugins/semantic_kernel/jtms_plugin.py` (surface SK JTMS).

## Limites connues

- sans `__init__.py`, le répertoire n'est pas packagé : toute « intégration » ici est invisible pour un install du package ;
- 677 lignes maintenues par le lint sans aucun consommateur — le formatage Black continue de toucher un module mort.
