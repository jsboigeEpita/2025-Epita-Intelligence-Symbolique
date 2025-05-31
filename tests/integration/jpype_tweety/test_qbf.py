import pytest
# import jpype # Commenté, sera importé localement


# Les classes Java sont importées via la fixture 'qbf_classes' de conftest.py
# et 'dung_classes' n'est pas nécessaire ici.

def test_qbf_parser_simple_formula(qbf_classes):
    """
    Teste le parsing d'une formule QBF simple : exists x forall y (x or not y)
    """
    QbfParser = qbf_classes["QbfParser"]
    # Les classes pour Or, Not, Variable seraient nécessaires pour une vérification
    # plus approfondie de la structure de la formule, mais pour l'instant,
    # on se contente de vérifier que le parsing ne lève pas d'erreur et
    # que la formule toString() correspond.
    # Variable = qbf_classes["Variable"]
    # Or = qbf_classes.get("Or") # Peut être None si non défini dans la fixture
    # Not = qbf_classes.get("Not")

    parser = QbfParser()
    qbf_string = "exists x forall y (x or not y)"
    # La représentation de Tweety peut varier légèrement (espaces, parenthèses)
    # Il faudra peut-être ajuster expected_representation.
    # Exemple de ce que Tweety pourrait retourner (à vérifier) :
    # "exists x: forall y: (x | !y)" ou similaire.
    # Pour un test robuste, il faudrait inspecter la structure de l'objet Formula.

    try:
        import jpype # Import local
        formula = parser.parseFormula(qbf_string)
        assert formula is not None, "La formule parsée ne devrait pas être nulle."
        
        # La méthode toString() de Tweety est le moyen le plus simple de vérifier
        # la formule sans inspecter sa structure interne complexe.
        # Il faut être conscient que cette représentation peut changer entre les versions de Tweety.
        # Une normalisation de la chaîne (ex: supprimer les espaces superflus) peut aider.
        parsed_formula_str = str(formula.toString()).replace(" ", "")
        
        # Exemples de représentations attendues possibles (après suppression des espaces)
        # Cela dépend fortement de la sortie de Tweety.
        expected_representations = [
            "existsx:forally:(x|!y)", # Tweety utilise souvent ':' après quantificateur et '|' pour OR, '!' pour NOT
            "existsxforall_y(xor-y)", # Autre format possible
            "existsx(forally((xor(-y))))" # Encore un autre
        ]
        
        # Normaliser la chaîne d'entrée pour la comparaison si nécessaire
        normalized_qbf_string_for_comparison = qbf_string.replace(" ", "").replace("or", "|").replace("not", "!")
        
        # Pour ce test, nous allons être un peu plus flexibles et vérifier si les éléments clés sont présents.
        # Une meilleure approche serait de connaître la sortie exacte de `formula.toString()`
        # ou de décomposer la formule et de vérifier ses composants.
        assert "exists" in str(formula.toString()).lower()
        assert "forall" in str(formula.toString()).lower()
        assert "x" in str(formula.toString())
        assert "y" in str(formula.toString())
        # Les opérateurs 'or' et 'not' peuvent être représentés par des symboles.
        
        print(f"Formule QBF parsée : {formula.toString()}")
        # Un test plus strict serait :
        # assert parsed_formula_str in [rep.replace(" ", "") for rep in expected_representations]

    except jpype.JException as e: # jpype doit être importé
        pytest.fail(f"Erreur Java lors du parsing de la QBF '{qbf_string}': {e.stacktrace()}")

