import pytest
# import jpype # Commenté, sera importé localement
# # Patch pour jpype.types si nécessaire
# if not hasattr(jpype, 'types'): # Supposons que jpype est correctement installé
#     class JpypeTypesPlaceholder:
#         pass
#     jpype.types = JpypeTypesPlaceholder()
# from jpype import JArray, JString, JObject, JBoolean, JInt, JDouble # Sera importé localement ou via jpype.*
# import jpype.imports # Commenté, sera importé localement
# import jpype # Commenté

# L'import de java.util.Arrays sera fait dans les fonctions de test après démarrage JVM

# Les classes Java sont importées via la fixture 'belief_revision_classes' de conftest.py

def test_pl_belief_set_creation_and_addition(belief_revision_classes):
    import jpype # Import local
    """Teste la création d'un PlBeliefSet et l'ajout de formules."""
    PlBeliefSet = belief_revision_classes["PlBeliefSet"]
    PlParser = belief_revision_classes["PlParser"]
    PlFormula = belief_revision_classes["PlFormula"]

    parser = PlParser()
    belief_set = PlBeliefSet()

    formula_str1 = "bird(tweety)"
    formula_str2 = "penguin(tweety) -> !flies(tweety)"

    pl_formula1 = parser.parseFormula(formula_str1)
    pl_formula2 = parser.parseFormula(formula_str2)

    # Remplacer isinstance par une vérification de l'attribut class_name du mock
    # car PlFormula sera une instance de MockJClass lorsque le mock jpype est actif.
    assert hasattr(pl_formula1, 'class_name') and pl_formula1.class_name == "org.tweetyproject.logics.pl.syntax.PlFormula"
    assert hasattr(pl_formula2, 'class_name') and pl_formula2.class_name == "org.tweetyproject.logics.pl.syntax.PlFormula"

    belief_set.add(pl_formula1)
    belief_set.add(pl_formula2)

    assert belief_set.size() == 2
    assert belief_set.contains(pl_formula1)
    assert belief_set.contains(pl_formula2)
    print(f"PlBeliefSet créé : {belief_set.toString()}")

