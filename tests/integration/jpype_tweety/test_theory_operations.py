import pytest
import jpype
import os

# Importations spécifiques depuis Tweety (via JPype) seront faites dans les méthodes de test
# en utilisant la fixture `belief_revision_classes`

@pytest.mark.real_jpype
class TestTheoryOperations:
    """
    Tests d'intégration pour les opérations sur les théories logiques (union, intersection, etc.).
    """

    def test_belief_set_union(self, belief_revision_classes, integration_jvm):
        """
        Scénario: Tester l'union de deux bases de croyances.
        Données de test: Deux `PlBeliefSet` distinctes.
        Logique de test:
            1. Créer deux `PlBeliefSet` avec des formules différentes.
            2. Effectuer l'union des deux bases.
            3. Assertion: La base résultante devrait contenir toutes les formules uniques des deux bases originales.
        """
        PlBeliefSet = belief_revision_classes["PlBeliefSet"]
        PlParser = belief_revision_classes["PlParser"]
        
        parser = PlParser()

        # Créer la première base de croyances
        kb1 = PlBeliefSet()
        formula_p = parser.parseFormula("p")
        formula_q = parser.parseFormula("q")
        kb1.add(formula_p)
        kb1.add(formula_q)
        
        # Créer la deuxième base de croyances
        kb2 = PlBeliefSet()
        formula_r = parser.parseFormula("r")
        formula_s = parser.parseFormula("s")
        # Ajout d'une formule commune pour tester l'unicité
        kb2.add(formula_q)
        kb2.add(formula_r)
        kb2.add(formula_s)

        # Effectuer l'union
        # La méthode union dans Tweety PlBeliefSet est `unionWith(BeliefSet other)` et modifie l'objet appelant.
        # Ou `union(BeliefSet one, BeliefSet other)` qui est statique et retourne un nouveau BeliefSet.
        # Pour être sûr, je vais créer une copie et utiliser unionWith, ou utiliser la méthode statique si disponible.
        # PlBeliefSet a une méthode `union(PlBeliefSet other)` qui retourne un nouveau PlBeliefSet.
        
        # Alternative: utiliser la méthode statique si elle existe, ou la méthode d'instance.
        # PlBeliefSet.union(kb1, kb2) n'est pas une méthode statique standard.
        # La méthode d'instance `union(BeliefSet other)` retourne un nouveau BeliefSet.
        
        # Utiliser addAll qui modifie kb1 en place (hérité de Collection)
        kb1.addAll(kb2)
        union_kb = kb1 # union_kb est maintenant une référence à kb1 modifié

        # Assertions
        assert union_kb.size() == 4, "La taille de l'union devrait être 4 (p, q, r, s)"
        
        # Vérifier la présence des formules
        # Pour convertir les formules Java en chaînes Python pour comparaison facile:
        # Il faut s'assurer que la méthode `contains` fonctionne comme attendu avec les objets Formula.
        # Ou convertir les formules de union_kb en un ensemble de chaînes.
        
        union_formulas_str = set()
        iterator = union_kb.iterator()
        while iterator.hasNext():
            union_formulas_str.add(str(iterator.next()))

        expected_formulas_str = {"p", "q", "r", "s"}
        
        assert union_formulas_str == expected_formulas_str, \
            f"Les formules dans l'union ne correspondent pas. Attendu: {expected_formulas_str}, Obtenu: {union_formulas_str}"

        # kb1 a été modifié par unionWith. kb2 ne devrait pas avoir changé.
        assert kb2.size() == 3, "kb2 ne devrait pas être modifiée par kb1.unionWith(kb2)"

    def test_belief_set_intersection(self, belief_revision_classes, integration_jvm):
        """
        Scénario: Tester l'intersection de deux bases de croyances.
        Données de test: Deux `PlBeliefSet` avec des formules communes et distinctes.
        Logique de test:
            1. Créer deux `PlBeliefSet`.
            2. Effectuer l'intersection des deux bases.
            3. Assertion: La base résultante devrait contenir uniquement les formules communes aux deux bases.
        """
        PlBeliefSet = belief_revision_classes["PlBeliefSet"]
        PlParser = belief_revision_classes["PlParser"]
        
        parser = PlParser()

        kb1 = PlBeliefSet()
        formula_p = parser.parseFormula("p")
        formula_q = parser.parseFormula("q")
        formula_common = parser.parseFormula("common")
        kb1.add(formula_p)
        kb1.add(formula_q)
        kb1.add(formula_common)
        
        kb2 = PlBeliefSet()
        formula_r = parser.parseFormula("r")
        formula_s = parser.parseFormula("s")
        kb2.add(formula_r)
        kb2.add(formula_s)
        kb2.add(formula_common) # Formule commune

        # La méthode d'instance `intersection(BeliefSet other)` retourne un nouveau BeliefSet.
        intersection_kb = kb1.intersection(kb2)

        assert intersection_kb.size() == 1, "La taille de l'intersection devrait être 1"
        
        intersection_formulas_str = set()
        iterator = intersection_kb.iterator()
        while iterator.hasNext():
            intersection_formulas_str.add(str(iterator.next()))
            
        expected_formulas_str = {"common"}
        assert intersection_formulas_str == expected_formulas_str, \
            f"Les formules dans l'intersection ne correspondent pas. Attendu: {expected_formulas_str}, Obtenu: {intersection_formulas_str}"
        
        assert kb1.contains(formula_common)
        assert kb2.contains(formula_common)
        assert intersection_kb.contains(formula_common)


    def test_belief_set_difference(self, belief_revision_classes, integration_jvm):
        """
        Scénario: Tester la différence entre deux bases de croyances.
        Données de test: Deux `PlBeliefSet`.
        Logique de test:
            1. Créer deux `PlBeliefSet`.
            2. Effectuer la différence (A - B).
            3. Assertion: La base résultante devrait contenir les formules de A qui ne sont pas dans B.
        """
        PlBeliefSet = belief_revision_classes["PlBeliefSet"]
        PlParser = belief_revision_classes["PlParser"]
        
        parser = PlParser()

        kb_a = PlBeliefSet()
        formula_p = parser.parseFormula("p")
        formula_q = parser.parseFormula("q") # Commune
        formula_r = parser.parseFormula("r") # Unique à A
        kb_a.add(formula_p)
        kb_a.add(formula_q)
        kb_a.add(formula_r)
        
        kb_b = PlBeliefSet()
        formula_s = parser.parseFormula("s") # Unique à B
        formula_t = parser.parseFormula("t") # Unique à B
        kb_b.add(formula_q) # Commune
        kb_b.add(formula_s)
        kb_b.add(formula_t)

        # La méthode d'instance `difference(BeliefSet other)` retourne un nouveau BeliefSet (A - B).
        difference_kb = kb_a.difference(kb_b)

        assert difference_kb.size() == 2, "La taille de la différence (A-B) devrait être 2"
        
        difference_formulas_str = set()
        iterator = difference_kb.iterator()
        while iterator.hasNext():
            difference_formulas_str.add(str(iterator.next()))
            
        # Formules de A qui ne sont pas dans B: p, r
        expected_formulas_str = {"p", "r"}
        assert difference_formulas_str == expected_formulas_str, \
            f"Les formules dans la différence (A-B) ne correspondent pas. Attendu: {expected_formulas_str}, Obtenu: {difference_formulas_str}"

    def test_belief_set_subsumption(self, belief_revision_classes, integration_jvm):
        """
        Scénario: Tester si une base de croyances en subsume une autre.
        Données de test: Deux `PlBeliefSet` où l'une est une conséquence logique de l'autre.
        Logique de test:
            1. Créer deux `PlBeliefSet` (ex: KB1 = {p, p=>q}, KB2 = {q}).
            2. Utiliser un reasoner pour vérifier si KB1 subsume KB2.
            3. Assertion: KB1 devrait subsumer KB2.
        """
        PlBeliefSet = belief_revision_classes["PlBeliefSet"]
        PlParser = belief_revision_classes["PlParser"]
        SimplePlReasoner = belief_revision_classes["SimplePlReasoner"] # Ou un autre reasoner approprié

        parser = PlParser()
        reasoner = SimplePlReasoner()

        # KB1 = {p, p=>q}
        kb1 = PlBeliefSet()
        kb1.add(parser.parseFormula("p"))
        kb1.add(parser.parseFormula("p => q"))
        
        # KB2 = {q}
        kb2 = PlBeliefSet()
        kb2.add(parser.parseFormula("q"))

        # KB3 = {p}
        kb3 = PlBeliefSet()
        kb3.add(parser.parseFormula("p"))

        # KB4 = {r}
        kb4 = PlBeliefSet()
        kb4.add(parser.parseFormula("r"))

        # La méthode `isSubsumedBy(BeliefBase B, BeliefBase A)` vérifie si A subsume B (A |= B)
        # Ou `A.subsumes(B)` si une telle méthode existe.
        # Dans Tweety, un `Reasoner` a une méthode `query(BeliefBase kb, Formula formula)`
        # Pour vérifier la subsomption KB1 |= KB2, on vérifie si chaque formule de KB2 est une conséquence de KB1.
        # Tweety `PlBeliefSet` a une méthode `subsumes(PlBeliefSet other)`
        
        assert kb1.subsumes(kb2) == True, "KB1 {p, p=>q} devrait subsumer KB2 {q}"
        assert kb1.subsumes(kb3) == True, "KB1 {p, p=>q} devrait subsumer KB3 {p}"
        assert kb2.subsumes(kb1) == False, "KB2 {q} ne devrait pas subsumer KB1 {p, p=>q}"
        assert kb1.subsumes(kb4) == False, "KB1 {p, p=>q} ne devrait pas subsumer KB4 {r}"

    def test_belief_set_equivalence(self, belief_revision_classes, integration_jvm):
        """
        Scénario: Tester l'équivalence logique entre deux bases de croyances.
        Données de test: Deux `PlBeliefSet` logiquement équivalentes.
        Logique de test:
            1. Créer deux `PlBeliefSet` logiquement équivalentes (ex: {p && q} et {q && p}).
            2. Utiliser un reasoner pour vérifier l'équivalence.
            3. Assertion: Les deux bases devraient être équivalentes.
        """
        PlBeliefSet = belief_revision_classes["PlBeliefSet"]
        PlParser = belief_revision_classes["PlParser"]

        parser = PlParser()

        # KB1 = {p & q}
        kb1 = PlBeliefSet()
        kb1.add(parser.parseFormula("p && q"))
        
        # KB2 = {q & p}
        kb2 = PlBeliefSet()
        kb2.add(parser.parseFormula("q && p"))

        # KB3 = {p, q}
        kb3 = PlBeliefSet()
        kb3.add(parser.parseFormula("p"))
        kb3.add(parser.parseFormula("q"))
        
        # KB4 = {p}
        kb4 = PlBeliefSet()
        kb4.add(parser.parseFormula("p"))

        # `PlBeliefSet` a une méthode `isEquivalent(PlBeliefSet other)`
        assert kb1.isEquivalent(kb2) == True, "{p && q} devrait être équivalent à {q && p}"
        assert kb1.isEquivalent(kb3) == True, "{p && q} devrait être équivalent à {p, q}"
        assert kb2.isEquivalent(kb3) == True, "{q && p} devrait être équivalent à {p, q}"
        assert kb1.isEquivalent(kb4) == False, "{p && q} ne devrait pas être équivalent à {p}"


    def test_theory_serialization_deserialization(self, belief_revision_classes, integration_jvm, tmp_path):
        """
        Scénario: Tester la sérialisation et désérialisation d'une théorie logique.
        Données de test: Une `PlBeliefSet`.
        Logique de test:
            1. Créer une `PlBeliefSet`.
            2. Sérialiser la base en chaîne de caractères ou fichier.
            3. Désérialiser la chaîne/fichier en une nouvelle `PlBeliefSet`.
            4. Assertion: La base désérialisée devrait être équivalente à l'originale.
        """
        PlBeliefSet = belief_revision_classes["PlBeliefSet"]
        PlParser = belief_revision_classes["PlParser"]
        # Pour la sérialisation/désérialisation, Tweety utilise souvent des classes IO spécifiques
        # ou des méthodes sur les objets eux-mêmes.
        # `PlBeliefSet.toString()` donne une représentation, mais pas forcément pour la re-création.
        # `PlParser` a `parseBeliefBase(Reader reader)` ou `parseBeliefBaseFromFile(String filename)`
        # Pour la sérialisation, il faut trouver une méthode comme `beliefSet.writeToFile(String filename)`
        # ou un `PlWriter`.
        # `org.tweetyproject.logics.pl.io.PlBeliefSetWriter` pourrait exister.
        # Ou `PlBeliefSet.prettyPrint()`
        
        # Tentons avec les méthodes de PlParser et une écriture manuelle au format attendu par le parser.
        # Le format standard est souvent une formule par ligne.

        parser = PlParser()
        
        original_kb = PlBeliefSet()
        original_kb.add(parser.parseFormula("a => b"))
        original_kb.add(parser.parseFormula("b && c"))
        original_kb.add(parser.parseFormula("!d || e"))

        # Sérialisation: écrire les formules dans un fichier, une par ligne.
        temp_file = tmp_path / "theory.lp"
        
        # Utiliser la méthode `writeFile` de `PlBeliefSet` si elle existe et est appropriée.
        # D'après la documentation de Tweety (ou exploration), `PlBeliefSet` a `writeFile(String filename)`.
        original_kb.writeFile(str(temp_file))

        # Désérialisation
        # `PlParser` a `parseBeliefBaseFromFile(String filename)`
        deserialized_kb = parser.parseBeliefBaseFromFile(str(temp_file))

        # Assertion
        assert deserialized_kb is not None, "La désérialisation ne devrait pas retourner None"
        assert original_kb.isEquivalent(deserialized_kb), \
            "La base désérialisée devrait être équivalente à l'originale."
        assert original_kb.size() == deserialized_kb.size(), \
            "Les tailles des bases devraient être égales après sérialisation/désérialisation."

        # Vérification supplémentaire du contenu
        original_formulas_str = set()
        iterator_orig = original_kb.iterator()
        while iterator_orig.hasNext():
            original_formulas_str.add(str(iterator_orig.next()))

        deserialized_formulas_str = set()
        iterator_deser = deserialized_kb.iterator()
        while iterator_deser.hasNext():
            deserialized_formulas_str.add(str(iterator_deser.next()))
        
        assert original_formulas_str == deserialized_formulas_str, \
            "Les ensembles de formules (chaînes) devraient être égaux."