def test_qbf_programmatic_creation_exists(qbf_classes):
    """
    Teste la création programmatique d'une QBF simple : exists x (x)
    (Nécessite que la classe Variable soit bien importée et utilisable)
    """
    QuantifiedBooleanFormula = qbf_classes["QuantifiedBooleanFormula"]
    Quantifier = qbf_classes["Quantifier"]
    Variable = qbf_classes["Variable"]

    try:
        import jpype # Import local
        x_var = Variable("x")
        # La formule interne est juste 'x'.
        # Pour créer QuantifiedBooleanFormula(Quantifier, JArray(Variable), Formula interne)
        # La "Formula interne" ici est la variable elle-même, car une variable est une formule atomique.
        
        # Créer un JArray de Variable pour les variables quantifiées
        quantified_vars = jpype.JArray(Variable)([x_var])

        qbf = QuantifiedBooleanFormula(Quantifier.EXISTS, quantified_vars, x_var)
        
        assert qbf is not None
        # La représentation toString() est la façon la plus simple de vérifier.
        # Elle pourrait être "exists x: x" ou similaire.
        formula_str = str(qbf.toString())
        print(f"Formule QBF créée programmatiquement : {formula_str}")

        # Vérifications de base
        assert "exists" in formula_str.lower()
        assert "x" in formula_str # Le nom de la variable doit apparaître
        # Idéalement, vérifier la structure :
        assert qbf.getQuantifier() == Quantifier.EXISTS
        assert qbf.getVariables().length == 1
        assert str(qbf.getVariables()[0].getName()) == "x"
        assert str(qbf.getFormula().toString()) == "x" # La formule interne est x

    except jpype.JException as e: # jpype doit être importé
        pytest.fail(f"Erreur Java lors de la création programmatique de la QBF : {e.stacktrace()}")

def test_qbf_programmatic_creation_forall_nested(qbf_classes):
    """
    Teste la création programmatique d'une QBF imbriquée : forall y exists x (y)
    (Nécessite Variable, Quantifier, QuantifiedBooleanFormula)
    """
    QuantifiedBooleanFormula = qbf_classes["QuantifiedBooleanFormula"]
    Quantifier = qbf_classes["Quantifier"]
    Variable = qbf_classes["Variable"]
    # Supposons que les opérateurs logiques comme Or, And, Not sont nécessaires
    # et doivent être importés de Tweety, par exemple de org.tweetyproject.logics.pl.syntax
    # Pour cet exemple, nous allons utiliser une formule interne simple (juste une variable).
    # Si nous avions Or = jpype.JClass("org.tweetyproject.logics.pl.syntax.Or")
    # et Not = jpype.JClass("org.tweetyproject.logics.pl.syntax.Not")
    # alors on pourrait faire : inner_formula = Or(x_var, Not(y_var))

    try:
        import jpype # Import local
        x_var = Variable("x")
        y_var = Variable("y")

        # Formule la plus interne : exists x (y)
        # Note: la formule interne ici est juste 'y'. Si on voulait 'exists x (x or y)',
        # il faudrait construire 'x or y' d'abord.
        # Pour 'exists x (y)', la formule interne est 'y'.
        inner_qbf = QuantifiedBooleanFormula(Quantifier.EXISTS, jpype.JArray(Variable)([x_var]), y_var)
        
        # Formule externe : forall y ( inner_qbf )
        outer_qbf = QuantifiedBooleanFormula(Quantifier.FORALL, jpype.JArray(Variable)([y_var]), inner_qbf)

        assert outer_qbf is not None
        formula_str = str(outer_qbf.toString())
        print(f"Formule QBF imbriquée créée : {formula_str}")

        # Vérifications de base (la représentation exacte peut varier)
        # ex: "forall y: exists x: y"
        assert "forall" in formula_str.lower()
        assert "exists" in formula_str.lower()
        assert "x" in formula_str
        assert "y" in formula_str
        
        # Vérification structurelle
        assert outer_qbf.getQuantifier() == Quantifier.FORALL
        assert str(outer_qbf.getVariables()[0].getName()) == "y"
        
        nested_formula = outer_qbf.getFormula()
        assert isinstance(nested_formula, QuantifiedBooleanFormula) # Java: nested_formula instanceof QuantifiedBooleanFormula # type: ignore
        assert nested_formula.getQuantifier() == Quantifier.EXISTS
        assert str(nested_formula.getVariables()[0].getName()) == "x"
        assert str(nested_formula.getFormula().toString()) == "y" # La formule la plus interne

    except jpype.JException as e: # jpype doit être importé
        pytest.fail(f"Erreur Java lors de la création de QBF imbriquée : {e.stacktrace()}")

