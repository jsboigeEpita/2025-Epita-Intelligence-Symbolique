# Architecture des Agents Logiques

## Vue d'ensemble

L'architecture des agents logiques est conçue pour offrir une approche modulaire, extensible et robuste pour le raisonnement logique. Cette présentation détaille les composants clés, leurs interactions et les principes de conception qui sous-tendent notre système.

## Principes de conception

Notre architecture repose sur plusieurs principes fondamentaux :

1. **Abstraction** : Interface commune pour tous les types de logique
2. **Séparation des préoccupations** : Distinction claire entre représentation, raisonnement et interface
3. **Extensibilité** : Facilité d'ajout de nouveaux types de logique ou fonctionnalités
4. **Interopérabilité** : Communication standardisée entre composants
5. **Robustesse** : Gestion des erreurs et validation à chaque niveau

## Diagramme d'architecture

```
┌───────────────────────────────────────────────────────────────┐
│                        Application Client                      │
└───────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                           API Web                              │
└───────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                        LogicFactory                            │
└───────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────┬─────────────────────────────────┐
│                             │                                  │
▼                             ▼                                  ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│PropositionalLogicAgent│ │FirstOrderLogicAgent │ │  ModalLogicAgent   │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
          │                       │                        │
          ▼                       ▼                        ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│  BeliefSet (Prop)   │ │  BeliefSet (FOL)    │ │  BeliefSet (Modal)  │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
          │                       │                        │
          └───────────┬───────────┘                        │
                      ▼                                    ▼
          ┌─────────────────────┐              ┌─────────────────────┐
          │    TweetyBridge     │◄─────────────┤   ModalReasoner     │
          └─────────────────────┘              └─────────────────────┘
```

## Composants principaux

### 1. AbstractLogicAgent

Classe abstraite définissant l'interface commune pour tous les agents logiques :

```java
public abstract class AbstractLogicAgent {
    // Méthodes principales
    public abstract BeliefSet createBeliefSet(String text);
    public abstract QueryResult executeQuery(BeliefSet beliefSet, String query);
    public abstract List<String> generateQueries(BeliefSet beliefSet);
    public abstract String interpretResults(BeliefSet beliefSet, List<QueryResult> results);
    
    // Méthodes utilitaires
    protected abstract void validateBeliefSet(BeliefSet beliefSet);
    protected abstract void validateQuery(String query);
}
```

### 2. Implémentations spécifiques

Chaque type de logique possède sa propre implémentation :

#### PropositionalLogicAgent

Spécialisé dans la logique propositionnelle :
- Traitement des opérateurs booléens (∧, ∨, ¬, →, ↔)
- Évaluation de tables de vérité
- Vérification de satisfiabilité et validité

#### FirstOrderLogicAgent

Spécialisé dans la logique du premier ordre :
- Gestion des quantificateurs (∀, ∃)
- Unification de termes
- Résolution et preuve de théorèmes

#### ModalLogicAgent

Spécialisé dans la logique modale :
- Opérateurs modaux (□, ◇)
- Sémantique des mondes possibles
- Systèmes modaux (K, T, S4, S5)

### 3. BeliefSet

Représentation formelle d'un ensemble de croyances :

```java
public class BeliefSet {
    private String id;
    private String content;
    private LogicType type;
    private Object internalRepresentation;
    
    // Méthodes pour manipuler l'ensemble de croyances
    public boolean isConsistent();
    public List<String> getFormulas();
    public void addFormula(String formula);
    public void removeFormula(String formula);
}
```

### 4. TweetyBridge

Interface avec la bibliothèque TweetyProject pour les opérations logiques complexes :

```java
public class TweetyBridge {
    public static BeliefBase convertToTweetyBeliefBase(BeliefSet beliefSet);
    public static boolean checkEntailment(BeliefBase base, Formula formula);
    public static boolean checkConsistency(BeliefBase base);
    public static Set<Interpretation> getModels(BeliefBase base);
}
```

### 5. LogicFactory

Fabrique pour créer l'agent approprié selon le type de logique :

```java
public class LogicFactory {
    public static AbstractLogicAgent createAgent(LogicType type) {
        switch (type) {
            case PROPOSITIONAL:
                return new PropositionalLogicAgent();
            case FIRST_ORDER:
                return new FirstOrderLogicAgent();
            case MODAL:
                return new ModalLogicAgent();
            default:
                throw new IllegalArgumentException("Type de logique non supporté");
        }
    }
}
```

## Flux de données

### 1. Création d'un ensemble de croyances

1. Le client envoie un texte à l'API Web
2. L'API Web détermine le type de logique et utilise LogicFactory
3. L'agent logique approprié analyse le texte
4. L'agent crée un BeliefSet formalisé
5. Le BeliefSet est retourné au client

### 2. Exécution d'une requête

1. Le client envoie une requête et un ID de BeliefSet
2. L'API Web récupère le BeliefSet et détermine l'agent approprié
3. L'agent valide la requête
4. L'agent exécute la requête sur le BeliefSet (via TweetyBridge si nécessaire)
5. Le résultat est retourné au client avec une explication

## Mécanismes d'extension

L'architecture est conçue pour être facilement extensible :

### Ajout d'un nouveau type de logique

1. Créer une nouvelle implémentation de AbstractLogicAgent
2. Définir une classe BeliefSet spécifique si nécessaire
3. Ajouter le nouveau type à LogicFactory
4. Mettre à jour l'API Web pour prendre en charge le nouveau type

### Ajout de nouvelles fonctionnalités

1. Étendre l'interface AbstractLogicAgent
2. Implémenter la fonctionnalité dans chaque agent
3. Mettre à jour l'API Web pour exposer la nouvelle fonctionnalité

## Considérations techniques

### Performance

- Mise en cache des résultats de requêtes fréquentes
- Optimisation des algorithmes de raisonnement
- Parallélisation des opérations indépendantes

### Sécurité

- Validation des entrées à tous les niveaux
- Limitation de la complexité des requêtes
- Isolation des ressources par utilisateur

### Évolutivité

- Architecture sans état pour faciliter la mise à l'échelle horizontale
- Séparation claire entre API et logique métier
- Possibilité de déploiement en microservices

## Conclusion

L'architecture des agents logiques offre :

- Une base solide pour le raisonnement logique
- Une flexibilité pour différents types de logique
- Une extensibilité pour de futures fonctionnalités
- Une intégration facile via l'API Web

Cette conception modulaire permet d'adapter le système à une variété de cas d'utilisation tout en maintenant une cohérence interne et une robustesse opérationnelle.