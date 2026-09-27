# `kernel/` — ancien emplacement de `KernelBuilder` (retiré, #2711 B)

## Rôle et frontière

Ce répertoire ne contient plus de code. Il portait `kernel_builder.py`, dont la classe `KernelBuilder` (WO-02, 2025-06-29) devait être l'unique fabrique de kernel Semantic Kernel. Elle n'a jamais eu d'appelant en production. Son dernier consommateur, `tests/utils/scenario_runner.py`, a été retiré par #2703. #2711 B l'a retirée à son tour, avec ses 3 tests (`tests/kernel/test_kernel_builder.py`).

## Fabrique canonique

**`argumentation_analysis/core/llm_service.py:create_llm_service`**. Un kernel se compose en deux lignes, `Kernel()` puis `kernel.add_service(create_llm_service(service_id=…))`, et chaque appelant garde son `service_id`. La fabrique porte tout ce que `KernelBuilder` faisait, et ce qu'il ne faisait pas :

- OpenAI, et la bascule OpenRouter (`OPENROUTER_BASE_URL` + `OPENROUTER_API_KEY`) ;
- la substitution des modèles retirés (#1930) ;
- Azure, avec sa propre configuration : `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME`, lus par `AzureOpenAISettings` au moment de la construction.

Pour les appels SDK bruts (hors kernel), le résolveur de route est `resolve_chat_endpoint` (#2352).

## Ce que le retrait a recyclé

La seule configuration Azure juste de l'arbre était celle de `KernelBuilder`. La branche Azure de `create_llm_service` résolvait d'abord la clé OpenAI ou OpenRouter et l'envoyait à l'endpoint Azure. Elle prenait aussi l'id de modèle OpenAI comme nom de déploiement, et refusait un poste configuré pour Azure seul. #2711 B a déplacé les lectures de `KernelBuilder` dans la fabrique (`_create_azure_chat_completion`) avant de le retirer. Témoin : `tests/unit/argumentation_analysis/core/test_llm_service_azure_2711.py`, qui construit le vrai `AzureChatCompletion`.

`AppSettings.azure_openai` n'avait pas d'autre lecteur que `KernelBuilder`. Le champ est parti avec lui : la fabrique instancie `AzureOpenAISettings` au moment de construire le service, comme elle lit l'environnement OpenAI au moment de l'appel.

## Historique

- #2115 : la branche Azure lisait `settings.azure_openai`, un nom qu'`AppSettings` ne portait pas. L'`AttributeError` était avalée en « clé absente ».
- #2198 : le bloc Azure est remonté de `JVMSettings` vers `AppSettings`, où son lecteur le cherchait.
- #2711 B : la configuration passe dans la fabrique, et `KernelBuilder` est retiré.