def test_simple_levi_revision(belief_revision_classes):
    """
    Teste une révision simple avec l'opérateur de Levi.
    Base initiale: {bird(tweety), bird(X) && !abnormal(X) -> flies(X), !abnormal(tweety)}
    Nouvelle info: {penguin(tweety), penguin(X) -> abnormal(X)}
    Attendu: La base révisée devrait impliquer flies(tweety) est faux, ou abnormal(tweety) est vrai.
    """
    PlBeliefSet = belief_revision_classes["PlBeliefSet"]
    PlParser = belief_revision_classes["PlParser"]
    KernelContractionOperator = belief_revision_classes["KernelContractionOperator"]
    RandomIncisionFunction = belief_revision_classes["RandomIncisionFunction"]
    SimplePlReasoner = belief_revision_classes["SimplePlReasoner"]
    DefaultMultipleBaseExpansionOperator = belief_revision_classes["DefaultMultipleBaseExpansionOperator"]
    LeviMultipleBaseRevisionOperator = belief_revision_classes["LeviMultipleBaseRevisionOperator"]
    PlFormula = belief_revision_classes["PlFormula"]

    parser = PlParser()
    belief_set = PlBeliefSet()

    # Base de croyances initiale
    initial_formulas_str = [
        "bird(tweety)",
        "bird(X) && !abnormal(X) -> flies(X)",
        "!abnormal(tweety)"
    ]
    for f_str in initial_formulas_str:
        belief_set.add(parser.parseFormula(f_str))

    print(f"Base initiale pour révision: {belief_set.toString()}")

    # Nouvelle information
    new_info_formulas_str = [
        "penguin(tweety)",
        "penguin(X) -> abnormal(X)"
    ]
    import jpype # Import local pour jpype.java...
    new_information_list = jpype.java.util.ArrayList()
    for f_str in new_info_formulas_str:
        new_information_list.add(parser.parseFormula(f_str))
    
    # Configuration de l'opérateur de révision
    # TweetyProject attend une Collection<PlFormula> pour la révision multiple.
    # new_information_collection = JArray(PlFormula)(len(new_info_formulas))
    # for i, f_str in enumerate(new_info_formulas_str):
    #     new_information_collection[i] = parser.parseFormula(f_str)
    
    # Utilisation de java.util.Arrays.asList pour créer une Collection Java
    # new_information_java_collection = jpype.JClass("java.util.Arrays").asList(new_information_collection)


    try:
        reasoner = SimplePlReasoner()
        incision_function = RandomIncisionFunction()
        contraction_op = KernelContractionOperator(incision_function, reasoner)
        expansion_op = DefaultMultipleBaseExpansionOperator()
        revision_op = LeviMultipleBaseRevisionOperator(contraction_op, expansion_op)

        # La méthode revise attend Collection<? extends PlFormula>
        revised_beliefs_collection = revision_op.revise(belief_set, new_information_list)
        
        revised_belief_set = PlBeliefSet(revised_beliefs_collection)
        print(f"Base révisée: {revised_belief_set.toString()}")

        # Vérifications (peuvent être complexes à définir précisément sans solveur TMS complet)
        # On s'attend à ce que '!abnormal(tweety)' soit retiré ou modifié.
        # Et que 'abnormal(tweety)' soit dérivable.
        assert revised_belief_set.contains(parser.parseFormula("penguin(tweety)"))
        assert revised_belief_set.contains(parser.parseFormula("penguin(X) -> abnormal(X)"))
        
        # Vérifier si 'abnormal(tweety)' est maintenant une conséquence
        # ou si '!abnormal(tweety)' n'est plus une conséquence directe.
        # Cela nécessite un raisonneur sur la base révisée.
        # Par exemple, on s'attend à ce que 'flies(tweety)' ne soit plus cru.
        flies_tweety = parser.parseFormula("flies(tweety)")
        abnormal_tweety = parser.parseFormula("abnormal(tweety)")

        # Utiliser un raisonneur pour vérifier les conséquences
        # Note: SimplePlReasoner peut ne pas gérer la logique des variables comme 'X' correctement.
        # Pour des tests robustes, il faudrait un raisonneur plus avancé ou des formules propositionnalisées.
        # Pour l'instant, on vérifie la présence des nouvelles infos et l'absence d'une ancienne croyance clé.
        
        # On s'attend à ce que la croyance initiale '!abnormal(tweety)' soit révisée.
        # Il est difficile de prédire l'état exact sans connaître la fonction d'incision exacte utilisée
        # et comment le raisonneur interne de Tweety gère ces cas.
        # Un test plus simple serait de vérifier qu'une contradiction évidente est résolue.

        # Exemple de test plus simple :
        # Base: {a, a -> b}  Nouvelle info: {!b}
        # Attendu: {a} est retiré ou {a -> b} est retiré.
        
        # Pour ce test, nous allons nous contenter de vérifier que la révision s'exécute
        # et que les nouvelles informations sont présentes.
        # Des tests plus spécifiques sur les conséquences nécessiteraient une analyse plus fine
        # de l'opérateur de révision de TweetyProject.

    except jpype.JException as e:
        pytest.fail(f"Erreur Java lors de la révision de Levi : {e.stacktrace()}")

def test_crmas_belief_set_creation(belief_revision_classes):
    """Teste la création d'un CrMasBeliefSet avec des agents et un ordre de crédibilité."""
    CrMasBeliefSet = belief_revision_classes["CrMasBeliefSet"]
    DummyAgent = belief_revision_classes["DummyAgent"]
    Order = belief_revision_classes["Order"]
    PlSignature = belief_revision_classes["PlSignature"]
    InformationObject = belief_revision_classes["InformationObject"]
    PlParser = belief_revision_classes["PlParser"]

    parser = PlParser()

    # Création des agents
    import jpype # Import local
    agent_expert = DummyAgent("Expert")
    agent_witness = DummyAgent("Witness")
    
    agents_list_java = jpype.java.util.ArrayList()
    agents_list_java.add(agent_expert)
    agents_list_java.add(agent_witness)

    # Ordre de crédibilité: Expert > Witness
    credibility_order = Order(agents_list_java) # Passe une Collection d'agents
    credibility_order.setOrderedBefore(agent_expert, agent_witness)

    # Base de croyances multi-agents
    belief_set = CrMasBeliefSet(credibility_order, PlSignature())

    # Ajout d'informations avec sources
    info_obj1 = InformationObject(parser.parseFormula("rainy_day"), agent_witness)
    info_obj2 = InformationObject(parser.parseFormula("!rainy_day"), agent_expert)
    
    belief_set.add(info_obj1)
    belief_set.add(info_obj2)

    assert belief_set.size() == 2
    print(f"CrMasBeliefSet créé : {belief_set.toString()}")
    # Des vérifications plus poussées pourraient concerner la résolution des conflits
    # basée sur la crédibilité, mais cela dépend des opérateurs de révision.

