# Plan de Conception : Configuration du Solveur v2

## 1. Contexte et Objectifs

Ce document détaille la conception technique pour un système de configuration de solveur flexible. L'objectif est de remplacer la logique de sélection de solveur actuellement implicite ou codée en dur par un mécanisme de configuration explicite, piloté par une variable d'environnement.

Le système doit permettre de choisir entre :
*   Le solveur par défaut, basé sur l'écosystème **TweetyProject** (via JPype).
*   Le solveur alternatif **`prover9`**, utilisé comme un processus externe.

La configuration sera gérée à l'aide de `pydantic-settings` et de la variable d'environnement `ARG_ANALYSIS_SOLVER`.

## 2. Analyse de l'Architecture Existante

L'analyse du code révèle deux chemins d'exécution complètement distincts pour le raisonnement en logique du premier ordre (FOL).

### 2.1. Chemin d'Exécution `prover9`

*   **Mécanisme :** Appel d'un processus externe.
*   **Composants clés :**
    *   `argumentation_analysis/core/prover9_runner.py`: Contient la fonction `run_prover9` qui exécute l'exécutable `prover9.bat` avec un fichier d'entrée temporaire.
    *   `argumentation_analysis/agents/core/logic/fol_handler.py`: Prépare les données pour `prover9`, appelle le runner et interprète la sortie texte.
*   **Conclusion :** Cette voie est totalement indépendante de Java et de Tweety. Elle est utilisée pour des tâches spécifiques comme la vérification de cohérence (`fol_check_consistency`) et l'interrogation (`fol_query`).

### 2.2. Chemin d'Exécution `Tweety`

*   **Mécanisme :** Intégration Java via le pont JPype.
*   **Composants clés :**
    *   `TweetyBridge` (concept identifié dans la documentation) : Sert de façade pour interagir avec les fonctionnalités de Tweety.
    *   Gestionnaires de logique (ex: `FOLHandler`, `PLHandler`) : Composants qui utilisent le pont pour appeler des classes Java spécifiques.
    *   Classes Java de Tweety : Des `Reasoner` comme `org.tweetyproject.logics.fol.reasoner.SimpleFolReasoner` sont instanciés et utilisés au sein de la JVM.
*   **Conclusion :** Cette voie est entièrement contenue dans l'écosystème JVM/Tweety.

## 3. Proposition de Conception Détaillée

La solution consiste à introduire une couche de configuration centralisée qui sera consultée par le `FOLHandler` pour décider quelle voie d'exécution emprunter.

### 3.1. Schéma de la Solution

```
+--------------------------+         +----------------------------+
| Variable d'Environnement |         |   [NOUVEAU FICHIER]        |
| (ARG_ANALYSIS_SOLVER)    | ------> | config.py                  |
+--------------------------+         |   - SolverChoice (Enum)    |
                                   |   - ArgAnalysisSettings    |
                                   +-------------+--------------+
                                                 |
                                                 | (1) Lit la configuration
                                                 v
+------------------------------------------------+----------------------------+
| argumentation_analysis/agents/core/logic/fol_handler.py                     |
|                                                                             |
| class FOLHandler:                                                           |
|                                                                             |
|   def __init__(self):                                                       |
|     self.settings = ArgAnalysisSettings()                                   |
|                                                                             |
|   def query(self, belief_set, formula):                                     |
|     if self.settings.solver == SolverChoice.PROVER9:  <-- (2) Aiguillage   |
|       // Branche Prover9                                                    |
|       return run_prover9(...)  -----------------------------------------+   |
|     else:                                                                   |
|       // Branche Tweety                                                     |
|       return self.tweety_bridge.fol_query(...) ---+                      |   |
|                                                    |                      |   |
+----------------------------------------------------+----------------------+
                                                     |
             +---------------------------------------+
             |
             v
+------------+------------------+     +-------------------------------+
| argumentation_analysis/core/  |     | Pont JPype -> JVM Tweety      |
| prover9_runner.py             |     |                               |
|                               |     | ...SimpleFolReasoner.query()  |
+-------------------------------+     +-------------------------------+
```

### 3.2. Nouvelle Classe de Configuration

Un nouveau fichier sera créé pour centraliser la configuration de l'analyse argumentative.

**Nouveau fichier : `argumentation_analysis/core/config.py`**
```python
import enum
from pydantic_settings import BaseSettings, SettingsConfigDict

class SolverChoice(str, enum.Enum):
    """Énumération pour les choix de solveurs disponibles."""
    TWEETY = "tweety"
    PROVER9 = "prover9"

class ArgAnalysisSettings(BaseSettings):
    """
    Paramètres de configuration pour le système d'analyse d'arguments.
    
    Les valeurs sont chargées à partir des variables d'environnement.
    """
    #
    # Le choix du solveur à utiliser pour les opérations de logique.
    # 'tweety' (défaut) utilise le pont JPype vers TweetyProject.
    # 'prover9' utilise un appel à un processus externe Prover9.
    #
    solver: SolverChoice = SolverChoice.TWEETY

    model_config = SettingsConfigDict(
        env_prefix='ARG_ANALYSIS_'
    )

# Instance unique à importer dans les autres modules
settings = ArgAnalysisSettings()

```

