import os # jpype et jpype.imports seront importés dans la fonction

# from jpype.types import JString # Sera importé si nécessaire dans la fonction

def test_list_models(integration_jvm): # Ajout de la fixture integration_jvm
    import jpype # Importation locale
    import jpype.imports
    from jpype.types import JString

    try:
        print("Démarrage du test de listage des modèles...")

        # L'initialisation de la JVM est maintenant gérée globalement par conftest.py
        if not jpype.isJVMStarted():
            # Cette condition ne devrait plus être vraie si conftest.py fonctionne correctement.
            # Lever une erreur ou un skip si la JVM n'est pas démarrée comme attendu.
            print("ERREUR CRITIQUE: La JVM n'a pas été démarrée par conftest.py comme attendu.")
            # On pourrait utiliser pytest.skip ou lever une exception pour arrêter le test.
            # Pour l'instant, on logue et on laisse le test échouer plus loin si les imports Java échouent.
            # raise RuntimeError("JVM non démarrée par conftest.py") # Optionnel: être plus strict
        from org.tweetyproject.logics.pl.syntax import PlBeliefSet
        from org.tweetyproject.logics.pl.parser import PlParser
        # from org.tweetyproject.logics.pl.reasoner import SimplePlReasoner, SatReasoner
        from org.tweetyproject.logics.pl.sat import SatSolver, Sat4jSolver, SimpleModelEnumerator
        from org.tweetyproject.logics.pl.syntax import Proposition, Implication, Negation # Ajout Implication, Negation
        from org.tweetyproject.logics.pl.semantics import PossibleWorld # PossibleWorld est un alias pour PlInterpretation
        JArrayList = jpype.JClass("java.util.ArrayList")
        # from org.tweetyproject.commons import InterpretationSet # Pas nécessaire d'importer directement si on itère sur le résultat de getModels
        
        print("JVM démarrée et classes Tweety importées.")
        
        # Configuration du solveur SAT par défaut
        SatSolver_JClass = jpype.JClass("org.tweetyproject.logics.pl.sat.SatSolver")
        Sat4jSolver_JClass = jpype.JClass("org.tweetyproject.logics.pl.sat.Sat4jSolver")
        if not SatSolver_JClass.hasDefaultSolver(): # Correction: isDefaultSolverSet -> hasDefaultSolver
            SatSolver_JClass.setDefaultSolver(Sat4jSolver_JClass())
            print("INFO: Sat4jSolver configuré comme solveur par défaut pour PL.")
        else:
            print("INFO: Un solveur SAT par défaut est déjà configuré.")

        # Construction manuelle de la PlBeliefSet pour isoler du parsing
        print("Construction manuelle de la PlBeliefSet...")
        belief_set = PlBeliefSet()
        p_a = Proposition("a")
        p_b = Proposition("b")
        p_c = Proposition("c")
        p_d = Proposition("d")

        # b.
        belief_set.add(p_b)
        # a :- b.  (b => a)
        belief_set.add(Implication(p_b, p_a))
        # c :- not d. (not d => c)
        belief_set.add(Implication(Negation(p_d), p_c))
        # d :- not c. (not c => d)
        belief_set.add(Implication(Negation(p_c), p_d))
        print(f"PlBeliefSet construite manuellement. Nombre de formules : {belief_set.size()}")
        
        # theory_file_path = os.path.join(os.path.dirname(__file__), "sample_theory.lp")
        # print(f"Chemin du fichier de théorie : {theory_file_path}")

        # if not os.path.exists(theory_file_path):
        #     raise FileNotFoundError(f"Le fichier de théorie {theory_file_path} n'a pas été trouvé.")

        # parser = PlParser()
        # JFile = jpype.JClass("java.io.File")
        # java_file = JFile(JString(theory_file_path))
        # belief_set = parser.parseBeliefBaseFromFile(theory_file_path)

        # print(f"Théorie chargée avec succès. Nombre de formules : {belief_set.size()}") # Commenté car belief_set est manuel
        print("Formules dans le belief_set (construites manuellement):")
        formulas_iterator = belief_set.iterator()
        formula_idx = 0
        while formulas_iterator.hasNext():
            formula = formulas_iterator.next()
            print(f"- Formule {formula_idx}: {formula.toString()}")
            formula_idx += 1
        
        # Instancier un raisonneur simple
        # Note: SimpleReasoner ne fournit pas directement une méthode getModels().
        # Pour obtenir les modèles, on utilise souvent un solver spécifique ou un raisonneur plus avancé,
        # ou on vérifie la satisfiabilité.
        # Cependant, si l'objectif est de lister les modèles,
        # il faut s'assurer que le raisonneur utilisé le permet.
        # Pour la logique propositionnelle, `SatReasoner` est plus approprié pour lister les modèles.
        # from net.sf.tweety.arg.dung.reasoner import SatReasoner <- Ceci est pour l'argumentation
        # Pour la logique PL, il faut un solveur SAT. Tweety intègre des solveurs.
        # Par exemple, net.sf.tweety.logics.pl.sat.Sat4jSolver
        # from org.tweetyproject.logics.pl.sat import Sat4jSolver, SimpleModelEnumerator, SimpleModelEnumerator # ou un autre solveur SAT disponible

        # Si SimpleReasoner ne peut pas lister les modèles, ce test devra être adapté
        # ou utiliser un autre raisonneur.
        # Vérifions la documentation de Tweety ou les exemples pour le listage de modèles.
        # Typiquement, un `ModelEnumerator` ou une méthode sur un `SatSolver` est utilisée.

        # Pour l'instant, supposons que nous voulons vérifier la cohérence (existence d'au moins un modèle)
        # ou si un raisonneur plus apte est disponible.
        # Si `SimpleReasoner` ne peut pas lister les modèles, nous allons utiliser `Sat4jSolver`
        # qui est un wrapper pour un solveur SAT et peut généralement énumérer les modèles.

        # Tentative avec un solveur SAT si SimpleReasoner ne suffit pas.
        # Assurez-vous que le JAR de Sat4j (ou un autre solveur configuré) est dans le classpath.
        # Suppression du bloc try-except pour Sat4jSolver et setDefaultSolver (lignes 64-78)
        # et de l'instanciation de SimpleModelEnumerator

        # Obtenir les modèles de la base de connaissances en utilisant SimpleModelEnumerator.
        # Tentative de définition du solveur SAT par défaut sur Sat4jSolver,
        # en espérant que SimpleModelEnumerator() l'utilisera et trouvera tous les modèles.

        # Utilisation directe de SimpleModelEnumerator(), car les tentatives de configuration du solveur
        # via constructeur ou setDefaultSolver avec setFindAllModels n'ont pas fonctionné comme attendu
        # ou ont causé des erreurs.
        # SimpleModelEnumerator() est la seule forme qui n'a pas levé d'AttributeError/TypeError pour l'appel getModels.
        # Instancier Sat4jSolver explicitement
        # explicit_sat4j_solver = Sat4jSolver_JClass() # Plus nécessaire si le défaut est bien pris
        # print("Sat4jSolver instancié explicitement.") # Commenté

        # Tenter d'utiliser SimpleModelEnumerator avec ce solveur spécifique si possible,
        # ou s'assurer que le solveur par défaut est bien celui-ci.
        # La documentation de SimpleModelEnumerator ne montre pas de constructeur acceptant un solver.
        # On continue de se fier à setDefaultSolver.
        
        print("Utilisation de SimpleModelEnumerator (après configuration du solveur par défaut).")

        # Instancier SimpleModelEnumerator. Il utilisera le solveur configuré par défaut.
        model_enumerator = SimpleModelEnumerator()
        
        # PlBeliefSet est une Collection<PlFormula>.
        # La méthode getModels(Collection<? extends PlFormula>) de SimpleModelEnumerator retourne Set<InterpretationSet>.
        java_models_set = model_enumerator.getModels(belief_set) # Doit retourner Set<InterpretationSet>

        model_count = java_models_set.size() # Obtenir la taille directement
        print(f"Nombre de modèles trouvés : {model_count}")

        if java_models_set.isEmpty():
            print("Aucun modèle trouvé. La théorie est incohérente.")
            raise AssertionError("ÉCHEC : Aucun modèle trouvé pour une théorie cohérente.")
        else:
            print("Modèles trouvés (détail de l'interprétation via InterpretationSet) :")
            
            # Obtenir la signature de la belief_set
            # signature = belief_set.getMinimalSignature() # Ne semble pas retourner les atomes simples.
            
            # Définir manuellement les propositions atomiques d'intérêt pour l'affichage
            Proposition_JClass = jpype.JClass("org.tweetyproject.logics.pl.syntax.Proposition")
            propositions_for_interpretation = [
                Proposition_JClass("a"),
                Proposition_JClass("b"),
                Proposition_JClass("c"),
                Proposition_JClass("d")
            ]
            print(f"Propositions utilisées pour l'interprétation des modèles: {[p.getName() for p in propositions_for_interpretation]}")
        
            actual_model_index = 0
            # java_models_set est un java.util.Set<org.tweetyproject.logics.pl.semantics.PossibleWorld>
            java_set_iterator = java_models_set.iterator()
            while java_set_iterator.hasNext():
                possible_world = java_set_iterator.next() # C'est un PossibleWorld (PlInterpretation)
                actual_model_index += 1
                current_model_py = {}
            
                # Itérer sur les propositions d'intérêt définies manuellement
                for prop_object in propositions_for_interpretation:
                    atom_name = str(prop_object.getName()) # Convertir en chaîne Python
                    # Un PossibleWorld contient les propositions qui sont vraies.
                    is_true_in_model = possible_world.contains(prop_object)
                    current_model_py[atom_name] = bool(is_true_in_model)
            
                # Trier le dictionnaire par nom de proposition pour un affichage cohérent
                sorted_model_items = sorted(current_model_py.items())
                model_representation_list = [f"'{key}': {value}" for key, value in sorted_model_items]
                model_representation = ", ".join(model_representation_list)
                print(f"Modèle {actual_model_index} (Python dict): {{{model_representation}}}")
                # Affichage brut si souhaité (InterpretationSet a aussi une méthode toString())
                # print(f"Modèle {actual_model_index} (Java toString()): {interpretation_set.toString()}")
            
            # model_count est déjà défini par java_models_set.size()
            # L'itération ci-dessus sert à l'affichage et à la vérification.
            
            # Vérification du nombre de modèles attendus.
            # La théorie est:
            # a :- b.
            # b.
            # c :- not d.
            # d :- not c.
            # 'a' et 'b' sont toujours vrais.
            # Les règles pour c et d (c XOR d en pratique pour les modèles stables) donnent deux scénarios:
            # 1. c=True, d=False
            # 2. c=False, d=True
            # Donc, les modèles sont {a,b,c} et {a,b,d}. (Ceci est pour les modèles stables)
            # En logique propositionnelle classique, c :- not d (d V c) et d :- not c (c V d)
            # combiné avec a et b vrais, donne 3 modèles:
            # {a:T,b:T, c:T,d:F}, {a:T,b:T, c:F,d:T}, {a:T,b:T, c:T,d:T}
            expected_models = 3 # Ajusté pour la logique propositionnelle classique
            # model_count est déjà calculé à partir de java_models_set.size()
            if model_count == expected_models:
                 print(f"Test de listage des modèles (logique PL classique) RÉUSSI. {model_count} modèles trouvés comme attendu.")
            else:
                # L'affichage détaillé des modèles ci-dessus aide au débogage si cette assertion échoue.
                print(f"ATTENTION: Le nombre de modèles attendu ({expected_models}) pour la logique PL classique ne correspond pas au nombre trouvé ({model_count}).")
                raise AssertionError(f"ÉCHEC : Nombre de modèles incorrect pour la logique PL classique. Attendu : {expected_models}, Trouvé : {model_count}")


    except Exception as e:
        print(f"Test de listage des modèles ÉCHOUÉ : {e}")
        import traceback
        traceback.print_exc()
        raise

    # finally: # Commenté pour permettre à pytest de gérer la JVM via conftest
        # if jpype.isJVMStarted():
        #     jpype.shutdownJVM()
        #     print("JVM arrêtée.")
        pass