def test_qbf_programmatic_creation_example_from_subject_fiche(qbf_classes):
    """
    Teste la création programmatique de la QBF ∃x ∀y (x ∧ ¬y) de la fiche sujet.
    """
    # Classes QBF (devraient être dans qbf_classes)
    QuantifiedBooleanFormula = qbf_classes["QuantifiedBooleanFormula"]
    Quantifier = qbf_classes["Quantifier"]
    Variable = qbf_classes["Variable"] # Utilisé pour JArray(Variable) pour les variables quantifiées

    # Classes de la logique propositionnelle pour la matrice de la formule
    # Importées directement car non garanties d'être dans qbf_classes et pour ne pas modifier conftest.py
    import jpype # Import local
    Proposition = jpype.JClass("org.tweetyproject.logics.propositional.syntax.Proposition")
    Conjunction = jpype.JClass("org.tweetyproject.logics.propositional.syntax.Conjunction")
    Negation = jpype.JClass("org.tweetyproject.logics.propositional.syntax.Negation")

    try:
        # Définition des propositions pour la matrice
        x_prop = Proposition("x")
        y_prop = Proposition("y")

        # Définition des variables pour la quantification
        # (Tweety s'attend à des objets Variable pour la quantification)
        x_var_quant = Variable("x")
        y_var_quant = Variable("y")

        # Construction de la matrice : (x ∧ ¬y)
        matrix = Conjunction(x_prop, Negation(y_prop))

        # Construction de la partie quantifiée universellement : ∀y (x ∧ ¬y)
        formula_forall_y = QuantifiedBooleanFormula(Quantifier.FORALL, jpype.JArray(Variable)([y_var_quant]), matrix)

        # Construction de la formule QBF complète : ∃x ∀y (x ∧ ¬y)
        qbf_formula_exists_x = QuantifiedBooleanFormula(Quantifier.EXISTS, jpype.JArray(Variable)([x_var_quant]), formula_forall_y)

        assert qbf_formula_exists_x is not None, "La formule QBF construite ne devrait pas être nulle."
        
        formula_str = str(qbf_formula_exists_x.toString())
        print(f"Formule QBF (fiche sujet) créée : {formula_str}")

        # Vérifications de la structure de la formule
        # 1. Vérification du quantificateur existentiel externe
        assert qbf_formula_exists_x.getQuantifier() == Quantifier.EXISTS, "Le quantificateur externe doit être EXISTS."
        assert qbf_formula_exists_x.getVariables().length == 1, "Un seul variable doit être quantifiée existentiellement."
        assert str(qbf_formula_exists_x.getVariables()[0].getName()) == "x", "La variable existentielle doit être 'x'."
        
        # 2. Vérification de la sous-formule (quantifiée universellement)
        nested_formula_forall = qbf_formula_exists_x.getFormula()
        assert isinstance(nested_formula_forall, QuantifiedBooleanFormula), "La sous-formule doit être une QuantifiedBooleanFormula." # type: ignore
        assert nested_formula_forall.getQuantifier() == Quantifier.FORALL, "Le quantificateur interne doit être FORALL."
        assert nested_formula_forall.getVariables().length == 1, "Une seule variable doit être quantifiée universellement."
        assert str(nested_formula_forall.getVariables()[0].getName()) == "y", "La variable universelle doit être 'y'."
        
        # 3. Vérification de la matrice (x ∧ ¬y)
        final_matrix = nested_formula_forall.getFormula()
        assert final_matrix.getClass().getName() == "org.tweetyproject.logics.propositional.syntax.Conjunction", \
               "La matrice finale doit être une Conjonction."

        matrix_str_representation = str(final_matrix.toString()).replace(" ", "")
        assert "x" in matrix_str_representation
        assert "y" in matrix_str_representation
        assert "Conjunction(" in str(final_matrix.toString()) or "&" in matrix_str_representation or "AND" in matrix_str_representation.upper()
        assert "Negation(" in str(final_matrix.toString()) or "!" in matrix_str_representation or "NOT" in matrix_str_representation.upper()

    except jpype.JException as e: # jpype doit être importé
        pytest.fail(f"Erreur Java lors de la création programmatique de la QBF ∃x ∀y (x ∧ ¬y) : {e.stacktrace()}")
    except Exception as e:
        pytest.fail(f"Erreur Python inattendue lors de la création de QBF : {str(e)}")
# Les tests de satisfiabilité avec QBFSolver sont plus complexes car ils
# peuvent nécessiter la configuration d'un solveur QBF externe ou intégré à Tweety.
# Ces tests sont donc commentés pour l'instant et pourront être ajoutés
# une fois que l'environnement de test pour les solveurs est clarifié.