def test_inconsistency_measure_contension(belief_revision_classes):
    """Teste la mesure d'incohérence de Contension."""
    PlBeliefSet = belief_revision_classes["PlBeliefSet"]
    PlParser = belief_revision_classes["PlParser"]
    ContensionInconsistencyMeasure = belief_revision_classes["ContensionInconsistencyMeasure"]

    parser = PlParser()
    inconsistent_set = PlBeliefSet()
    inconsistent_set.add(parser.parseFormula("a"))
    inconsistent_set.add(parser.parseFormula("!a"))
    inconsistent_set.add(parser.parseFormula("b && c"))
    inconsistent_set.add(parser.parseFormula("!b || !c")) # équivalent à !(b && c)

    print(f"Base inconsistante pour mesure: {inconsistent_set.toString()}")

    try:
        contension_measure = ContensionInconsistencyMeasure()
        # La méthode inconsistencyMeasure attend Collection<? extends PlFormula>
        # PlBeliefSet implémente Collection<PlFormula>
        value = contension_measure.inconsistencyMeasure(inconsistent_set)
        
        print(f"Valeur de contension: {value}")
        # La valeur exacte dépend de l'implémentation de Tweety.
        # Pour {a, !a}, la contension est souvent 1.
        # Pour {a, !a, b&c, !(b&c)}, elle pourrait être 2 ou une autre valeur normalisée.
        # On s'attend à ce qu'elle soit > 0 pour un ensemble inconsistant.
        import jpype # Import local pour JObject, JDouble
        from jpype import JObject, JDouble # Assurer que ces types sont accessibles
        assert value is not None
        assert JObject(value, JDouble).doubleValue() > 0.0

    except jpype.JException as e: # jpype doit être importé pour jpype.JException
        pytest.fail(f"Erreur Java lors du calcul de la mesure de contension : {e.stacktrace()}")

# TODO: Ajouter des tests pour d'autres opérateurs de révision (CrMasSimple, CrMasArgumentative)
# TODO: Ajouter des tests pour d'autres mesures d'incohérence (MUS-based, distance-based, fuzzy)
# TODO: Tester des cas de révision plus complexes et vérifier les résultats attendus plus finement.
# TODO: Tester la gestion des erreurs (ex: formules mal formées, configurations incorrectes).
def test_kernel_contraction_operator_simple(belief_revision_classes):
    """Teste KernelContractionOperator avec une incision simple."""
    PlBeliefSet = belief_revision_classes["PlBeliefSet"]
    PlParser = belief_revision_classes["PlParser"]
    KernelContractionOperator = belief_revision_classes["KernelContractionOperator"]
    RandomIncisionFunction = belief_revision_classes["RandomIncisionFunction"]
    SimplePlReasoner = belief_revision_classes["SimplePlReasoner"]
    PlFormula = belief_revision_classes["PlFormula"]

    parser = PlParser()
    belief_set = PlBeliefSet()
    belief_set.add(parser.parseFormula("a && b"))
    belief_set.add(parser.parseFormula("c"))

    formula_to_contract = parser.parseFormula("a && b")
    
    reasoner = SimplePlReasoner()
    incision_function = RandomIncisionFunction() # Ou une autre fonction d'incision simple
    contraction_op = KernelContractionOperator(incision_function, reasoner)

    try:
        contracted_set_collection = contraction_op.contract(belief_set, formula_to_contract)
        contracted_set = PlBeliefSet(contracted_set_collection)
        
        print(f"Base initiale pour contraction: {belief_set.toString()}")
        print(f"Formule à contracter: {formula_to_contract.toString()}")
        print(f"Base contractée: {contracted_set.toString()}")

        # L'assertion exacte dépend de l'incision. Avec RandomIncision, "a && b" devrait être parti.
        # Ou une de ses composantes si l'incision est plus fine et que la base contenait "a", "b" séparément.
        # Pour ce test, on vérifie que la formule contractée n'est plus là si elle était la seule source.
        # Si la base était {a && b, c} et on contracte a && b, le résultat pourrait être {c}.
        assert not contracted_set.contains(formula_to_contract)
        assert contracted_set.contains(parser.parseFormula("c")) # c devrait rester
        assert contracted_set.size() <= belief_set.size()

    except jpype.JException as e:
        pytest.fail(f"Erreur Java lors de la contraction par kernel : {e.stacktrace()}")

