import pytest
import jpype
import os

# Les classes Java nécessaires seront importées via une fixture ou directement.
# La fixture 'integration_jvm' du conftest.py racine doit gérer le démarrage/arrêt de la JVM.

# S'assurer que la fixture integration_jvm est bien active (implicitement via conftest.py racine)

def test_load_logic_theory_from_file(logic_classes, integration_jvm):
    """
    Teste le chargement d'une théorie logique (ex: programme logique) depuis un fichier.
    """
    PlBeliefSet = logic_classes["PlBeliefSet"]
    PlParser = logic_classes["PlParser"]
    JFile = jpype.JClass("java.io.File")

    # Chemin vers le fichier de théorie dans le répertoire de test d'intégration
    theory_file_path = os.path.join(os.path.dirname(__file__), "sample_theory.lp")
    
    assert os.path.exists(theory_file_path), f"Le fichier de théorie {theory_file_path} n'existe pas."

    parser = PlParser()
    
    # La méthode parseBeliefBaseFromFile attend un chemin de fichier (String)
    # ou un objet java.io.File. Utilisons le chemin direct.
    belief_set = parser.parseBeliefBaseFromFile(theory_file_path)

    assert belief_set is not None, "Le belief set ne devrait pas être None après parsing."
    # Un programme logique "a :- b. b." devrait avoir au moins 2 formules/règles.
    # "c :- not d. d :- not c." ajoute 2 autres.
    # Le nombre exact peut dépendre de la représentation interne (ex: faits comptés comme règles).
    # PlBeliefSet.size() retourne le nombre de formules.
    assert belief_set.size() >= 2, f"Attendu au moins 2 formules, obtenu {belief_set.size()}."

    # Vérification plus fine (optionnelle, dépend de ce que Tweety compte)
    # Par exemple, si on s'attend à 4 éléments distincts (2 règles, 2 faits/règles)
    # Pour "a :- b. b. c :- not d. d :- not c.", on s'attend à 4 éléments.
    assert belief_set.size() == 4, f"Attendu 4 formules pour sample_theory.lp, obtenu {belief_set.size()}."

    print(f"Théorie chargée depuis {theory_file_path}. Nombre de formules: {belief_set.size()}")
    # Pour déboguer, on pourrait imprimer les formules:
    # iterator = belief_set.iterator()
    # while iterator.hasNext():
    #     formula = iterator.next()
    #     print(f"- {formula.toString()}")
def test_simple_pl_reasoner_queries(logic_classes, integration_jvm):
    """
    Teste l'exécution de requêtes simples (entailment) sur un SimplePlReasoner
    en utilisant la théorie chargée depuis sample_theory.lp.
    sample_theory.lp:
    a :- b.
    b.
    c :- not d.
    d :- not c.
    """
    PlParser = logic_classes["PlParser"]
    Proposition = logic_classes["Proposition"]
    # Negation = logic_classes["Negation"] # Pas explicitement nécessaire si on teste des propositions simples
    SimplePlReasoner = logic_classes["SimplePlReasoner"]

    theory_file_path = os.path.join(os.path.dirname(__file__), "sample_theory.lp")
    parser = PlParser()
    belief_set = parser.parseBeliefBaseFromFile(theory_file_path)

    assert belief_set is not None, "Le belief set ne doit pas être None."
    assert belief_set.size() == 4, f"Attendu 4 formules, obtenu {belief_set.size()}."

    reasoner = SimplePlReasoner()

    # Création des propositions à tester
    prop_a = Proposition("a")
    prop_b = Proposition("b")
    prop_c = Proposition("c")
    prop_d = Proposition("d")
    prop_x = Proposition("x") # Une proposition non présente et non dérivable

    # Vérification des conséquences attendues
    # query(knowledge_base, formula_to_check)
    assert reasoner.query(belief_set, prop_a), "La proposition 'a' devrait être une conséquence."
    assert reasoner.query(belief_set, prop_b), "La proposition 'b' (fait) devrait être une conséquence."
    
    Disjunction = logic_classes["Disjunction"]
    formula_c_or_d = Disjunction(prop_c, prop_d)

    query_c_result = reasoner.query(belief_set, prop_c)
    query_d_result = reasoner.query(belief_set, prop_d)
    query_c_or_d_result = reasoner.query(belief_set, formula_c_or_d)

    print(f"Query for 'c': {query_c_result}")
    print(f"Query for 'd': {query_d_result}")
    print(f"Query for 'c or d': {query_c_or_d_result}")

    assert query_c_or_d_result, "La formule 'c or d' devrait être une conséquence."
    assert not query_c_result, "La proposition 'c' ne devrait pas être une conséquence sceptique."
    assert not query_d_result, "La proposition 'd' ne devrait pas être une conséquence sceptique."

    # Vérification d'une proposition non conséquence
    assert not reasoner.query(belief_set, prop_x), "La proposition 'x' ne devrait pas être une conséquence."

    print("Test des requêtes SimplePlReasoner réussi.")