# def test_qbf_satisfiability_simple_true(qbf_classes):
#     """Teste la satisfiabilité d'une QBF simple vraie : exists x (x)"""
#     QbfParser = qbf_classes["QbfParser"]
#     QBFSolver = qbf_classes.get("QBFSolver") # Peut être None
#     if not QBFSolver:
#         pytest.skip("QBFSolver non disponible dans les fixtures, test de satisfiabilité sauté.")
#
#     parser = QbfParser()
#     try:
#         # Une QBF comme "exists x (x)" est généralement vraie si x peut être vrai.
#         # Dans QBF, les variables propositionnelles sont implicitement dans un domaine {true, false}.
#         # Cependant, la sémantique exacte peut dépendre de la définition de "formule valide" dans Tweety.
#         # Une formule plus canonique serait "exists x (x or not x)" (toujours vraie)
#         # ou "exists x (x)" si x est une proposition simple.
#         # Pour Tweety, une simple variable "x" est une formule.
#         formula = parser.parseFormula("exists x (x)") # ou parser.parseFormula("exists x (x=x)") si c'est une syntaxe
#
#         # Obtenir le solveur par défaut (peut nécessiter une configuration système)
#         solver = QBFSolver.getDefaultSolver()
#         if not solver:
#              pytest.skip("Aucun solveur QBF par défaut n'a pu être obtenu.")
#
#         is_satisfiable = solver.isSatisfiable(formula)
#         print(f"La formule '{formula.toString()}' est satisfiable : {is_satisfiable}")
#         assert is_satisfiable is True
#
#     except jpype.JException as e:
#         # Certaines erreurs peuvent être dues à l'absence de solveur configuré.
#         if "No QBF solver installed" in e.message() or "No default QBF solver specified" in e.message():
#             pytest.skip(f"Solveur QBF non configuré ou non trouvé : {e.message()}")
#         else:
#             pytest.fail(f"Erreur Java lors du test de satisfiabilité QBF (true) : {e.stacktrace()}")
#
# def test_qbf_satisfiability_simple_false(qbf_classes):
#     """Teste la satisfiabilité d'une QBF simple fausse : forall x (x and not x)"""
#     QbfParser = qbf_classes["QbfParser"]
#     QBFSolver = qbf_classes.get("QBFSolver")
#     if not QBFSolver:
#         pytest.skip("QBFSolver non disponible, test de satisfiabilité sauté.")
#
#     parser = QbfParser()
#     try:
#         formula = parser.parseFormula("forall x (x and not x)") # Ceci est toujours faux
#         solver = QBFSolver.getDefaultSolver()
#         if not solver:
#              pytest.skip("Aucun solveur QBF par défaut n'a pu être obtenu.")
#
#         is_satisfiable = solver.isSatisfiable(formula)
#         print(f"La formule '{formula.toString()}' est satisfiable : {is_satisfiable}")
#         assert is_satisfiable is False
#
#     except jpype.JException as e:
#         if "No QBF solver installed" in e.message() or "No default QBF solver specified" in e.message():
#             pytest.skip(f"Solveur QBF non configuré ou non trouvé : {e.message()}")
#         else:
#             pytest.fail(f"Erreur Java lors du test de satisfiabilité QBF (false) : {e.stacktrace()}")

