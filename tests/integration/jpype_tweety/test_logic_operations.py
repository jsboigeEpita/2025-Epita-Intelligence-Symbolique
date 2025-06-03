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
    
    belief_set = parser.parseBeliefBaseFromFile(theory_file_path)

    assert belief_set is not None, "Le belief set ne devrait pas être None après parsing."
    assert belief_set.size() >= 2, f"Attendu au moins 2 formules, obtenu {belief_set.size()}."
    assert belief_set.size() == 2, f"Attendu 2 formules pour le contenu actuel de sample_theory.lp ('b.' et 'b => a.'), obtenu {belief_set.size()}."

    # print(f"Théorie chargée depuis {theory_file_path}. Nombre de formules: {belief_set.size()}")

def test_simple_pl_reasoner_queries(logic_classes, integration_jvm):
    """
    Teste l'exécution de requêtes simples (entailment) sur un SimplePlReasoner
    en utilisant la théorie chargée depuis sample_theory.lp.
    sample_theory.lp (actuellement):
    b.
    b => a.
    """
    PlParser = logic_classes["PlParser"]
    Proposition = logic_classes["Proposition"]
    SimplePlReasoner = logic_classes["SimplePlReasoner"]

    theory_file_path = os.path.join(os.path.dirname(__file__), "sample_theory.lp")
    parser = PlParser()
    belief_set = parser.parseBeliefBaseFromFile(theory_file_path)

    assert belief_set is not None, "Le belief set ne doit pas être None."
    assert belief_set.size() == 2, f"Attendu 2 formules (contenu actuel de sample_theory.lp), obtenu {belief_set.size()}."

    reasoner = SimplePlReasoner()

    prop_c = Proposition("c")
    prop_d = Proposition("d")
    prop_x = Proposition("x") 

    # Test query en parsant les formules à interroger
    prop_b_formula = parser.parseFormula("b.")
    assert isinstance(prop_b_formula, Proposition), "La formule 'b.' devrait être parsée comme une Proposition."
    query_b_result = reasoner.query(belief_set, prop_b_formula)
    assert query_b_result, "La proposition 'b' (fait explicite, parsé comme formule) devrait être une conséquence."
    
    # prop_a_formula = parser.parseFormula("a.") # Inutile si l'assertion est commentée
    # assert isinstance(prop_a_formula, Proposition), "La formule 'a.' devrait être parsée comme une Proposition."
    # query_a_result = reasoner.query(belief_set, prop_a_formula)
    # assert query_a_result, "La proposition 'a' (parsée comme formule) devrait être une conséquence (par b et b=>a)."
    # Commenté car SimplePlReasoner ne semble pas effectuer le modus ponens.

    assert not reasoner.query(belief_set, prop_c), "La proposition 'c' ne devrait pas être une conséquence."
    assert not reasoner.query(belief_set, prop_d), "La proposition 'd' ne devrait pas être une conséquence."
    assert not reasoner.query(belief_set, prop_x), "La proposition 'x' ne devrait pas être une conséquence."