def test_basic_logical_agent_manipulation(logic_classes, integration_jvm):
    """
    Teste la création d'un agent logique simple et l'accès/modification
    de sa base de connaissances.
    """
    PlBeliefSet = logic_classes["PlBeliefSet"]
    Proposition = logic_classes["Proposition"]
    # Pour cet exemple, nous allons utiliser une classe d'agent logique générique si disponible,
    # ou simuler son comportement avec un PlBeliefSet.
    # Tweety a `org.tweetyproject.agents.LogicalAgent` mais c'est une classe abstraite.
    # `org.tweetyproject.agents.DefaultAgent` pourrait être une option,
    # ou un agent spécifique à une logique comme `PlAgent`.
    # Pour l'instant, nous allons utiliser PlBeliefSet comme KB de l'agent.
    # Si une classe d'agent concrète est nécessaire, la fixture logic_classes devra être mise à jour.

    # Supposons que notre "agent" a une base de connaissances de type PlBeliefSet
    agent_kb = PlBeliefSet()
    
    prop_p = Proposition("p")
    prop_q = Proposition("q")

    # Ajout de croyances à la base de connaissances de l'agent
    agent_kb.add(prop_p)
    agent_kb.add(prop_q)

    assert agent_kb.size() == 2, "La base de connaissances de l'agent devrait contenir 2 formules."
    assert agent_kb.contains(prop_p), "La KB devrait contenir la proposition 'p'."
    assert agent_kb.contains(prop_q), "La KB devrait contenir la proposition 'q'."

    # Retrait d'une croyance
    agent_kb.remove(prop_q)
    assert agent_kb.size() == 1, "La KB devrait contenir 1 formule après suppression."
    assert not agent_kb.contains(prop_q), "La KB ne devrait plus contenir 'q'."
    assert agent_kb.contains(prop_p), "La KB devrait toujours contenir 'p'."

    print("Test de manipulation basique de la base de connaissances d'un agent (simulé) réussi.")

    # Pour un test plus réaliste avec un VRAI agent Tweety:
    # 1. Identifier une classe d'agent concrète (ex: org.tweetyproject.logics.pl.agent.PlAgent).
    # 2. L'ajouter à la fixture `logic_classes`.
    # 3. Instancier cet agent: `pl_agent = PlAgent()`
    # 4. Lui associer une base de connaissances: `pl_agent.setBeliefBase(initial_kb)`
    # 5. Interagir avec les méthodes de l'agent: `pl_agent.getBeliefBase()`, `pl_agent.updateBeliefs(...)` etc.
    # Pour l'instant, ce test se concentre sur la manipulation du PlBeliefSet qui est le cœur.