### 3.3. Modifications des Fichiers Existants

La modification principale concernera le `FOLHandler` qui doit être adapté pour utiliser la nouvelle configuration.

**Fichier à modifier : `argumentation_analysis/agents/core/logic/fol_handler.py`**

Les méthodes existantes comme `fol_query` et `fol_check_consistency` seront refactorisées pour utiliser le mécanisme d'aiguillage.

```python
# --- Au début du fichier ---
from argumentation_analysis.core.config import settings, SolverChoice
from argumentation_analysis.core.prover9_runner import run_prover9
# ... autres imports

class FOLHandler:
    # ... (init et autres méthodes)

    # Exemple de refactorisation de la méthode de requête
    def fol_query(self, belief_set, query_formula_str: str) -> bool:
        """
        Checks if a query is entailed by a belief base using the configured solver.
        """
        logger.debug(f"Performing FOL query with solver: {settings.solver.value}")

        if settings.solver == SolverChoice.PROVER9:
            return self._fol_query_with_prover9(belief_set, query_formula_str)
        else:
            # La logique d'appel à Tweety doit être implémentée ou appelée ici
            return self._fol_query_with_tweety(belief_set, query_formula_str)

    def _fol_query_with_prover9(self, belief_set, query_formula_str: str) -> bool:
        """
        Ancienne logique d'interrogation via un processus externe Prover9.
        (Contenu de la méthode fol_query existante)
        """
        logger.debug(f"Performing FOL query via external Prover9. Query: '{query_formula_str}'")
        try:
            # Convert belief set and query to Prover9 input format
            formulas_str = belief_set.toString().replace(";", ".\n")
            prover9_goal = query_formula_str.rstrip('.')
            prover9_input = f"formulas(assumptions).\n{formulas_str}\nend_of_list.\n\ngoals.\n{prover9_goal}.\nend_of_list."
            
            logger.debug(f"Prover9 input for query:\n{prover9_input}")

            # Run Prover9 externally
            prover9_output = run_prover9(prover9_input)

            # Check for "END OF PROOF" which means the goal was proven
            entails = "END OF PROOF" in prover9_output
            
            logger.info(f"FOL Query: KB entails '{query_formula_str}'? {entails}")
            return entails

        except Exception as e:
            logger.error(f"Error during external FOL query: {e}", exc_info=True)
            raise RuntimeError(f"FOL query failed. Details: {getattr(e, 'stderr', str(e))}") from e

    def _fol_query_with_tweety(self, belief_set, query_formula_str: str) -> bool:
        """
        Logique d'interrogation via Tweety/JPype.
        NOTE : Cette partie doit être connectée au TweetyBridge.
        """
        logger.debug(f"Performing FOL query via Tweety. Query: '{query_formula_str}'")
        # PSEUDO-CODE : La véritable implémentation dépend du TweetyBridge
        try:
            # Par exemple:
            # tweety_belief_set = self.tweety_initializer.parse_pl_belief_set(belief_set.toString())
            # tweety_query = self.tweety_initializer.pl_parser.parseFormula(query_formula_str)
            # reasoner = self.tweety_initializer.get_reasoner("SimpleFolReasoner")
            # entails = reasoner.query(tweety_belief_set, tweety_query)
            # return bool(entails)
            logger.warning("Tweety FOL query path is not fully implemented yet.")
            raise NotImplementedError("The Tweety pathway for FOL queries needs to be implemented.")
        except Exception as e:
            logger.error(f"Error during Tweety FOL query: {e}", exc_info=True)
            raise

    # La méthode fol_check_consistency doit être refactorisée de manière similaire.
```

### 3.4. Stratégie de Test

Une stratégie de test à deux niveaux sera adoptée pour valider cette nouvelle fonctionnalité.

#### 3.4.1. Tests Unitaires

*   **`test_config.py`**:
    *   Tester que `ArgAnalysisSettings` se charge correctement.
    *   Vérifier que la valeur par défaut est `SolverChoice.TWEETY`.
    *   Utiliser `unittest.mock.patch.dict` pour simuler la présence de la variable d'environnement `ARG_ANALYSIS_SOLVER=prover9` et vérifier que l'objet `settings` est mis à jour en conséquence.

#### 3.4.2. Tests d'Intégration

*   **`test_fol_handler.py`**:
    *   **Test du chemin par défaut (Tweety)**:
        *   Sans définir de variable d'environnement.
        *   Appeler `fol_handler.query(...)`.
        *   Mocker la méthode `_fol_query_with_tweety` et vérifier qu'elle a été appelée.
    *   **Test du chemin `prover9`**:
        *   Avec `ARG_ANALYSIS_SOLVER=prover9`.
        *   Appeler `fol_handler.query(...)`.
        *   Mocker la méthode `_fol_query_with_prover9` (ou `run_prover9`) et vérifier qu'elle a été appelée.

## 4. Documentation

Le fichier `README.md` principal ou un guide de configuration développeur sera mis à jour pour inclure des informations sur la nouvelle variable d'environnement `ARG_ANALYSIS_SOLVER` et ses valeurs possibles (`tweety`, `prover9`).
