# Analyse des Orchestrations Agentiques Sherlock/Watson

## Vue d'ensemble

Ce document analyse les flux d'orchestration dans les conversations agentiques entre Sherlock Holmes et Dr. Watson, développés dans les systèmes Cluedo et Einstein. L'analyse se concentre sur leurs interactions, outils utilisés, et notamment l'usage obligatoire des solvers Tweety par Watson dans les contextes de logique formelle.

## Architecture des orchestrations

### Systèmes développés

1. **Système Cluedo** (`cluedo_orchestrator.py`)
   - Logique informelle et déductive
   - Mécanisme suggestion/réfutation
   - Pas d'usage de Tweety

2. **Système Einstein** (`logique_complexe_orchestrator.py`)
   - Logique formelle obligatoire
   - Usage forcé de TweetyProject
   - Validation par seuils de complexité

## Patterns d'interaction Sherlock/Watson

### 1. Workflow Cluedo Simple

#### Rôle de Sherlock
```
**STRATÉGIE D'ENQUÊTE (CLUEDO) :**
1. FAIRE UNE SUGGESTION : faire_suggestion(suspect: str, arme: str, lieu: str)
2. ANALYSER L'INDICE : Recevoir réfutation de Watson
3. METTRE À JOUR DÉDUCTIONS : Éliminer les cartes connues
4. ITÉRER : Nouvelle suggestion basée sur les indices
5. ACCUSATION FINALE : propose_final_solution(solution: dict)
```

#### Rôle de Watson  
```
**PROTOCOLE DE TRAVAIL :**
1. ATTENDRE LES ORDRES : Attendre instruction de Sherlock
2. EXÉCUTER LA REQUÊTE : Analyser avec validate_formula, execute_query
3. RAPPORTER LES FAITS : Présenter résultats factuels
4. SUGGÉRER (si nécessaire) : Proposer clarifications logiques
```

#### Mécanisme de suggestion/réfutation
```python
def faire_suggestion(self, suspect: str, arme: str, lieu: str) -> str:
    suggestion = {"suspect": suspect, "arme": arme, "lieu": lieu}
    
    # Watson vérifie ses cartes connues
    cartes_connues_watson = []
    for element_suggere in suggestion.values():
        if element_suggere in cartes_connues_watson:
            indice_trouve = f"Watson possède la carte '{element_suggere}'"
            
    return {"indice": indice_trouve or "Aucun élément connu. Continuez."}
```

### 2. Workflow Einstein Complexe

#### Instructions spéciales de Sherlock
```
**RÈGLES STRICTES:**
- Vous ne devez PAS tenter de résoudre par intuition
- Vous DEVEZ exiger que Watson utilise formuler_clause_logique pour chaque contrainte  
- Vous DEVEZ demander à Watson d'exécuter des executer_requete_tweety
- Solution acceptée SEULEMENT si Watson a formulé 10+ clauses logiques et 5+ requêtes
```

#### Instructions spéciales de Watson
```
**OUTILS OBLIGATOIRES:**
- formuler_clause_logique: Transformer contraintes en syntaxe TweetyProject
- executer_requete_tweety: Déduire informations via requêtes logiques
- valider_syntaxe_tweety: Vérifier formulations

**MÉTHODE OBLIGATOIRE:**
1. Formulez CHAQUE contrainte comme clause logique formelle
2. Exécutez requêtes pour déduire positions/attributs  
3. Vérifiez déductions partiellement
4. Minimum 10 clauses + 5 requêtes pour solution valide
```

## Usage des solvers Tweety

### Mécanismes de forçage

#### Système de seuils
```python
def verifier_progression_logique(self) -> Dict[str, Any]:
    return {
        "clauses_formulees": len(self.clauses_logiques),
        "requetes_executees": len(self.requetes_executees), 
        "force_logique_formelle": (
            len(self.clauses_logiques) >= 10 and 
            len(self.requetes_executees) >= 5
        )
    }
```

#### Rejection de solutions insuffisantes
```python
if "solution finale" in contenu.lower():
    if not progression["force_logique_formelle"]:
        message_rappel = f"""[REJET] SOLUTION REJETÉE - LOGIQUE FORMELLE INSUFFISANTE
        
        Progression actuelle:
        - Clauses formulées: {progression['clauses_formulees']}/10 (minimum requis)
        - Requêtes exécutées: {progression['requetes_executees']}/5 (minimum requis)
        
        Watson: Vous DEVEZ utiliser davantage TweetyProject."""
```

### Outils Tweety de Watson

