import os # jpype et jpype.imports seront importés dans la fonction
# from jpype.types import JString # Sera importé si nécessaire

def test_reasoner_query(integration_jvm): # Ajout de la fixture integration_jvm
    import jpype # Importation locale
    import jpype.imports
    from jpype.types import JString

    try:
        print("Démarrage du test du raisonneur et de requête simple...")

        # L'initialisation de la JVM est maintenant gérée globalement par conftest.py
        if not jpype.isJVMStarted():
            # Cette condition ne devrait plus être vraie si conftest.py fonctionne correctement.
            print("ERREUR CRITIQUE: La JVM n'a pas été démarrée par conftest.py comme attendu dans test_reasoner_query.")
            # Lever une exception pour que le test échoue clairement si la JVM n'est pas prête.
            raise RuntimeError("JVM non démarrée par conftest.py, test_reasoner_query ne peut pas continuer.")
        from org.tweetyproject.logics.pl.syntax import PlBeliefSet
        from org.tweetyproject.logics.pl.parser import PlParser
        from org.tweetyproject.logics.pl.syntax import PlSignature, Proposition
        from org.tweetyproject.logics.pl.reasoner import SimplePlReasoner
        from org.tweetyproject.logics.commons.syntax import Predicate

        print("JVM démarrée et classes Tweety importées.")

        # theory_file_path = os.path.join(os.path.dirname(__file__), "sample_theory.lp")
        # print(f"Chemin du fichier de théorie : {theory_file_path}")

        # if not os.path.exists(theory_file_path):
        #     raise FileNotFoundError(f"Le fichier de théorie {theory_file_path} n'a pas été trouvé.")

        parser = PlParser()
        # JFile = jpype.JClass("java.io.File")
        # java_file = JFile(JString(theory_file_path))
        # belief_set_from_file = parser.parseBeliefBaseFromFile(theory_file_path)
        # print(f"Théorie chargée depuis fichier. Nombre de formules : {belief_set_from_file.size()}")

        # Construction programmatique du PlBeliefSet
        belief_set = PlBeliefSet()
        prop_a = parser.parseFormula(JString("a")) # Proposition a
        prop_b = parser.parseFormula(JString("b")) # Proposition b
        # prop_c = parser.parseFormula(JString("c")) # Proposition c
        # prop_d = parser.parseFormula(JString("d")) # Proposition d

        # Ajout de "b." (b est un fait)
        belief_set.add(prop_b)
        print(f"Ajout de '{prop_b.toString()}' au belief_set.")

        # Ajout de "a :- b." (a si b)
        # Une implication "X :- Y" est équivalente à "Y => X" ou "!Y || X"
        # TweetyProject utilise souvent des classes spécifiques pour les implications ou les parse directement.
        # Essayons de parser la règle directement.
        rule_a_if_b = parser.parseFormula(JString("b => a")) # ou "a :- b" si le parser le gère pour les formules individuelles
        belief_set.add(rule_a_if_b)
        print(f"Ajout de la règle '{rule_a_if_b.toString()}' au belief_set.")
        
        # Optionnel: ajout des autres règles pour la complétude si nécessaire pour d'autres tests,
        # mais pour "a", ce qui précède devrait suffire.
        # rule_c_if_not_d = parser.parseFormula(JString("not d => c"))
        # belief_set.add(rule_c_if_not_d)
        # print(f"Ajout de la règle '{rule_c_if_not_d.toString()}' au belief_set.")
        # rule_d_if_not_c = parser.parseFormula(JString("not c => d"))
        # belief_set.add(rule_d_if_not_c)
        # print(f"Ajout de la règle '{rule_d_if_not_c.toString()}' au belief_set.")


        print(f"Théorie construite programmatiquement. Nombre de formules : {belief_set.size()}")

        print("Formules dans belief_set (construit programmatiquement):")
        # Tentative d'itération directe sur belief_set ou via sa méthode iterator()
        # PlBeliefSet pourrait implémenter Iterable ou avoir une méthode iterator()
        try:
            java_iterator = belief_set.iterator() # Standard pour les collections Java
            while java_iterator.hasNext():
                print(f"  - {java_iterator.next().toString()}")
        except AttributeError:
            print("  - belief_set.iterator() n'est pas disponible. Tentative d'autres approches si nécessaire ou log d'erreur.")
            # Si PlBeliefSet est une collection de formules, il pourrait être directement itérable en Python via JPype
            # ou nécessiter une conversion explicite si JPype ne le gère pas automatiquement.
            # Pour l'instant, on logue et on continue pour voir si le reste du test fonctionne,
            # bien que l'inspection des formules soit utile.

        print("Méthodes de belief_set:", dir(belief_set))

        # Instancier un raisonneur simple
        reasoner = SimplePlReasoner()
            # Le belief_set sera pass  la mthode query
        print("SimpleReasoner instancié.")
        print("Méthodes de reasoner:", dir(reasoner))

        # Créer une formule à interroger (par exemple, "a")
        # D'abord, créer une signature propositionnelle si nécessaire ou l'obtenir
        # Pour créer une Proposition, nous avons besoin d'un Predicate.
        # Un Predicate a un nom et une arité (0 pour les propositions).
        
        # Créer la proposition "a"
        # Note: La création de propositions peut varier.
        # Souvent, on les parse à partir d'une chaîne ou on les construit.
        # Si le parser peut parser une seule formule :
        query_formula_str = "a"
        # query_formula = parser.parseFormula(JString(query_formula_str))
        
        # Alternativement, construire la proposition directement:
        # Obtenir la signature de la base de connaissances ou créer une nouvelle
        signature = belief_set.getSignature()
        if not signature:
            # Si la signature n'est pas automatiquement créée ou récupérable,
            # il faut la créer manuellement et s'assurer que les propositions y sont.
            # Pour cet exemple, nous supposons que le parser crée les propositions
            # et qu'elles sont accessibles ou que le raisonneur peut les gérer.
            # Une manière plus directe de créer une proposition si elle existe déjà dans la signature :
            # Proposition propA = signature.getProposition("a");
            # Cependant, si "a" n'est pas explicitement dans la signature (par ex. si elle est vide au départ),
            # il faut la créer.
            # Le plus simple est souvent de parser la formule.
            # Si PlParser.parseFormula n'existe pas ou ne fonctionne pas comme attendu,
            # on peut créer un Predicate et ensuite une Proposition.
            # predicate_a = Predicate("a", 0) # Nom "a", arité 0
            # query_formula = Proposition(predicate_a)
            # Ou, si le parser a une méthode pour parser une formule simple :
            query_formula = parser.parseFormula(JString("a"))

        else:
            # Essayer de récupérer la proposition de la signature existante
            # Ou parser la formule directement
            query_formula = parser.parseFormula(JString("a"))


        print(f"Formule de requête créée : {query_formula.toString()}")

        # Vérifier si la formule est une conséquence
        is_consequence = reasoner.query(belief_set, query_formula)
        print(f"La formule '{query_formula.toString()}' est-elle une conséquence ? {is_consequence}")

        if is_consequence:
            print("Test du raisonneur et de requête simple RÉUSSI (a est une conséquence).")
        else:
            # Dans notre sample_theory.lp, "a" est une conséquence (a :- b. et b.)
            raise AssertionError(f"ÉCHEC : La formule '{query_formula.toString()}' devrait être une conséquence, mais le raisonneur a retourné {is_consequence}.")

    except Exception as e:
        print(f"Test du raisonneur et de requête simple ÉCHOUÉ : {e}")
        import traceback
        traceback.print_exc()
        raise

    # finally: # Commenté pour permettre à pytest de gérer la JVM via conftest
        # if jpype.isJVMStarted():
        #     jpype.shutdownJVM()
        #     print("JVM arrêtée.")
        pass