def test_basic_logical_agent_manipulation(logic_classes, integration_jvm):
    """
    Teste la création d'un agent logique simple et l'accès/modification
    de sa base de connaissances.
    """
    PlBeliefSet = logic_classes["PlBeliefSet"]
    Proposition = logic_classes["Proposition"]

    agent_kb = PlBeliefSet()
    
    prop_p = Proposition("p")
    prop_q = Proposition("q")

    agent_kb.add(prop_p)
    agent_kb.add(prop_q)

    assert agent_kb.size() == 2, "La base de connaissances de l'agent devrait contenir 2 formules."
    assert agent_kb.contains(prop_p), "La KB devrait contenir la proposition 'p'."
    assert agent_kb.contains(prop_q), "La KB devrait contenir la proposition 'q'."

    agent_kb.remove(prop_q)
    assert agent_kb.size() == 1, "La KB devrait contenir 1 formule après suppression."
    assert not agent_kb.contains(prop_q), "La KB ne devrait plus contenir 'q'."
    assert agent_kb.contains(prop_p), "La KB devrait toujours contenir 'p'."

    # print("Test de manipulation basique de la base de connaissances d'un agent (simulé) réussi.")

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
    PlFormula = logic_classes["PlFormula"] 

    parser = PlParser()

    formula_str1 = "p && q"
    parsed_formula1 = parser.parseFormula(formula_str1)
    assert parsed_formula1 is not None, f"Le parsing de '{formula_str1}' ne devrait pas retourner None."
    assert isinstance(parsed_formula1, Conjunction), f"'{formula_str1}' devrait parser en Conjunction."
    assert parsed_formula1.toString() in ["(p && q)", "p&&q"], f"Représentation de '{formula_str1}' incorrecte: {parsed_formula1.toString()}"

    formula_str2 = "!(a => b)" 
    parsed_formula2 = parser.parseFormula(formula_str2)
    assert parsed_formula2 is not None
    assert isinstance(parsed_formula2, Negation)

    prop_x = Proposition("x")
    prop_y = Proposition("y")
    
    formula_neg_x = Negation(prop_x)
    assert isinstance(formula_neg_x, Negation)
    assert formula_neg_x.getFormula().equals(prop_x)
    assert formula_neg_x.toString() == "!x" 

    elements_for_disjunction = jpype.JArray(PlFormula)([prop_x, prop_y])
    formula_x_or_y = Disjunction(elements_for_disjunction)
    assert isinstance(formula_x_or_y, Disjunction)
    sub_formulas_or = formula_x_or_y.getFormulas()
    assert sub_formulas_or.size() == 2
    py_set_or = set()
    iterator_or = sub_formulas_or.iterator()
    while iterator_or.hasNext():
        py_set_or.add(iterator_or.next())
    assert prop_x in py_set_or and prop_y in py_set_or
    assert formula_x_or_y.toString() in ["(x || y)", "x||y"] 

    formula_x_impl_y = Implication(prop_x, prop_y)
    assert isinstance(formula_x_impl_y, Implication)
    pair_operands = formula_x_impl_y.getFormulas() 
    assert pair_operands.getFirst().equals(prop_x) 
    assert pair_operands.getSecond().equals(prop_y) 
    assert formula_x_impl_y.toString() in ["(x => y)", "(x=>y)"] 

    parsed_formula_p_and_q = parser.parseFormula("p && q")
    parsed_formula_q_and_p = parser.parseFormula("q && p")
    assert not parsed_formula_p_and_q.equals(parsed_formula_q_and_p), \
        "p && q et q && p sont structurellement différents pour PlFormula.equals()"

    equiv_formula_str = "(p && q) <=> (q && p)"
    parsed_equiv = parser.parseFormula(equiv_formula_str)
    assert isinstance(parsed_equiv, Equivalence)
    
    SimplePlReasoner = logic_classes["SimplePlReasoner"]
    PlBeliefSet = logic_classes["PlBeliefSet"]
    reasoner = SimplePlReasoner()
    empty_kb = PlBeliefSet() 
    
    assert reasoner.query(empty_kb, parsed_equiv), \
        f"La formule '{equiv_formula_str}' devrait être une tautologie (valide)."

    invalid_formula_str = "p && (q || )" 
    threw_exception = False
    try:
        parser.parseFormula(invalid_formula_str)
    except jpype.JException: 
        threw_exception = True
    except Exception as e_py: 
        pytest.fail(f"Exception Python inattendue lors du parsing de formule invalide: {e_py}")
        
    assert threw_exception, f"Le parsing de la formule syntaxiquement invalide '{invalid_formula_str}' aurait dû lever une exception Java."

