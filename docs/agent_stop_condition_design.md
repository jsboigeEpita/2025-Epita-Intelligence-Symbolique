# Document de Design : Condition d'Arrêt pour l'Agent d'Analyse de Sophismes

**Auteur**: Roo, Architecte IA
**Date**: 2025-07-04
**Statut**: Proposition

## 1. Contexte

L'agent actuel d'analyse de sophismes est contraint de descendre dans l'arbre de la taxonomie, aboutissant systématiquement à l'identification d'un sophisme, même lorsque le texte analysé n'en contient aucun. Ce comportement est dû à une boucle de navigation qui ne possède pas de condition de sortie explicite en cas de non-pertinence.

Ce document propose une modification architecturale pour introduire une telle condition d'arrêt.

## 2. Solution Proposée

La solution consiste à habiliter l'agent "esclave" (`ExplorationPlugin`) à conclure à une absence de sophisme et à permettre à l'agent "maître" (`FallacyWorkflowPlugin`) de recevoir et d'interpréter cette conclusion pour interrompre le processus.

Cela se décline en deux axes de modification principaux :

1.  **Enrichissement du Plugin Esclave** : Ajout d'une nouvelle capacité pour signaler l'absence de pertinence.
2.  **Adaptation du Plugin Maître** : Modification de la logique de contrôle pour gérer le nouveau signal.

---

## 3. Spécifications Techniques

### 3.1. Modification du `ExplorationPlugin`

Le fichier [`argumentation_analysis/agents/plugins/exploration_plugin.py`](argumentation_analysis/agents/plugins/exploration_plugin.py) doit être modifié.

#### 3.1.1. Nouvelle Fonction `conclude_no_fallacy`

Une nouvelle fonction `kernel_function` doit être ajoutée à la classe `ExplorationPlugin`. Cette fonction permettra à l'agent de signaler qu'aucune des options d'exploration n'est appropriée.

**Signature de la fonction :**

```python
    @kernel_function(
        name="conclude_no_fallacy",
        description="Conclut qu'aucun des sophismes ou catégories proposés n'est pertinent pour le texte analysé."
    )
    def conclude_no_fallacy(
        self, reason: Annotated[str, "L'explication concise expliquant pourquoi aucune branche n'est pertinente."]
    ) -> Annotated[str, "Une confirmation de la conclusion."]:
        """
        Enregistre la conclusion qu'aucun sophisme pertinent n'a été trouvé à cette étape.
        """
        # La fonction n'a pas besoin de faire grand chose, le simple fait de l'appeler est le signal.
        # On pourrait logger la raison pour le débogage.
        return f"Conclusion enregistrée : {reason}"

```

### 3.2. Modification du `FallacyWorkflowPlugin`

Le fichier [`argumentation_analysis/agents/plugins/fallacy_workflow_plugin.py`](argumentation_analysis/agents/plugins/fallacy_workflow_plugin.py) requiert des modifications à plusieurs endroits.

#### 3.2.1. Mise à jour du Prompt Système de l'Esclave

Le prompt système, défini dans la méthode `run_guided_analysis`, doit être mis à jour pour informer le LLM de sa nouvelle option.

**Nouveau texte du prompt (à remplacer à la ligne 124) :**

```python
slave_system_message = (
    "You are a taxonomy navigation assistant. Your task is to analyze a text to find a logical fallacy. "
    "Based on the user's text and the provided taxonomy branch, you must choose the next most relevant node to explore. "
    "You MUST call the 'explore_branch' function with the 'node_id' of your choice from the provided list. "
    "If, after careful consideration, NONE of the proposed branches or fallacies seem relevant, you MUST call the "
    "'conclude_no_fallacy' function and provide a brief explanation."
)
```

#### 3.2.2. Mise à jour de la Configuration du Kernel Esclave

Dans la méthode `_create_slave_kernel`, la configuration `FunctionChoiceBehavior` doit être modifiée pour ne plus forcer l'appel à une seule fonction spécifique. Elle doit permettre au modèle de choisir entre `explore_branch` et `conclude_no_fallacy`.

**Modification de `_create_slave_kernel` (lignes 73-77) :**

*Avant :*
```python
        slave_exec_settings = OpenAIPromptExecutionSettings(
            function_choice_behavior=FunctionChoiceBehavior.Required(
                auto_invoke=False, function_name="explore_branch", plugin_name="Exploration"
            )
        )
```

*Après :*
```python
        slave_exec_settings = OpenAIPromptExecutionSettings(
            function_choice_behavior=FunctionChoiceBehavior.Auto(
                auto_invoke=False
            )
        )
```
**Note :** Utiliser `Auto` (ou ne rien spécifier, car c'est la valeur par défaut) permettra au LLM de choisir librement parmi les fonctions disponibles dans le plugin "Exploration" ajouté au noyau esclave.

#### 3.2.3. Adaptation de la boucle de contrôle `run_guided_analysis`

La boucle `while True` (commençant à la ligne 136) doit être modifiée pour inspecter le nom de la fonction appelée par l'agent esclave.

**Pseudo-code de la nouvelle logique :**

```python
# ... à l'intérieur de la boucle while True, après la ligne 172

# Récupérer la fonction appelée depuis la réponse de l'historique
function_call = history.messages[-1].items[0]
if not isinstance(function_call, FunctionCallContent):
    self.logger.warning("Slave did not return a function call. Breaking path.")
    break

# Vérifier QUELLE fonction a été appelée
if function_call.name == "conclude_no_fallacy":
    reason = json.loads(function_call.arguments).get("reason", "No reason provided.")
    self.logger.info(f"Slave concluded NO FALLACY. Reason: {reason}")
    # Vider la liste des sophismes finaux pour s'assurer qu'aucun résultat n'est retourné
    final_fallacies.clear()
    # Interrompre la boucle de recherche principale
    # Note: On a besoin d'un moyen de sortir des deux boucles (interne et externe).
    # On peut utiliser un flag.
    path_concluded = True # Un flag à définir avant la boucle
    break # Sort de la boucle 'while True' interne

# Si c'était un 'explore_branch', on continue comme avant
chosen_node_id = json.loads(function_call.arguments)["node_id"]
self.logger.info(f"Slave chose to explore next: '{chosen_node_id}'")

# ... reste de la logique (is_leaf, is_confirmation, etc.)

# Après la boucle interne 'while True' :
if path_concluded:
    break # Sort de la boucle 'while candidate_nodes' externe
```

**Note sur l'implémentation :**
Une meilleure façon de gérer la sortie des boucles imbriquées serait de restructurer légèrement le code pour éviter les flags, par exemple en déplaçant la logique de la boucle interne dans une fonction séparée qui retournerait un statut. Cependant, l'approche par flag est la plus simple à implémenter dans la structure actuelle.

---

## 4. Prochaines Étapes

1.  **Validation**: Faire valider ce document de design par les parties prenantes.
2.  **Implémentation**: Créer une nouvelle tâche en mode `code` pour implémenter les changements décrits ci-dessus.
3.  **Test**: Tester la nouvelle logique avec des textes contenant clairement un sophisme, et surtout, avec des textes n'en contenant aucun, pour vérifier que la condition d'arrêt fonctionne comme prévu.
