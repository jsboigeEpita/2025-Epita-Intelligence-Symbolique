# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_belief_set.py
"""
Tests unitaires pour les classes BeliefSet.
"""

import unittest
from unittest.mock import patch

from argumentation_analysis.agents.core.logic.belief_set import (
    BeliefSet,
    PropositionalBeliefSet,
    FirstOrderBeliefSet,
    ModalBeliefSet,
)


class MockBeliefSet(BeliefSet):
    """Classe concrète pour tester la classe abstraite BeliefSet."""

    @property
    def logic_type(self):
        """Implémentation de la méthode abstraite."""
        return "mock"


class TestBeliefSet(unittest.TestCase):
    """Tests pour la classe abstraite BeliefSet."""

    def test_initialization(self):
        """Test de l'initialisation d'un ensemble de croyances."""
        belief_set = MockBeliefSet("a => b")
        self.assertEqual(belief_set.content, "a => b")

    def test_to_dict(self):
        """Test de la conversion en dictionnaire."""
        belief_set = MockBeliefSet("a => b")
        result = belief_set.to_dict()

        self.assertEqual(result["logic_type"], "mock")
        self.assertEqual(result["content"], "a => b")

    def test_from_dict_propositional(self):
        """Test de la création à partir d'un dictionnaire pour la logique propositionnelle."""
        data = {"logic_type": "propositional", "content": "a => b"}

        belief_set = BeliefSet.from_dict(data)

        self.assertIsInstance(belief_set, PropositionalBeliefSet)
        self.assertEqual(belief_set.content, "a => b")
        self.assertEqual(belief_set.logic_type, "propositional")

    def test_from_dict_first_order(self):
        """Test de la création à partir d'un dictionnaire pour la logique du premier ordre."""
        data = {"logic_type": "first_order", "content": "forall X: (P(X) => Q(X))"}

        belief_set = BeliefSet.from_dict(data)

        self.assertIsInstance(belief_set, FirstOrderBeliefSet)
        self.assertEqual(belief_set.content, "forall X: (P(X) => Q(X))")
        self.assertEqual(belief_set.logic_type, "first_order")

    def test_from_dict_modal(self):
        """Test de la création à partir d'un dictionnaire pour la logique modale."""
        data = {"logic_type": "modal", "content": "[]p => <>q"}

        belief_set = BeliefSet.from_dict(data)

        self.assertIsInstance(belief_set, ModalBeliefSet)
        self.assertEqual(belief_set.content, "[]p => <>q")
        self.assertEqual(belief_set.logic_type, "modal")

    def test_from_dict_unsupported(self):
        """Test de la création à partir d'un dictionnaire pour un type non supporté."""
        data = {"logic_type": "unsupported", "content": "content"}

        belief_set = BeliefSet.from_dict(data)

        self.assertIsNone(belief_set)

    def test_from_dict_missing_fields(self):
        """Test de la création à partir d'un dictionnaire incomplet."""
        data = {"logic_type": "propositional"}

        belief_set = BeliefSet.from_dict(data)

        self.assertIsInstance(belief_set, PropositionalBeliefSet)
        self.assertEqual(belief_set.content, "")


class TestPropositionalBeliefSet(unittest.TestCase):
    """Tests pour la classe PropositionalBeliefSet."""

    def test_logic_type(self):
        """Test de la propriété logic_type."""
        belief_set = PropositionalBeliefSet("a => b")
        self.assertEqual(belief_set.logic_type, "propositional")


class TestFirstOrderBeliefSet(unittest.TestCase):
    """Tests pour la classe FirstOrderBeliefSet."""

    def test_logic_type(self):
        """Test de la propriété logic_type."""
        belief_set = FirstOrderBeliefSet("forall X: (P(X) => Q(X))")
        self.assertEqual(belief_set.logic_type, "first_order")


class TestModalBeliefSet(unittest.TestCase):
    """Tests pour la classe ModalBeliefSet."""

    def test_logic_type(self):
        """Test de la propriété logic_type."""
        belief_set = ModalBeliefSet("[]p => <>q")
        self.assertEqual(belief_set.logic_type, "modal")


if __name__ == "__main__":
    unittest.main()