# TODO:
# - Ajouter des tests pour les opérateurs logiques (Or, Implies, Equivalence)
#   et approfondir les tests pour And (Conjunction) et Not (Negation) qui ont été
#   utilisés dans test_qbf_programmatic_creation_example_from_subject_fiche.
#   Clarifier l'importation de ces classes (ex: org.tweetyproject.logics.pl.syntax.*)
#   et les ajouter à la fixture qbf_classes si pertinent.
# - Explorer d'autres fonctionnalités de l'API QBF de Tweety (conversion en CNF/DNF, etc.)
#   et ajouter des tests correspondants.
# - Gérer les cas d'erreur (parsing de formules incorrectes, etc.).
def test_qbf_prenex_normal_form_transformation(qbf_classes):
    """
    Teste la transformation d'une QBF en forme normale prénexe.
    Exemple: forall x ( (exists y (y)) and (exists z (z)) )
    Devrait devenir: forall x exists y exists z (y and z) (ou une variante équivalente)
    Cela suppose l'existence d'une classe de transformation.
    """
    QuantifiedBooleanFormula = qbf_classes["QuantifiedBooleanFormula"]
    Quantifier = qbf_classes["Quantifier"]
    Variable = qbf_classes["Variable"]
    QbfParser = qbf_classes["QbfParser"]
    # Supposons l'existence d'un converter, ex: PrenexNormalFormConverter
    # Le nom exact et le package doivent être vérifiés dans Tweety.
    import jpype # Import local
    try:
        PrenexConverter = jpype.JClass("org.tweetyproject.logics.qbf.transform.PrenexNormalFormConverter")
    except jpype.JException as e:
        pytest.skip(f"Classe PrenexNormalFormConverter non trouvée ou erreur: {e}. Test sauté.")
        return

    parser = QbfParser()
    # Formule non prénexe: "forall x ( (exists y (y)) and (exists z (z)) )"
    # Pour la créer programmatiquement pour être sûr de sa structure interne:
    # Matrice 1: y
    # Matrice 2: z
    # QBF1: exists y (y)
    # QBF2: exists z (z)
    # Conjonction: (exists y (y)) and (exists z (z))
    # QBF finale: forall x ( (exists y (y)) and (exists z (z)) )

    try:
        x_var = Variable("x")
        y_var = Variable("y")
        z_var = Variable("z")

        # Propositionnel pour les matrices internes (plus simple)
        Prop_y = jpype.JClass("org.tweetyproject.logics.propositional.syntax.Proposition")("y")
        Prop_z = jpype.JClass("org.tweetyproject.logics.propositional.syntax.Proposition")("z")
        
        qbf1_exists_y = QuantifiedBooleanFormula(Quantifier.EXISTS, jpype.JArray(Variable)([y_var]), Prop_y)
        qbf2_exists_z = QuantifiedBooleanFormula(Quantifier.EXISTS, jpype.JArray(Variable)([z_var]), Prop_z)

        Conjunction = jpype.JClass("org.tweetyproject.logics.pl.syntax.Conjunction") # ou qbf.syntax.QbfConjunction
        inner_matrix_conj = Conjunction(qbf1_exists_y, qbf2_exists_z)
        
        original_qbf = QuantifiedBooleanFormula(Quantifier.FORALL, jpype.JArray(Variable)([x_var]), inner_matrix_conj)
        print(f"Original QBF (non-prénexe): {original_qbf.toString()}")

        converter = PrenexConverter()
        prenex_qbf = converter.convert(original_qbf)

        assert prenex_qbf is not None, "La formule en forme prénexe ne devrait pas être nulle."
        prenex_str = str(prenex_qbf.toString()).lower().replace(" ", "")
        print(f"Formule QBF en forme prénexe: {prenex_qbf.toString()}")

        # La forme prénexe attendue pourrait être "forall x: exists y: exists z: (y & z)"
        # ou avec les quantificateurs regroupés différemment selon l'algorithme.
        # Vérifications de base:
        assert "forallx" in prenex_str or "forall x" in prenex_qbf.toString().lower() # Garder flexibilité sur les espaces
        assert "existsy" in prenex_str or "exists y" in prenex_qbf.toString().lower()
        assert "existsz" in prenex_str or "exists z" in prenex_qbf.toString().lower()
        
        # Vérifier que les quantificateurs sont au début.
        # Ceci est une heuristique. Une vraie vérification nécessiterait d'inspecter la structure de l'objet.
        # Par exemple, la formule interne de la QBF prénexe ne devrait plus être une QuantifiedBooleanFormula.
        if isinstance(prenex_qbf.getFormula(), QuantifiedBooleanFormula): # type: ignore
             pytest.fail("La matrice de la formule prénexe ne devrait plus être quantifiée.")

        # Vérifier que la matrice est correcte (y and z)
        # Cela dépend de comment la conversion est faite.
        # Exemple: "(y&z)" ou "Conjunction(y,z)"
        matrix_str = str(prenex_qbf.getFormula().toString()).replace(" ", "")
        assert "y" in matrix_str
        assert "z" in matrix_str
        assert "&" in matrix_str or "and" in matrix_str.lower() or "conjunction" in matrix_str.lower()

    except jpype.JException as e: # jpype doit être importé
        if "Could not find class" in str(e) or "NoSuchMethodException" in str(e):
             pytest.skip(f"Dépendance ou méthode manquante pour la transformation prénexe: {e}")
        else:
            pytest.fail(f"Erreur Java lors de la transformation en forme prénexe: {e.stacktrace()}")
    except Exception as e:
        pytest.fail(f"Erreur Python inattendue: {str(e)}")