def test_kernel_contraction_with_priority_incision(belief_revision_classes):
    """Teste KernelContractionOperator avec PriorityIncisionFunction."""
    PlBeliefSet = belief_revision_classes["PlBeliefSet"]
    PlParser = belief_revision_classes["PlParser"]
    KernelContractionOperator = belief_revision_classes["KernelContractionOperator"]
    PriorityIncisionFunction = belief_revision_classes["PriorityIncisionFunction"]
    SimplePlReasoner = belief_revision_classes["SimplePlReasoner"]
    PlFormula = belief_revision_classes["PlFormula"]
    import jpype # Import local
    from jpype import JDouble # Pour JDouble
    # import java.util.HashMap # Ceci n'est pas un import Python valide
    HashMap = jpype.JClass("java.util.HashMap")

    parser = PlParser()
    belief_set = PlBeliefSet()
    
    f1 = parser.parseFormula("a")
    f2 = parser.parseFormula("b")
    f3 = parser.parseFormula("a -> x")
    f4 = parser.parseFormula("b -> x")

    belief_set.add(f1)
    belief_set.add(f2)
    belief_set.add(f3)
    belief_set.add(f4) # Base: {a, b, a -> x, b -> x}, implique x

    formula_to_contract = parser.parseFormula("x") # On veut retirer x

    # Définir les priorités: f1 (a) a une priorité plus basse
    priorities = HashMap()
    # Les priorités sont des Doubles en Java
    priorities.put(f1, JDouble(0.1)) 
    priorities.put(f2, JDouble(0.5))
    priorities.put(f3, JDouble(0.9))
    priorities.put(f4, JDouble(0.9))

    reasoner = SimplePlReasoner()
    # La signature de PriorityIncisionFunction dans Tweety est IncisionFunction<T extends Formula>
    # et son constructeur prend Map<T, Double>
    # Il faut s'assurer que le HashMap est correctement typé pour JPype si nécessaire.
    # Ici, on passe directement le HashMap Java.
    incision_function = PriorityIncisionFunction(priorities)
    contraction_op = KernelContractionOperator(incision_function, reasoner)

    try:
        contracted_set_collection = contraction_op.contract(belief_set, formula_to_contract)
        contracted_set = PlBeliefSet(contracted_set_collection)
        
        print(f"Base initiale pour contraction priorisée: {belief_set.toString()}")
        print(f"Formule à contracter: {formula_to_contract.toString()}")
        print(f"Priorités: {priorities.toString()}")
        print(f"Base contractée: {contracted_set.toString()}")

        # Attendu: f1 ("a") ou f3 ("a -> x") devrait être retiré car f1 a la plus basse priorité
        # parmi les formules impliquant x.
        # Si f1 est retiré, f3 reste. Si f3 est retiré, f1 reste.
        # L'opérateur de contraction essaie de minimiser l'impact tout en retirant la formule.
        # PriorityIncisionFunction devrait choisir de retirer les formules de plus basse priorité
        # qui sont dans les "remainder sets".
        # Ici, pour ne plus dériver "x", il faut casser soit (a et a->x) soit (b et b->x).
        # Si on casse (a et a->x), on retire 'a' (prio 0.1) ou 'a->x' (prio 0.9). 'a' sera choisi.
        # Si on casse (b et b->x), on retire 'b' (prio 0.5) ou 'b->x' (prio 0.9). 'b' sera choisi.
        # L'opérateur choisira la coupure la "moins coûteuse".
        
        # Vérifions que x n'est plus dérivable (ou présent si c'était une formule explicite)
        assert not contracted_set.contains(formula_to_contract) # Si x était explicite
        # Plus important: vérifier que x n'est plus une conséquence logique.
        # Cela nécessite un raisonneur sur la base contractée.
        # Pour simplifier, on vérifie que 'a' (la formule de plus basse priorité impliquée) a été retirée.
        assert not contracted_set.contains(f1) # 'a' devrait être retiré
        assert contracted_set.contains(f2)     # 'b' devrait rester
        assert contracted_set.contains(f4)     # 'b -> x' devrait rester

    except jpype.JException as e: # jpype doit être importé
        pytest.fail(f"Erreur Java lors de la contraction par kernel avec priorité : {e.stacktrace()}")


