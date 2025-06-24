# 🧩 Démonstration d'Énigme Logique Complexe

## Vue d'ensemble

Cette démonstration présente une **énigme d'Einstein complexe** qui **force obligatoirement** l'utilisation des outils de logique formelle TweetyProject par Watson. Contrairement au Cluedo simple qui peut être résolu par déduction informelle, cette énigme nécessite une formalisation logique complète.

## 🎯 Objectifs pédagogiques

1. **Démontrer l'utilisation obligatoire de TweetyProject** par Watson
2. **Illustrer la différence** entre logique informelle (Cluedo) et logique formelle (Einstein)
3. **Valider le système de contraintes** pour forcer l'utilisation d'outils spécialisés
4. **Tester la robustesse** du bridge TweetyProject sous charge logique

## 🧮 Complexité de l'énigme

### Domaine du problème
- **5 maisons** en ligne (positions 1-5)
- **5 caractéristiques** par maison:
  - Couleur: Rouge, Bleue, Verte, Jaune, Blanche
  - Nationalité: Anglais, Suédois, Danois, Norvégien, Allemand
  - Animal: Chien, Chat, Oiseau, Poisson, Cheval
  - Boisson: Thé, Café, Lait, Bière, Eau
  - Métier: Médecin, Avocat, Ingénieur, Professeur, Artiste

### 15 contraintes interdépendantes
1. L'Anglais vit dans la maison rouge
2. Le Suédois a un chien
3. Le Danois boit du thé
4. La maison verte est immédiatement à gauche de la maison blanche
5. Le propriétaire de la maison verte boit du café
6. La personne qui fume des Pall Mall élève des oiseaux
7. Le propriétaire de la maison jaune est médecin
8. L'homme qui vit dans la maison du centre boit du lait
9. Le Norvégien vit dans la première maison
10. L'homme qui est avocat vit à côté de celui qui a des chats
11. L'homme qui a un cheval vit à côté de celui qui est médecin
12. L'homme qui est artiste boit de la bière
13. L'Allemand est professeur
14. Le Norvégien vit à côté de la maison bleue
15. L'avocat vit à côté de celui qui boit de l'eau

## 🚫 Contraintes de validation

Pour qu'une solution soit acceptée, Watson DOIT avoir:
- **Minimum 10 clauses logiques** formulées en syntaxe TweetyProject
- **Minimum 5 requêtes logiques** exécutées via TweetyProject
- **Syntaxe formelle correcte** avec prédicats et opérateurs logiques

## 📝 Syntaxe TweetyProject requise

### Prédicats de domaine
```
Maison(x)          - x est une maison
Position(x,n)      - maison x est en position n
Couleur(x,c)       - maison x a la couleur c
Nationalité(x,n)   - maison x a la nationalité n
Animal(x,a)        - maison x a l'animal a
Boisson(x,b)       - maison x a la boisson b
Métier(x,m)        - maison x a le métier m
Adjacent(x,y)      - maisons x et y sont adjacentes
```

### Opérateurs logiques
```
∀  - Pour tout (quantificateur universel)
∃  - Il existe (quantificateur existentiel)
∃! - Il existe exactement un
→  - Implique
∧  - Et logique
∨  - Ou logique
¬  - Négation
```

### Exemples de clauses valides
```
∀x (Maison(x) ∧ Couleur(x,Rouge) → Nationalité(x,Anglais))
∃!x (Position(x,3) ∧ Boisson(x,Lait))
∀x (Couleur(x,Verte) → ∃y (Position(y,Position(x)+1) ∧ Couleur(y,Blanche)))
∀x (Métier(x,Avocat) → ∃y (Adjacent(x,y) ∧ Animal(y,Chat)))
```

## 🛠️ Outils disponibles pour Watson

### Outils obligatoires TweetyProject
- `formuler_clause_logique(clause, justification)` - Formalise une contrainte
- `executer_requete_tweety(requete, type_requete)` - Exécute une requête logique
- `valider_syntaxe_tweety(clause_proposee)` - Valide la syntaxe

### Outils de progression
- `verifier_deduction_partielle(position, caracteristiques)` - Teste une déduction
- `obtenir_progression_logique()` - Vérifie l'état de formalisation
- `generer_indice_complexe()` - Obtient un indice nécessitant formalisation

### Outils d'exploration
- `get_enigme_description()` - Description complète de l'énigme
- `get_contraintes_logiques()` - Liste des 15 contraintes
- `proposer_solution_complete(solution)` - Propose la solution finale

## 🔄 Workflow attendu

1. **Sherlock** explore l'énigme avec `get_enigme_description()`
2. **Sherlock** demande les contraintes avec `get_contraintes_logiques()`
3. **Watson** formalise chaque contrainte avec `formuler_clause_logique()`
4. **Watson** exécute des requêtes avec `executer_requete_tweety()`
5. **Watson** vérifie des déductions partielles
6. **Sherlock** vérifie la progression avec `obtenir_progression_logique()`
7. **Watson** propose la solution finale (acceptée seulement si 10+ clauses + 5+ requêtes)

## 🚀 Lancement de la démonstration

```bash
# Depuis la racine du projet
python examples/Sherlock_Watson/agents_logiques_production.py --scenario examples/Sherlock_Watson/einstein_scenario.json
```

### Prérequis
- Variable d'environnement `OPENAI_API_KEY` configurée
- Modèle GPT-4 recommandé pour la complexité logique
- TweetyProject initialisé et fonctionnel

## 📊 Métriques de succès

### Critères de réussite
- ✅ Watson utilise TweetyProject massivement (10+ clauses, 5+ requêtes)
- ✅ Solution correcte trouvée avec formalisation complète
- ✅ Pas de raccourcis ou raisonnement informel accepté

### Critères d'échec
- ❌ Tentative de résolution sans formalisation suffisante
- ❌ Solution rejetée par manque de clauses logiques
- ❌ Timeout sans utilisation adéquate des outils TweetyProject

## 🆚 Comparaison avec Cluedo simple

| Aspect | Cluedo Simple | Einstein Complexe |
|--------|---------------|-------------------|
| **Raisonnement** | Informel suffisant | Formel obligatoire |
| **Outils Watson** | Optionnels | TweetyProject requis |
| **Validation** | Immédiate | Après formalisation |
| **Complexité** | 3×3×3 = 27 combinaisons | 5⁵ = 3125 arrangements |
| **Contraintes** | 1 par suggestion | 15 interdépendantes |
| **Tours** | 3-5 tours | 15-25 tours |

## 🎓 Apprentissages attendus

Cette démonstration illustre:
1. **Nécessité absolue** de la logique formelle pour certains problèmes
2. **Validation par contraintes** pour forcer l'utilisation d'outils spécialisés
3. **Différenciation automatique** entre problèmes simples et complexes
4. **Robustesse du système** TweetyProject sous charge réelle