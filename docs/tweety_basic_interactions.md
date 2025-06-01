# Interactions Fondamentales avec TweetyProject via JPype

Ce document détaille les tests effectués pour valider quelques interactions de base avec la bibliothèque TweetyProject en utilisant JPype dans l'environnement Python du projet.

## Contexte

L'objectif était d'identifier et de tester 2-3 opérations fondamentales au-delà de la simple instanciation d'une classe Tweety, pour s'assurer de la fonctionnalité de base de l'intégration Python-Java.

Les tests ont été effectués avec le script `scratch_tweety_interactions.py` après activation de l'environnement via `activate_project_env.ps1`.

## Interactions Testées et Résultats

### 1. Instanciation de `PlSignature`

*   **Description :** Création d'une instance de la classe `org.tweetyproject.logics.pl.syntax.PlSignature`, qui représente une signature en logique propositionnelle (un ensemble de propositions atomiques).
*   **Snippet Python (partie pertinente) :**
    ```python
    import jpype
    # ... (Initialisation de la JVM et du classpath) ...

    _PlSignature = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlSignature")
    
    # Dans la fonction de test :
    if _PlSignature:
        try:
            sig = _PlSignature()
            print(f"   PlSignature instanciée: {sig}")
            # Tentative d'ajout d'une proposition (échoue si PropositionalFormula n'est pas chargée)
            # if _PropositionalFormula:
            #     p_prop = _PropositionalFormula("p")
            #     sig.add(p_prop)
            print("   Test PlSignature Réussi.")
        except Exception as e:
            print(f"   Erreur Test PlSignature: {e}")
    ```
*   **Résultat :** **SUCCÈS**. L'instanciation de `PlSignature` fonctionne correctement.
*   **Sortie Attendue/Observée :**
    ```
    --- Test 1: Instanciation de PlSignature ---
       PlSignature instanciée: []
       PropositionalFormula non disponible, test d'ajout de proposition sauté.
       Test 1 Réussi.
    ```

### 2. Instanciation de `PlParser`

*   **Description :** Création d'une instance de la classe `org.tweetyproject.logics.pl.parser.PlParser`, utilisée pour parser des chaînes de caractères représentant des formules logiques.
*   **Snippet Python (partie pertinente) :**
    ```python
    import jpype
    # ... (Initialisation de la JVM et du classpath) ...

    _PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")

    # Dans la fonction de test :
    if _PlParser:
        try:
            parser = _PlParser()
            print(f"   PlParser instancié: {parser}")
            print("   Test PlParser (instanciation) Réussi.")
        except Exception as e:
            print(f"   Erreur Test PlParser (instanciation): {e}")
    ```
*   **Résultat :** **SUCCÈS**. L'instanciation de `PlParser` fonctionne correctement.
*   **Sortie Attendue/Observée :**
    ```
    --- Test 2: Utilisation simple de PlParser ---
       PlParser instancié: org.tweetyproject.logics.pl.parser.PlParser@xxxxx 
       (l'adresse mémoire varie)
    ```
    (Suivi par l'erreur sur `parser.parse()` dans les tests complets)


### 3. Chargement de `PropositionalFormula`

*   **Description :** Tentative de chargement de la classe `org.tweetyproject.logics.pl.syntax.PropositionalFormula` via `jpype.JClass`.
*   **Snippet Python (partie pertinente) :**
    ```python
    try:
        _PropositionalFormula = jpype.JClass("org.tweetyproject.logics.pl.syntax.PropositionalFormula")
        print("  INFO: PropositionalFormula chargée.")
    except TypeError: # L'erreur réelle est TypeError si la classe n'est pas trouvée
        print("  AVERTISSEMENT: PropositionalFormula n'a pas pu être chargée via JClass.")
    ```
*   **Résultat :** **ÉCHEC**. La classe ne peut pas être chargée.
*   **Sortie Observée :**
    ```
    AVERTISSEMENT: PropositionalFormula n'a pas pu être chargée via JClass.
    ```

### 4. Utilisation de `PlParser.parse(String)`

*   **Description :** Tentative d'utilisation de la méthode `parse` d'un objet `PlParser` pour convertir une chaîne en formule.
*   **Snippet Python (partie pertinente) :**
    ```python
    # parser est une instance de _PlParser
    formula_str_ok = "a" 
    try:
        parsed_prop = parser.parse(formula_str_ok) 
        print(f"   Proposition '{formula_str_ok}' parsée: {parsed_prop}")
    except Exception as e_parse:
        print(f"   Erreur Python lors du parsing: {e_parse}")
    ```
*   **Résultat :** **ÉCHEC**. L'appel `parser.parse("a")` résulte en une `AttributeError`, indiquant que la méthode `parse` n'est pas directement accessible comme attribut de l'objet proxy JPype.
*   **Sortie Observée :**
    ```
       Erreur Python lors du parsing: 'org.tweetyproject.logics.pl.parser.PlParser' object has no attribute 'parse'
    ```

## Conclusion des Tests d'Interaction

Les interactions les plus basiques, à savoir l'instanciation de `PlSignature` et `PlParser`, fonctionnent comme attendu. Cependant, des opérations plus complexes comme le chargement de `PropositionalFormula` ou l'utilisation directe de méthodes comme `PlParser.parse()` rencontrent des difficultés.

Le problème avec `PropositionalFormula` empêche de tester des fonctionnalités clés comme la création de formules complexes ou l'utilisation du `SatSolver`. L'échec de `PlParser.parse()` suggère que l'accès aux méthodes des objets Java via JPype pourrait nécessiter une approche différente ou que certaines méthodes ne sont pas exposées comme prévu.

Ces résultats indiquent que bien que la connexion de base à la JVM et le chargement de certains JARs fonctionnent, une investigation plus approfondie est nécessaire pour utiliser pleinement les fonctionnalités de TweetyProject via JPype.