def test_formula_syntax_and_semantics(logic_classes, integration_jvm):
    """
    Teste le parsing de formules logiques, la création de formules programmatiques
    et la vérification de base de leur structure.
    """
    PlParser = logic_classes["PlParser"]
    Proposition = logic_classes["Proposition"]
    Negation = logic_classes["Negation"]
    Conjunction = logic_classes["Conjunction"]
    Disjunction = logic_classes["Disjunction"]
    Implication = logic_classes["Implication"]
    Equivalence = logic_classes["Equivalence"]
    PlFormula = logic_classes["PlFormula"] # Classe de base pour les formules PL

    parser = PlParser()

    # Test 1: Parser une formule simple
    formula_str1 = "p && q"
    parsed_formula1 = parser.parseFormula(formula_str1)
    assert parsed_formula1 is not None, f"Le parsing de '{formula_str1}' ne devrait pas retourner None."
    assert isinstance(parsed_formula1, Conjunction), f"'{formula_str1}' devrait parser en Conjunction."
    assert parsed_formula1.toString() == "(p && q)", f"Représentation de '{formula_str1}' incorrecte: {parsed_formula1.toString()}"
    print(f"Parsed '{formula_str1}' as: {parsed_formula1.toString()} (type: {type(parsed_formula1)})")

    # Test 2: Parser une formule plus complexe avec négation et implication
    formula_str2 = "!(a -> b)"
    parsed_formula2 = parser.parseFormula(formula_str2)
    assert parsed_formula2 is not None
    assert isinstance(parsed_formula2, Negation)
    # La représentation toString peut varier (ex: priorité des opérateurs, parenthèses)
    # Exemple: "!((a => b))" ou similaire. L'important est la structure.
    # Pour une assertion plus robuste, on pourrait vérifier les sous-formules.
    # assert parsed_formula2.getFormula().getLeft().getName() == "a" # Exemple si la structure est connue
    print(f"Parsed '{formula_str2}' as: {parsed_formula2.toString()}")

    # Test 3: Création programmatique de formules
    prop_x = Proposition("x")
    prop_y = Proposition("y")
    
    formula_neg_x = Negation(prop_x)
    assert isinstance(formula_neg_x, Negation)
    assert formula_neg_x.getFormula().equals(prop_x)
    assert formula_neg_x.toString() == "!x" # Ou format équivalent

    formula_x_or_y = Disjunction(prop_x, prop_y)
    assert isinstance(formula_x_or_y, Disjunction)
    # La méthode getFormulas() pour Disjunction/Conjunction retourne une Collection
    # Vérifions la taille et la présence des éléments
    sub_formulas_or = formula_x_or_y.getFormulas()
    assert sub_formulas_or.size() == 2
    # Pour vérifier la présence, il faut itérer ou convertir en set Python
    py_set_or = set()
    iterator_or = sub_formulas_or.iterator()
    while iterator_or.hasNext():
        py_set_or.add(iterator_or.next())
    assert prop_x in py_set_or and prop_y in py_set_or
    assert formula_x_or_y.toString() == "(x || y)"

    formula_x_impl_y = Implication(prop_x, prop_y)
    assert isinstance(formula_x_impl_y, Implication)
    assert formula_x_impl_y.getAntecedent().equals(prop_x)
    assert formula_x_impl_y.getConsequent().equals(prop_y)
    assert formula_x_impl_y.toString() == "(x => y)"

    # Test 4: Égalité de formules (sémantique)
    # p && q est différent de q && p pour l'objet, mais sémantiquement équivalent.
    # PlFormula.equals() est typiquement basé sur la structure.
    parsed_formula_p_and_q = parser.parseFormula("p && q")
    parsed_formula_q_and_p = parser.parseFormula("q && p")
    assert not parsed_formula_p_and_q.equals(parsed_formula_q_and_p), \
        "p && q et q && p sont structurellement différents pour PlFormula.equals()"

    # Pour vérifier l'équivalence sémantique, on utiliserait un reasoner
    # ou on construirait une formule d'équivalence et on vérifierait sa validité.
    # Exemple: (p && q) <-> (q && p)
    equiv_formula_str = "(p && q) <=> (q && p)"
    parsed_equiv = parser.parseFormula(equiv_formula_str)
    assert isinstance(parsed_equiv, Equivalence)
    
    # Vérifier la validité (tautologie)
    # Un SimplePlReasoner peut être utilisé pour cela: une formule est valide si sa négation est insatisfaisable.
    # Ou, si le reasoner a une méthode isTautology().
    # SimplePlReasoner.query(empty_belief_set, formula) vérifie la validité.
    SimplePlReasoner = logic_classes["SimplePlReasoner"]
    PlBeliefSet = logic_classes["PlBeliefSet"]
    reasoner = SimplePlReasoner()
    empty_kb = PlBeliefSet() # Base de connaissance vide
    
    assert reasoner.query(empty_kb, parsed_equiv), \
        f"La formule '{equiv_formula_str}' devrait être une tautologie (valide)."

    # Test 5: Parsing d'une formule invalide (syntaxiquement)
    # Le comportement de PlParser pour les erreurs de syntaxe peut être de lever une exception.
    invalid_formula_str = "p && (q || )" # Erreur de syntaxe
    threw_exception = False
    try:
        parser.parseFormula(invalid_formula_str)
    except jpype.JException as e: # Attraper les exceptions Java
        # Le type d'exception exact peut varier (ex: ParseException, IllegalArgumentException)
        # On vérifie juste qu'une exception Java est levée.
        print(f"Exception Java attrapée comme prévu pour formule invalide '{invalid_formula_str}': {e}")
        threw_exception = True
    except Exception as e_py: # Autres exceptions Python inattendues
        pytest.fail(f"Exception Python inattendue lors du parsing de formule invalide: {e_py}")
        
    assert threw_exception, f"Le parsing de la formule syntaxiquement invalide '{invalid_formula_str}' aurait dû lever une exception Java."

    print("Test de syntaxe et sémantique des formules réussi.")
