"""Description Logic (DL) handler — TweetyProject integration.

Provides ontological reasoning with ALC Description Logic:
- TBox (terminological axioms): concept equivalences, subsumptions
- ABox (assertional axioms): concept/role assertions about individuals
- Reasoning: consistency checking, subsumption, instance queries

Uses Tweety's DL module: org.tweetyproject.logics.dl
"""

import jpype
import logging
from typing import Dict, List, Optional, Tuple

from .tweety_initializer import TweetyInitializer

logger = logging.getLogger(__name__)


class DLHandler:
    """Handles Description Logic operations using TweetyProject.

    Supports ALC (Attributive Language with Complement):
    - Atomic concepts, roles, individuals
    - Complement, union, intersection
    - Existential/universal restrictions
    - TBox + ABox reasoning via NaiveDlReasoner
    """

    def __init__(self, initializer_instance: TweetyInitializer):
        if not initializer_instance.is_jvm_ready():
            raise RuntimeError("JVM not ready — cannot initialize DLHandler.")
        self._initializer_instance = initializer_instance
        self._reasoner = None  # Lazy-loaded
        self._load_classes()

    def _load_classes(self):
        """Load all required DL Java classes."""
        try:
            dl_pkg = "org.tweetyproject.logics.dl.syntax"
            self._AtomicConcept = jpype.JClass(f"{dl_pkg}.AtomicConcept")
            self._AtomicRole = jpype.JClass(f"{dl_pkg}.AtomicRole")
            self._Individual = jpype.JClass(f"{dl_pkg}.Individual")
            self._Complement = jpype.JClass(f"{dl_pkg}.Complement")
            self._Union = jpype.JClass(f"{dl_pkg}.Union")
            self._Intersection = jpype.JClass(f"{dl_pkg}.Intersection")
            self._ExistentialRestriction = jpype.JClass(
                f"{dl_pkg}.ExistentialRestriction"
            )
            self._UniversalRestriction = jpype.JClass(f"{dl_pkg}.UniversalRestriction")
            self._EquivalenceAxiom = jpype.JClass(f"{dl_pkg}.EquivalenceAxiom")
            self._ConceptAssertion = jpype.JClass(f"{dl_pkg}.ConceptAssertion")
            self._RoleAssertion = jpype.JClass(f"{dl_pkg}.RoleAssertion")
            self._DlBeliefSet = jpype.JClass(f"{dl_pkg}.DlBeliefSet")
            self._DlSignature = jpype.JClass(f"{dl_pkg}.DlSignature")

            self._DlParser = jpype.JClass("org.tweetyproject.logics.dl.parser.DlParser")
            self._NaiveDlReasoner = jpype.JClass(
                "org.tweetyproject.logics.dl.reasoner.NaiveDlReasoner"
            )
            logger.info("DL classes loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load DL classes: {e}")
            raise RuntimeError(f"DL classes not available in Tweety: {e}") from e

    def _get_reasoner(self):
        """Lazy-load the DL reasoner."""
        if self._reasoner is None:
            self._reasoner = self._NaiveDlReasoner()
            logger.info("NaiveDlReasoner initialized.")
        return self._reasoner

    # ── Concept/Role/Individual builders ─────────────────────────────

    def concept(self, name: str):
        """Create an atomic concept."""
        return self._AtomicConcept(name)

    def role(self, name: str):
        """Create an atomic role."""
        return self._AtomicRole(name)

    def individual(self, name: str):
        """Create an individual."""
        return self._Individual(name)

    def complement(self, concept):
        """Negate a concept (¬C)."""
        return self._Complement(concept)

    def union(self, *concepts):
        """Disjunction of concepts (C ⊔ D)."""
        result = concepts[0]
        for c in concepts[1:]:
            result = self._Union(result, c)
        return result

    def intersection(self, *concepts):
        """Conjunction of concepts (C ⊓ D)."""
        result = concepts[0]
        for c in concepts[1:]:
            result = self._Intersection(result, c)
        return result

    def exists(self, role, concept):
        """Existential restriction (∃R.C)."""
        return self._ExistentialRestriction(role, concept)

    def forall(self, role, concept):
        """Universal restriction (∀R.C)."""
        return self._UniversalRestriction(role, concept)

    # ── KB construction ──────────────────────────────────────────────

    def create_knowledge_base(
        self,
        tbox: Optional[List[Tuple[str, str]]] = None,
        abox_concepts: Optional[List[Tuple[str, str]]] = None,
        abox_roles: Optional[List[Tuple[str, str, str]]] = None,
    ) -> object:
        """Build a DL knowledge base from simplified specification.

        Args:
            tbox: List of (concept_name, equivalent_concept_name) equivalences.
            abox_concepts: List of (individual_name, concept_name) assertions.
            abox_roles: List of (individual1, role_name, individual2) assertions.

        Returns:
            DlBeliefSet Java object.
        """
        kb = self._DlBeliefSet()

        if tbox:
            for lhs_name, rhs_name in tbox:
                lhs = self._AtomicConcept(lhs_name)
                rhs = self._AtomicConcept(rhs_name)
                axiom = self._EquivalenceAxiom(lhs, rhs)
                kb.add(axiom)

        if abox_concepts:
            for ind_name, concept_name in abox_concepts:
                ind = self._Individual(ind_name)
                concept = self._AtomicConcept(concept_name)
                assertion = self._ConceptAssertion(ind, concept)
                kb.add(assertion)

        if abox_roles:
            for ind1_name, role_name, ind2_name in abox_roles:
                ind1 = self._Individual(ind1_name)
                ind2 = self._Individual(ind2_name)
                r = self._AtomicRole(role_name)
                assertion = self._RoleAssertion(ind1, ind2, r)
                kb.add(assertion)

        return kb

    # ── Reasoning ────────────────────────────────────────────────────

    def is_consistent(self, kb) -> Tuple[bool, str]:
        """Check if a DL knowledge base is consistent."""
        reasoner = self._get_reasoner()
        try:
            result = reasoner.query(kb, self._AtomicConcept("⊤"))
            # NaiveDlReasoner.query returns true if kb entails the query
            # An inconsistent KB entails everything
            return True, "Knowledge base is consistent."
        except jpype.JException as e:
            error_msg = f"DL consistency check error: {e.getMessage()}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            logger.error(f"Unexpected DL error: {e}")
            return False, str(e)

    def query_concept(self, kb, individual_name: str, concept_name: str) -> bool:
        """Check if an individual is an instance of a concept."""
        reasoner = self._get_reasoner()
        try:
            ind = self._Individual(individual_name)
            concept = self._AtomicConcept(concept_name)
            assertion = self._ConceptAssertion(ind, concept)
            result = reasoner.query(kb, assertion)
            return bool(result)
        except Exception as e:
            logger.error(f"DL instance query failed: {e}")
            raise

    def query_subsumption(self, kb, sub_concept: str, super_concept: str) -> bool:
        """Check if sub_concept is subsumed by super_concept (C ⊑ D)."""
        reasoner = self._get_reasoner()
        try:
            sub = self._AtomicConcept(sub_concept)
            sup = self._AtomicConcept(super_concept)
            # Subsumption: C ⊑ D iff ¬(C ⊓ ¬D) is consistent
            test_concept = self._Intersection(sub, self._Complement(sup))
            test_ind = self._Individual("_test_ind")
            assertion = self._ConceptAssertion(test_ind, test_concept)
            result = reasoner.query(kb, assertion)
            return not bool(result)  # If asserting C ⊓ ¬D fails, subsumption holds
        except Exception as e:
            logger.error(f"DL subsumption query failed: {e}")
            raise

    def parse_and_query(self, kb_string: str, query_string: str) -> Tuple[bool, str]:
        """Parse a DL knowledge base and query from strings."""
        try:
            parser = self._DlParser()
            StringReader = jpype.JClass("java.io.StringReader")

            kb = parser.parseBeliefBase(StringReader(kb_string))
            query = parser.parseFormula(jpype.JString(query_string))

            reasoner = self._get_reasoner()
            result = reasoner.query(kb, query)

            if bool(result):
                return True, f"DL query '{query_string}' is ENTAILED."
            else:
                return False, f"DL query '{query_string}' is NOT entailed."
        except jpype.JException as e:
            error_msg = f"DL parse/query error: {e.getMessage()}"
            logger.error(error_msg)
            return False, f"FUNC_ERROR: {error_msg}"
        except Exception as e:
            logger.error(f"Unexpected DL error: {e}")
            return False, f"FUNC_ERROR: {e}"