#### 1. formuler_clause_logique
```python
@kernel_function(name="formuler_clause_logique")
def formuler_clause_logique(self, clause: str, justification: str = "") -> str:
    if len(clause.strip()) < 10:
        return "Erreur: Clause trop courte. Minimum 10 caractères."
    
    ajoutee = self._state.ajouter_clause_logique(clause, "Watson")
    progression = self._state.verifier_progression_logique()
    
    return f"Clause ajoutée. Progression: {progression['clauses_formulees']}/10"
```

#### 2. executer_requete_tweety  
```python
@kernel_function(name="executer_requete_tweety")
def executer_requete_tweety(self, requete: str, type_requete: str = "satisfiabilite") -> str:
    if len(self._state.clauses_logiques) < 3:
        return f"Erreur: Minimum 3 clauses requises. Actuellement: {len(self._state.clauses_logiques)}"
    
    resultat = self._state.executer_requete_logique(requete)
    progression = self._state.verifier_progression_logique()
    
    return f"Requête exécutée: {resultat}. Progression: {progression['requetes_executees']}/5"
```

### Syntaxe TweetyProject

#### Patterns de formules logiques
```
**SYNTAXE REQUISE:**
- Prédicats: Maison(x), Position(x,n), Couleur(x,c), Nationalité(x,n)
- Opérateurs: ∀ (pour tout), ∃ (il existe), → (implique), ∧ (et), ∨ (ou), ¬ (non)

**Exemples valides:**
- ∀x (Maison(x) ∧ Couleur(x,Rouge) → Nationalité(x,Anglais))
- ∃!x (Position(x,3) ∧ Boisson(x,Lait))  
- ∀x (Métier(x,Avocat) → ∃y (Adjacent(x,y) ∧ Animal(y,Chat)))
```

#### Normalisation des formules
```python
def _normalize_formula(self, formula: str) -> str:
    # Remplace opérateurs logiques textuels
    normalized = formula.replace("&&", "&").replace("||", "|").replace("!", "not ")
    
    # Remplace Predicat(Argument) par Predicat_Argument
    normalized = re.sub(r'(\w+)\(([\w\s]+)\)', lambda m: m.group(1) + "_" + m.group(2).replace(" ", ""), normalized)
    
    return normalized
```

## Différents cas d'usage

### Cluedo (logique informelle)

| Aspect | Comportement |
|--------|-------------|
| **Mécanisme principal** | Suggestion/Réfutation |
| **Outils Sherlock** | `faire_suggestion`, `propose_final_solution` |
| **Outils Watson** | `validate_formula`, `execute_query` (usage minimal) |
| **Terminaison** | Solution correcte trouvée |
| **Tweety** | Pas obligatoire |

### Einstein (logique formelle)

| Aspect | Comportement |
|--------|-------------|
| **Mécanisme principal** | Formalisation obligatoire |
| **Outils Sherlock** | `get_enigme_description`, `get_contraintes_logiques` |
| **Outils Watson** | `formuler_clause_logique`, `executer_requete_tweety` |
| **Terminaison** | Validation stricte (10 clauses + 5 requêtes) |
| **Tweety** | Usage forcé et vérifié |

### Transitions et escalations

#### Détection du niveau de complexité
```python
class LogiqueComplexeOrchestrator:
    def __init__(self, kernel: Kernel):
        self._max_tours = 25  # Plus de tours pour problème complexe
        
    async def resoudre_enigme_complexe(self):
        # Message initial forcé
        message_initial = """ÉNIGME D'EINSTEIN COMPLEXE - Niveau Logique Formelle Obligatoire
        
        Cette énigme nécessite OBLIGATOIREMENT TweetyProject pour être résolue.
        CONTRAINTE: Minimum 10 clauses logiques + 5 requêtes TweetyProject."""
```

#### Encouragements périodiques
```python
if self._tour_actuel % 5 == 0 and not progression["force_logique_formelle"]:
    message_encouragement = f"""[PROGRESSION] POINT PROGRESSION (Tour {self._tour_actuel})
    
    État logique actuel:
    - Clauses TweetyProject: {progression['clauses_formulees']}/10
    - Requêtes logiques: {progression['requetes_executees']}/5
    
    Cette énigme est IMPOSSIBLE à résoudre sans formalisation complète."""
```

## Outils à disposition des agents

### Outils de Sherlock

#### Cluedo
- `faire_suggestion(suspect, arme, lieu)` : Outil principal de test d'hypothèses
- `propose_final_solution(solution)` : Accusation finale uniquement
- `get_case_description()` : Rappel des éléments du jeu
- `add_hypothesis(text, confidence)` : Gestion d'hypothèses

#### Einstein  
- `get_enigme_description()` : Exploration initiale
- `get_contraintes_logiques()` : Récupération des contraintes
- `verifier_deduction_partielle(position, caracteristiques)` : Validation