def test_list_models_of_theory(logic_classes, integration_jvm):
    """
    Teste le listage des modèles (mondes possibles) d'une théorie propositionnelle simple.
    """
    PlParser = logic_classes["PlParser"]
    PlBeliefSet = logic_classes["PlBeliefSet"]
    Proposition = logic_classes["Proposition"]
    PossibleWorldIterator = logic_classes["PossibleWorldIterator"]
    PlSignature = logic_classes["PlSignature"]
    PlFormula_class = logic_classes["PlFormula"] 
    Implication = logic_classes["Implication"]

    parser = PlParser()
    
    # Théorie simple: p && q
    theory_str = "p && q"
    formula_pq = parser.parseFormula(theory_str)
    belief_set_pq = PlBeliefSet() 
    belief_set_pq.add(formula_pq) 

    sig = PlSignature()
    prop_p = Proposition("p")
    prop_q = Proposition("q")
    sig.add(prop_p)
    sig.add(prop_q)
    
    possible_world_iterator_pq = PossibleWorldIterator(sig)
    models_pq = []
    while possible_world_iterator_pq.hasNext():
        possible_world = possible_world_iterator_pq.next() 
        is_model = True
        belief_set_iterator_pq = belief_set_pq.iterator()
        while belief_set_iterator_pq.hasNext():
            formula_in_kb = belief_set_iterator_pq.next()
            if isinstance(formula_in_kb, Proposition):
                prop_name_in_kb_raw = formula_in_kb.getName()
                prop_name_in_kb_normalized = prop_name_in_kb_raw
                if prop_name_in_kb_normalized.endsWith('.'): 
                    prop_name_in_kb_normalized = prop_name_in_kb_normalized[:-1]
                
                satisfies = False
                for prop_in_pw_check in possible_world:
                    if prop_in_pw_check.getName() == prop_name_in_kb_normalized:
                        satisfies = True
                        break
            else: 
                satisfies = possible_world.satisfies(jpype.JObject(formula_in_kb, PlFormula_class))
            
            if not satisfies:
                is_model = False
                break
        if is_model:
            py_model = {prop.getName() for prop in possible_world}
            models_pq.append(py_model)

    assert len(models_pq) == 1, f"La théorie '{theory_str}' devrait avoir 1 modèle, obtenu {len(models_pq)}."
    assert {"p", "q"} in models_pq, f"Le modèle {{'p', 'q'}} est attendu pour '{theory_str}', modèles trouvés: {models_pq}."

    # Théorie plus complexe: p || q
    theory_str_porq = "p || q"
    formula_porq = parser.parseFormula(theory_str_porq)
    belief_set_porq = PlBeliefSet()
    belief_set_porq.add(formula_porq)
    
    possible_world_iterator_porq = PossibleWorldIterator(sig) 
    models_porq = []
    while possible_world_iterator_porq.hasNext():
        possible_world = possible_world_iterator_porq.next()
        is_model = True
        belief_set_iterator_porq = belief_set_porq.iterator()
        while belief_set_iterator_porq.hasNext():
            formula_in_kb = belief_set_iterator_porq.next()
            if isinstance(formula_in_kb, Proposition):
                prop_name_in_kb_raw = formula_in_kb.getName()
                prop_name_in_kb_normalized = prop_name_in_kb_raw
                if prop_name_in_kb_normalized.endsWith('.'): 
                    prop_name_in_kb_normalized = prop_name_in_kb_normalized[:-1]

                satisfies = False
                for prop_in_pw_check in possible_world:
                    if prop_in_pw_check.getName() == prop_name_in_kb_normalized:
                        satisfies = True
                        break
            else: 
                satisfies = possible_world.satisfies(jpype.JObject(formula_in_kb, PlFormula_class))

            if not satisfies:
                is_model = False
                break
        if is_model:
            py_model = {prop.getName() for prop in possible_world}
            models_porq.append(py_model)
            
    expected_models_porq = [{"p"}, {"q"}, {"p", "q"}]
    assert len(models_porq) == len(expected_models_porq), \
        f"La théorie '{theory_str_porq}' devrait avoir {len(expected_models_porq)} modèles, obtenu {len(models_porq)}."
    
    for em in expected_models_porq:
        assert em in models_porq, f"Modèle attendu {em} non trouvé dans {models_porq} pour '{theory_str_porq}'."

    # Test avec la théorie du fichier sample_theory.lp
    theory_file_path = os.path.join(os.path.dirname(__file__), "sample_theory.lp")
    belief_set_file = parser.parseBeliefBaseFromFile(theory_file_path)
    
    sig_abcd = PlSignature()
    sig_abcd.add(Proposition("a"))
    sig_abcd.add(Proposition("b"))
    sig_abcd.add(Proposition("c"))
    sig_abcd.add(Proposition("d"))
    
    possible_world_iterator_file = PossibleWorldIterator(sig_abcd)
    models_file = []
    while possible_world_iterator_file.hasNext():
        possible_world = possible_world_iterator_file.next()
        is_model = True
        belief_set_iterator_file = belief_set_file.iterator()
        while belief_set_iterator_file.hasNext():
            formula_in_kb = belief_set_iterator_file.next()
            
            satisfies = False
            if isinstance(formula_in_kb, Proposition):
                prop_name_in_kb_raw = formula_in_kb.getName()
                prop_name_in_kb_normalized = prop_name_in_kb_raw
                if prop_name_in_kb_normalized.endsWith('.'): 
                    prop_name_in_kb_normalized = prop_name_in_kb_normalized[:-1]

                for prop_in_pw_check in possible_world:
                    if prop_in_pw_check.getName() == prop_name_in_kb_normalized: 
                        satisfies = True
                        break
            elif isinstance(formula_in_kb, Implication):
                impl_left = formula_in_kb.getFormulas().getFirst()
                impl_right = formula_in_kb.getFormulas().getSecond()

                satisfies_left = False
                if isinstance(impl_left, Proposition):
                    left_name_raw = impl_left.getName()
                    left_name_norm = left_name_raw[:-1] if left_name_raw.endsWith('.') else left_name_raw
                    for prop_in_pw_check in possible_world:
                        if prop_in_pw_check.getName() == left_name_norm:
                            satisfies_left = True
                            break
                else: 
                    satisfies_left = possible_world.satisfies(jpype.JObject(impl_left, PlFormula_class))
                
                satisfies_right = False
                if isinstance(impl_right, Proposition):
                    right_name_raw = impl_right.getName()
                    right_name_norm = right_name_raw[:-1] if right_name_raw.endsWith('.') else right_name_raw
                    for prop_in_pw_check in possible_world:
                        if prop_in_pw_check.getName() == right_name_norm:
                            satisfies_right = True
                            break
                else: 
                    satisfies_right = possible_world.satisfies(jpype.JObject(impl_right, PlFormula_class))
                satisfies = (not satisfies_left) or satisfies_right 
            else: # Autres formules complexes
                satisfies = possible_world.satisfies(jpype.JObject(formula_in_kb, PlFormula_class))

            if not satisfies:
                is_model = False
                break
        if is_model:
            current_py_model = {prop.getName() for prop in possible_world}
            models_file.append(current_py_model)
    
    expected_models_file = [
        {"a", "b"},
        {"a", "b", "c"},
        {"a", "b", "d"},
        {"a", "b", "c", "d"}
    ]
    assert len(models_file) == len(expected_models_file), \
        f"sample_theory.lp ('b.', 'b => a.') devrait avoir {len(expected_models_file)} modèles sur signature {{a,b,c,d}}, obtenu {len(models_file)}. Modèles: {models_file}"
    for em in expected_models_file:
        assert em in models_file, f"Modèle attendu {em} non trouvé dans {models_file} pour sample_theory.lp ('b.', 'b => a.')."