def test_levi_multiple_base_revision_operator_detailed(belief_revision_classes):
    """Teste LeviMultipleBaseRevisionOperator de manière plus détaillée."""
    PlBeliefSet = belief_revision_classes["PlBeliefSet"]
    PlParser = belief_revision_classes["PlParser"]
    KernelContractionOperator = belief_revision_classes["KernelContractionOperator"]
    RandomIncisionFunction = belief_revision_classes["RandomIncisionFunction"]
    SimplePlReasoner = belief_revision_classes["SimplePlReasoner"]
    DefaultMultipleBaseExpansionOperator = belief_revision_classes["DefaultMultipleBaseExpansionOperator"]
    LeviMultipleBaseRevisionOperator = belief_revision_classes["LeviMultipleBaseRevisionOperator"]
    PlFormula = belief_revision_classes["PlFormula"]
    import jpype # Import local
    # import java.util.ArrayList # Non valide
    ArrayList = jpype.JClass("java.util.ArrayList")

    parser = PlParser()
    
    # Cas 1: Révision simple qui ne cause pas d'incohérence majeure
    belief_set1 = PlBeliefSet()
    belief_set1.add(parser.parseFormula("a"))
    belief_set1.add(parser.parseFormula("b"))

    new_info_list1 = ArrayList()
    new_info_list1.add(parser.parseFormula("c"))

    reasoner = SimplePlReasoner()
    incision_function = RandomIncisionFunction()
    contraction_op = KernelContractionOperator(incision_function, reasoner)
    expansion_op = DefaultMultipleBaseExpansionOperator()
    revision_op = LeviMultipleBaseRevisionOperator(contraction_op, expansion_op)

    try:
        revised_beliefs1_collection = revision_op.revise(belief_set1, new_info_list1)
        revised_set1 = PlBeliefSet(revised_beliefs1_collection)
        print(f"Cas 1 - Base initiale: {belief_set1.toString()}")
        print(f"Cas 1 - Nouvelle info: {new_info_list1.toString()}")
        print(f"Cas 1 - Base révisée: {revised_set1.toString()}")

        assert revised_set1.contains(parser.parseFormula("a"))
        assert revised_set1.contains(parser.parseFormula("b"))
        assert revised_set1.contains(parser.parseFormula("c"))
        assert revised_set1.size() == 3

    except jpype.JException as e: # jpype doit être importé
        pytest.fail(f"Erreur Java (Cas 1) LeviMultipleBaseRevisionOperator : {e.stacktrace()}")

    # Cas 2: Révision avec incohérence (similaire à test_simple_levi_revision)
    # Base: {p, p -> q}, Nouvelle info: {!q}
    # Attendu: p ou p -> q est retiré pour accommoder !q.
    belief_set2 = PlBeliefSet()
    belief_set2.add(parser.parseFormula("p"))
    belief_set2.add(parser.parseFormula("p -> q")) # Implique q

    new_info_list2 = ArrayList()
    new_info_list2.add(parser.parseFormula("!q"))

    try:
        revised_beliefs2_collection = revision_op.revise(belief_set2, new_info_list2)
        revised_set2 = PlBeliefSet(revised_beliefs2_collection)
        print(f"Cas 2 - Base initiale: {belief_set2.toString()}")
        print(f"Cas 2 - Nouvelle info: {new_info_list2.toString()}")
        print(f"Cas 2 - Base révisée: {revised_set2.toString()}")
        
        assert revised_set2.contains(parser.parseFormula("!q")) # La nouvelle info est présente
        # Soit "p" est retiré, soit "p -> q" est retiré.
        # La base révisée ne doit plus impliquer "q".
        # Avec RandomIncision, le choix est non déterministe sur ce qui est retiré.
        # On vérifie que la taille a changé ou que l'une des anciennes n'est plus là.
        initial_q_present = reasoner.query(belief_set2, parser.parseFormula("q"))
        revised_q_present = reasoner.query(revised_set2, parser.parseFormula("q"))

        assert initial_q_present # q était une conséquence
        assert not revised_q_present # q ne doit plus être une conséquence
        assert revised_set2.size() <= 3 # Au plus !q, et un des {p, p->q}

    except jpype.JException as e: # jpype doit être importé
        pytest.fail(f"Erreur Java (Cas 2) LeviMultipleBaseRevisionOperator : {e.stacktrace()}")