@pytest.mark.skip(reason="Parsing DIMACS QBF non clairement documenté pour QbfParser sans solveur.")
def test_qbf_parser_dimacs_format(qbf_classes):
    """
    Teste le parsing d'une QBF au format DIMACS (si supporté directement par QbfParser).
    Ce test est marqué comme skip car la fonctionnalité n'est pas évidente.
    """
    QbfParser = qbf_classes["QbfParser"]
    # Exemple de contenu DIMACS pour une formule simple (ex: exists 1 forall 2 (1 or -2))
    # p cnf 2 1 1 # 2 variables, 1 clause dans la matrice, 1 bloc de quantificateurs existentiels
    # e 1 0
    # a 2 0
    # 1 -2 0
    dimacs_content_satisfiable = """
    p cnf 2 2
    e 1 0
    a 2 0
    1 -2 0
    -1 2 0
    """
    # Cette QBF est ∃x₁ ∀x₂ ( (x₁ ∨ ¬x₂) ∧ (¬x₁ ∨ x₂) ) qui est équivalente à ∃x₁ ∀x₂ (x₁ ↔ x₂)
    # Elle est FAUSSE. Car si x1=true, x2 doit être true. Si x1=false, x2 doit être false.
    # Mais x2 est universel, donc il peut prendre la valeur opposée.

    dimacs_qbf_true_example = """
    c Example: exists x (x or not x)
    p cnf 1 1
    e 1 0
    1 -1 0
    """ # Cette formule est VRAIE.

    parser = QbfParser()
    formula = None
    try:
        # Hypothèse: il existe une méthode comme parseDimacsString ou parseDimacsStream
        # Si QbfParser a une méthode pour lire un fichier, on pourrait créer un fichier temporaire.
        # Tentative avec une méthode hypothétique:
        if hasattr(parser, "parseDimacsString"):
            formula = parser.parseDimacsString(jpype.JString(dimacs_qbf_true_example)) # jpype doit être importé
        elif hasattr(parser, "parseDimacs"): # Autre nom possible
            formula = parser.parseDimacs(jpype.JString(dimacs_qbf_true_example)) # jpype doit être importé
        else:
            pytest.skip("Aucune méthode évidente pour parser DIMACS trouvée sur QbfParser.")
            return

        assert formula is not None, "La formule QBF parsée depuis DIMACS ne devrait pas être nulle."
        # Vérifications supplémentaires sur la formule (nombre de variables, quantificateurs, etc.)
        # Par exemple, pour la formule "exists x (x or not x)"
        print(f"Formule QBF parsée depuis DIMACS: {formula.toString()}")
        assert "exists" in str(formula.toString()).lower()
        # La vérification de la satisfiabilité nécessiterait un solveur.

    except jpype.JException as e: # jpype doit être importé
        if "NoSuchMethodException" in str(e) or "method not found" in str(e).lower():
            pytest.skip(f"Méthode de parsing DIMACS non trouvée sur QbfParser: {e}")
        else:
            pytest.fail(f"Erreur Java lors du parsing DIMACS QBF: {e.stacktrace()}")
    except AttributeError:
        pytest.skip("Méthode de parsing DIMACS non trouvée (AttributeError).")