### Outils de Watson

#### Cluedo (usage minimal)
- `validate_formula(formula)` : Validation syntaxique basique
- `execute_query(belief_set, query)` : Requêtes simples

#### Einstein (usage forcé)
- `formuler_clause_logique(clause, justification)` : **Obligatoire**
- `executer_requete_tweety(requete, type_requete)` : **Obligatoire**  
- `valider_syntaxe_tweety()` : Vérification des formulations

## Exemples concrets d'exécution

### Trace Cluedo type
```
Tour 1:
Sherlock: faire_suggestion("Colonel Moutarde", "Poignard", "Salon")
Système: {"indice": "Watson possède la carte 'Poignard'"}

Tour 2: 
Sherlock: faire_suggestion("Professeur Violet", "Chandelier", "Cuisine") 
Système: {"indice": "Aucun élément connu. Continuez."}

Tour 3:
Sherlock: propose_final_solution({"suspect": "Professeur Violet", "arme": "Chandelier", "lieu": "Cuisine"})
Système: Solution correcte. Terminaison.
```

### Trace Einstein type
```
Tour 1:
Sherlock: get_enigme_description()
Système: "5 maisons, 5 caractéristiques, 15 contraintes interdépendantes"

Tour 2:
Sherlock: "Watson, formulez la contrainte 'L'Anglais vit dans la maison rouge'"
Watson: formuler_clause_logique("∀x (Maison(x) ∧ Couleur(x,Rouge) → Nationalité(x,Anglais))")
Système: "Clause ajoutée. Progression: 1/10"

Tour 5:
Watson: executer_requete_tweety("∃x (Position(x,1) ∧ Nationalité(x,Norvégien))")
Système: "Requête exécutée: True. Progression requêtes: 1/5"

Tour 20:
Sherlock: "Solution finale basée sur les déductions formelles..."
Système: "[REJET] SOLUTION REJETÉE - 8 clauses/10, 3 requêtes/5"

Tour 25:
Watson: [10ème clause et 5ème requête formulées]
Sherlock: "Solution finale validée logiquement..."
Système: "[SUCCÈS] Solution avec logique formelle suffisante."
```

## Architecture technique

### TweetyBridge et handlers
```python
class TweetyBridge:
    def __init__(self):
        self._initializer = TweetyInitializer(self)
        self._pl_handler = PLHandler(self._initializer)
        self._fol_handler = FOLHandler(self._initializer) 
        self._modal_handler = ModalHandler(self._initializer)
        
    def validate_formula(self, formula_string: str, constants: List[str]) -> Tuple[bool, str]:
        return self._pl_handler.validate_formula(formula_string, constants)
        
    def perform_pl_query(self, belief_set_content: str, query_string: str, constants: List[str]) -> Tuple[bool, str]:
        return self._pl_handler.perform_query(belief_set_content, query_string, constants)
```

### États de workflow
```python
class EinsteinsRiddleState(BaseWorkflowState):
    def __init__(self):
        # Domaines de l'énigme
        self.positions = [1, 2, 3, 4, 5]
        self.couleurs = ["Rouge", "Bleue", "Verte", "Jaune", "Blanche"]
        self.nationalites = ["Anglais", "Suédois", "Danois", "Norvégien", "Allemand"]
        
        # État du raisonnement  
        self.clauses_logiques: List[str] = []
        self.deductions_watson: List[Dict] = []
        self.requetes_executees: List[Dict] = []
        self.contraintes_obligatoires_restantes = 15
```

## Métriques et surveillance

### Progression logique
- **Clauses formulées** : Compteur incrémental des clauses TweetyProject
- **Requêtes exécutées** : Compteur des déductions logiques  
- **Force logique formelle** : Validation du seuil (10 clauses + 5 requêtes)
- **Tours utilisés** : Limitation temporelle des orchestrations

### Validation de solutions
- **Cluedo** : Comparaison directe avec solution secrète
- **Einstein** : Validation logique formelle préalable + cohérence

## Conclusions

Les orchestrations agentiques Sherlock/Watson démontrent une architecture sophistiquée à deux niveaux :

1. **Niveau informel (Cluedo)** : Interaction naturelle suggestion/réfutation sans contraintes logiques formelles
2. **Niveau formel (Einstein)** : Forçage de l'utilisation des solvers Tweety via seuils de validation stricts

Cette approche graduée permet d'adapter la complexité du raisonnement au problème traité, tout en garantissant la rigueur logique nécessaire pour les énigmes complexes.

L'architecture plugin-based avec TweetyBridge permet une séparation claire des responsabilités et une extensibilité vers d'autres types de logiques (FOL, Modal) selon les besoins futurs.