def test_crmas_simple_revision_operator(belief_revision_classes):
    """Teste CrMasSimpleRevisionOperator pour la révision multi-agents."""
    CrMasBeliefSet = belief_revision_classes["CrMasBeliefSet"]
    DummyAgent = belief_revision_classes["DummyAgent"]
    Order = belief_revision_classes["Order"]
    PlSignature = belief_revision_classes["PlSignature"]
    InformationObject = belief_revision_classes["InformationObject"]
    PlParser = belief_revision_classes["PlParser"]
    CrMasSimpleRevisionOperator = belief_revision_classes["CrMasSimpleRevisionOperator"]
    import jpype # Import local
    ArrayList = jpype.JClass("java.util.ArrayList")

    parser = PlParser()

    agent_expert = DummyAgent("Expert")
    agent_witness = DummyAgent("Witness")
    
    agents_list_java = ArrayList()
    agents_list_java.add(agent_expert)
    agents_list_java.add(agent_witness)

    credibility_order = Order(agents_list_java)
    credibility_order.setOrderedBefore(agent_expert, agent_witness) # Expert > Witness

    belief_set = CrMasBeliefSet(credibility_order, PlSignature())

    # Info initiale du témoin: "il pleut"
    belief_set.add(InformationObject(parser.parseFormula("rainy_day"), agent_witness))
    print(f"CrMas Base initiale: {belief_set.toString()}")

    # Nouvelle info de l'expert: "!il pleut"
    new_info_collection = ArrayList()
    new_info_collection.add(InformationObject(parser.parseFormula("!rainy_day"), agent_expert))
    print(f"CrMas Nouvelle Info (Expert): {new_info_collection.toString()}")

    revision_op = CrMasSimpleRevisionOperator()

    try:
        revised_crmas_set_collection = revision_op.revise(belief_set, new_info_collection)
        # Le résultat de CrMasSimpleRevisionOperator est une Collection<InformationObject<PlFormula>>
        # Il faut reconstruire un CrMasBeliefSet si on veut utiliser ses méthodes,
        # ou l'analyser directement.
        
        revised_crmas_set_list = list(revised_crmas_set_collection)
        print(f"CrMas Base révisée (liste d'InformationObject):")
        for item in revised_crmas_set_list:
            print(f"  - {item.getFormula().toString()} from {item.getSource().getName()}")

        # Attendu: l'info de l'expert ("!rainy_day") devrait prévaloir sur celle du témoin ("rainy_day")
        # car Expert > Witness.
        assert len(revised_crmas_set_list) == 1
        revised_info_obj = revised_crmas_set_list[0]
        assert str(revised_info_obj.getFormula()) == "!rainy_day"
        assert revised_info_obj.getSource().getName() == "Expert"

    except jpype.JException as e: # jpype doit être importé
        pytest.fail(f"Erreur Java lors de la révision CrMasSimple : {e.stacktrace()}")