def test_list_models_of_theory(logic_classes, integration_jvm):
    """
    Teste le listage des modèles (mondes possibles) d'une théorie propositionnelle simple.
    """
    PlParser = logic_classes["PlParser"]
    PlBeliefSet = logic_classes["PlBeliefSet"]
    Proposition = logic_classes["Proposition"]
    # La classe pour itérer sur les modèles est souvent `PossibleWorldIterator` ou similaire.
    # Elle peut être spécifique à la logique (ex: `PlPossibleWorldIterator`).
    # Tweety utilise `org.tweetyproject.logics.pl.syntax.PossibleWorldIterator`.
    PossibleWorldIterator = logic_classes["PossibleWorldIterator"]
    PlSignature = logic_classes["PlSignature"]


    parser = PlParser()
    
    # Théorie simple: p && q
    theory_str = "p && q"
    belief_set_pq = parser.parseFormula(theory_str).toBeliefSet() # Convertir une formule unique en BeliefSet

    # Pour lister les modèles, nous avons besoin d'une signature (ensemble de propositions atomiques)
    sig = PlSignature()
    prop_p = Proposition("p")
    prop_q = Proposition("q")
    sig.add(prop_p)
    sig.add(prop_q)

    # Créer l'itérateur de modèles pour le belief_set et la signature
    model_iterator_pq = PossibleWorldIterator(belief_set_pq, sig)
    
    models_pq = []
    while model_iterator_pq.hasNext():
        model = model_iterator_pq.next() # model est un Set<Proposition> représentant les atomes vrais
        # Convertir le modèle Java (Set<Proposition>) en un set de noms de propositions Python
        py_model = {prop.getName() for prop in model}
        models_pq.append(py_model)

    assert len(models_pq) == 1, f"La théorie '{theory_str}' devrait avoir 1 modèle, obtenu {len(models_pq)}."
    assert {"p", "q"} in models_pq, f"Le modèle {{'p', 'q'}} est attendu pour '{theory_str}', modèles trouvés: {models_pq}."
    print(f"Modèles pour '{theory_str}': {models_pq}")

    # Théorie plus complexe: p || q
    theory_str_porq = "p || q"
    belief_set_porq = parser.parseFormula(theory_str_porq).toBeliefSet()
    
    model_iterator_porq = PossibleWorldIterator(belief_set_porq, sig)
    models_porq = []
    while model_iterator_porq.hasNext():
        model = model_iterator_porq.next()
        py_model = {prop.getName() for prop in model}
        models_porq.append(py_model)
    
    expected_models_porq = [ {"p"}, {"q"}, {"p", "q"}]
    assert len(models_porq) == len(expected_models_porq), \
        f"La théorie '{theory_str_porq}' devrait avoir {len(expected_models_porq)} modèles, obtenu {len(models_porq)}."
    
    for em in expected_models_porq:
        assert em in models_porq, f"Modèle attendu {em} non trouvé dans {models_porq} pour '{theory_str_porq}'."
    print(f"Modèles pour '{theory_str_porq}': {models_porq}")

    # Test avec la théorie du fichier sample_theory.lp
    theory_file_path = os.path.join(os.path.dirname(__file__), "sample_theory.lp")
    belief_set_file = parser.parseBeliefBaseFromFile(theory_file_path)
    
    sig_abcd = PlSignature()
    sig_abcd.add(Proposition("a"))
    sig_abcd.add(Proposition("b"))
    sig_abcd.add(Proposition("c"))
    sig_abcd.add(Proposition("d"))

    model_iterator_file = PossibleWorldIterator(belief_set_file, sig_abcd)
    models_file = []
    while model_iterator_file.hasNext():
        model = model_iterator_file.next()
        py_model = {p.getName() for p in model}
        models_file.append(py_model)

    expected_models_file = [
        {"a", "b", "c"}, 
        {"a", "b", "d"},
        {"a", "b", "c", "d"}
    ]
    assert len(models_file) == len(expected_models_file), \
        f"sample_theory.lp devrait avoir {len(expected_models_file)} modèles, obtenu {len(models_file)}. Modèles: {models_file}"
    for em in expected_models_file:
        assert em in models_file, f"Modèle attendu {em} non trouvé dans {models_file} pour sample_theory.lp."

    print(f"Modèles pour sample_theory.lp: {models_file}")
    print("Test de listage des modèles réussi.")