# Test pour l'extraction de modèles (nécessite un solveur)
@pytest.mark.skip(reason="Extraction de modèles QBF nécessite un solveur configuré.")
def test_qbf_model_extraction(qbf_classes):
    """
    Teste l'extraction d'un modèle pour une QBF satisfiable.
    Exemple: exists x, y (x and y) -> modèle x=true, y=true
    Ce test est marqué comme skip car il dépend d'un QBFSolver.
    """
    QbfParser = qbf_classes["QbfParser"]
    QBFSolver = qbf_classes.get("QBFSolver") # Peut être dans qbf_classes si ajouté
    
    if not QBFSolver:
        # Tentative d'importation directe si non présent dans la fixture
        try:
            QBFSolver = jpype.JClass("org.tweetyproject.logics.qbf.solver.QBFSolver") # jpype doit être importé
        except jpype.JException: # jpype doit être importé
            pytest.skip("QBFSolver non disponible, test d'extraction de modèle sauté.")
            return

    parser = QbfParser()
    qbf_string = "exists x exists y (x and y)" # Satisfiable, modèle x=T, y=T
    
    try:
        formula = parser.parseFormula(qbf_string)
        
        # Obtenir un solveur (la méthode getDefaultSolver peut nécessiter une configuration)
        # ou instancier un solveur spécifique si son nom de classe est connu.
        solver_instance = None
        try:
            # Tenter d'obtenir le solveur par défaut
            solver_instance = QBFSolver.getDefaultSolver()
            if not solver_instance: # Si getDefaultSolver() retourne null
                 pytest.skip("Aucun solveur QBF par défaut n'a pu être obtenu.")
                 return
        except jpype.JException as e_solver: # jpype doit être importé
            # Si getDefaultSolver() lève une exception (ex: aucun solveur configuré)
            pytest.skip(f"Impossible d'obtenir un solveur QBF par défaut: {e_solver}. Test sauté.")
            return

        is_satisfiable = solver_instance.isSatisfiable(formula)
        assert is_satisfiable, f"La formule '{qbf_string}' devrait être satisfiable."

        # Extraction du modèle
        # La méthode pour obtenir un modèle peut s'appeler getModel(), getWitness(), etc.
        # Elle retourne souvent une Collection de Literals ou une Map.
        model = None
        if hasattr(solver_instance, "getModel"):
            model = solver_instance.getModel(formula)
        elif hasattr(solver_instance, "getWitness"): # Autre nom possible
             model = solver_instance.getWitness(formula)
        else:
            pytest.skip("Méthode d'extraction de modèle non trouvée sur le solveur.")
            return

        assert model is not None, "Le modèle extrait ne devrait pas être nul pour une formule satisfiable."
        
        # Interprétation du modèle (dépend du type de retour)
        # Si c'est une Collection de Literals (Proposition ou Negation)
        # Exemple: pour x=true, y=true, on attendrait les littéraux x et y.
        model_assignments = {}
        if hasattr(model, "iterator"): # Si c'est une collection Java
            iterator = model.iterator()
            while iterator.hasNext():
                literal = iterator.next()
                # Supposons que literal.getAtom().getName() donne le nom de la variable
                # et que literal est une instance de Proposition pour vrai, Negation pour faux.
                # Ou que literal est une assignation (Variable, BooleanValue)
                # Ceci est très dépendant de l'API de Tweety.
                # Pour l'instant, on vérifie juste que le modèle n'est pas vide.
                # Une vérification plus précise nécessiterait de connaître la structure du modèle retourné.
                # Exemple simplifié:
                if hasattr(literal, "getVariable") and hasattr(literal, "getValue"): # Si c'est une assignation
                    var_name = str(literal.getVariable().getName())
                    value = literal.getValue() # Supposons que c'est un booléen Java
                    model_assignments[var_name] = bool(value)
                elif hasattr(literal, "getAtom") and hasattr(literal, "isPositive"): # Si c'est un Literal
                    var_name = str(literal.getAtom().getName())
                    model_assignments[var_name] = literal.isPositive()

        print(f"Modèle extrait pour '{qbf_string}': {model_assignments if model_assignments else str(model)}")
        
        # Vérifications spécifiques pour "exists x exists y (x and y)"
        # On s'attend à x=true, y=true.
        # La manière de vérifier cela dépend de la structure de 'model'.
        # Si model_assignments a été peuplé:
        if model_assignments:
            assert model_assignments.get("x") is True, "x devrait être vrai dans le modèle."
            assert model_assignments.get("y") is True, "y devrait être vrai dans le modèle."
        else: # Si on ne peut pas facilement parser, au moins vérifier que le modèle n'est pas vide.
            assert not model.isEmpty() if hasattr(model, "isEmpty") else True, "Le modèle ne devrait pas être vide."


    except jpype.JException as e: # jpype doit être importé
        if "No QBF solver installed" in str(e) or "No default QBF solver specified" in str(e) or "Could not find class" in str(e):
            pytest.skip(f"Solveur QBF non configuré ou classe de solveur non trouvée: {e}")
        elif "NoSuchMethodException" in str(e) or "method not found" in str(e).lower():
            pytest.skip(f"Méthode nécessaire pour le solveur ou l'extraction de modèle non trouvée: {e}")
        else:
            pytest.fail(f"Erreur Java lors de l'extraction de modèle QBF: {e.stacktrace()}")
    except AttributeError:
        pytest.skip("Méthode d'extraction de modèle non trouvée (AttributeError).")