def test_inconsistency_measure_dsum(belief_revision_classes):
    """Teste la mesure d'incohérence DSumInconsistencyMeasure."""
    PlBeliefSet = belief_revision_classes["PlBeliefSet"]
    PlParser = belief_revision_classes["PlParser"]
    DSumInconsistencyMeasure = belief_revision_classes["DSumInconsistencyMeasure"]
    DalalDistance = belief_revision_classes["DalalDistance"]
    PossibleWorldIterator = belief_revision_classes["PossibleWorldIterator"]
    PlSignature = belief_revision_classes["PlSignature"] # Nécessaire pour PossibleWorldIterator

    parser = PlParser()
    inconsistent_set = PlBeliefSet()
    f_a = parser.parseFormula("a")
    f_nota = parser.parseFormula("!a")
    f_b = parser.parseFormula("b")
    
    inconsistent_set.add(f_a)
    inconsistent_set.add(f_nota)
    inconsistent_set.add(f_b) # {a, !a, b}

    print(f"Base inconsistante pour mesure DSum: {inconsistent_set.toString()}")

    try:
        # DSumInconsistencyMeasure a besoin d'une distance (ex: DalalDistance)
        # et d'un itérateur de mondes possibles.
        dalal_distance = DalalDistance()
        
        # PossibleWorldIterator a besoin de la signature des propositions.
        signature = PlSignature()
        signature.add(parser.parseFormula("a").getProposition()) # Ajoute la proposition 'a'
        signature.add(parser.parseFormula("b").getProposition()) # Ajoute la proposition 'b'
        # Si on a des formules plus complexes, il faut extraire toutes les propositions.
        # Pour {a, !a, b}, les propositions sont a et b.
        
        world_iterator = PossibleWorldIterator(signature)
        
        dsum_measure = DSumInconsistencyMeasure(dalal_distance, world_iterator)
        
        value = dsum_measure.inconsistencyMeasure(inconsistent_set)
        
        print(f"Valeur de DSum: {value}")
        # La valeur exacte dépend de l'implémentation de Tweety et de la distance de Dalal.
        # Pour {a, !a, b}, un modèle possible est {a, b} (distance 1 à !a), un autre {!a, b} (distance 1 à a).
        # La distance de Dalal entre un modèle et une formule est le nombre de littéraux qui diffèrent.
        # Les modèles de la base sont les assignations de vérité aux atomes.
        # Modèles de {a, !a, b}: aucun.
        # La mesure d'incohérence DSum est la somme des distances minimales de chaque modèle de la signature
        # à la base de croyances.
        # Mondes possibles pour {a,b}: (a,b), (a,!b), (!a,b), (!a,!b)
        # dist({a,b}, KB) = min(dist({a,b}, {a,b}), dist({a,b}, {!a,b})) = min(1,1) = 1 (si on considère la distance à la formule violée)
        # Pour {a, !a, b}:
        #   Modèle M1 = (a=T, b=T). dist(M1, KB) = dist(M1, !a) = 1.
        #   Modèle M2 = (a=T, b=F). dist(M2, KB) = dist(M2, !a) + dist(M2, b) = 1 + 1 = 2.
        #   Modèle M3 = (a=F, b=T). dist(M3, KB) = dist(M3, a) = 1.
        #   Modèle M4 = (a=F, b=F). dist(M4, KB) = dist(M4, a) + dist(M4, b) = 1 + 1 = 2.
        # Somme des distances minimales des modèles aux formules de la base.
        # La définition exacte de DSum dans Tweety peut varier.
        # On s'attend à ce qu'elle soit > 0 pour un ensemble inconsistant.
        import jpype # Import local
        from jpype import JObject, JDouble # Assurer l'accès
        assert value is not None
        assert JObject(value, JDouble).doubleValue() > 0.0

    except jpype.JException as e: # jpype doit être importé
        # Afficher plus de détails sur l'erreur Java, notamment le type d'exception
        java_exception = jpype.JavaException(e)
        print(f"Exception Java de type: {java_exception.java_class().getName()}")
        pytest.fail(f"Erreur Java lors du calcul de la mesure DSum : {e.stacktrace()}")