"""Handler for Assumption-Based Argumentation (ABA) via TweetyProject.

ABA frameworks use assumptions and inference rules to construct arguments.
Supports multiple semantics:
- Preferred
- Stable
- Complete
- Grounded (well-founded)
- Ideal
"""

import jpype
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ABAHandler:
    """Assumption-Based Argumentation analysis using Tweety."""

    REASONERS = {
        "preferred": "org.tweetyproject.arg.aba.reasoner.PreferredReasoner",
        "stable": "org.tweetyproject.arg.aba.reasoner.StableReasoner",
        "complete": "org.tweetyproject.arg.aba.reasoner.CompleteReasoner",
        "well_founded": "org.tweetyproject.arg.aba.reasoner.WellFoundedReasoner",
        "ideal": "org.tweetyproject.arg.aba.reasoner.IdealReasoner",
        "flat": "org.tweetyproject.arg.aba.reasoner.FlatAbaReasoner",
    }

    def __init__(self, initializer_instance=None):
        if initializer_instance and not initializer_instance.is_jvm_ready():
            raise RuntimeError("ABAHandler instantiated before JVM is ready.")
        self.AbaTheory = jpype.JClass("org.tweetyproject.arg.aba.syntax.AbaTheory")
        self.Assumption = jpype.JClass("org.tweetyproject.arg.aba.syntax.Assumption")
        self.InferenceRule = jpype.JClass("org.tweetyproject.arg.aba.syntax.InferenceRule")
        self.Negation = jpype.JClass("org.tweetyproject.arg.aba.syntax.Negation")
        self.AbaParser = jpype.JClass("org.tweetyproject.arg.aba.parser.AbaParser")
        # PL formula classes for ABA over propositional logic
        self.PlFormula = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlFormula")
        self.Proposition = jpype.JClass("org.tweetyproject.logics.pl.syntax.Proposition")
        self.PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")
        self._reasoner_cache = {}

    def _get_reasoner(self, semantics: str):
        if semantics not in self._reasoner_cache:
            if semantics not in self.REASONERS:
                raise ValueError(f"Unknown ABA semantics: {semantics}. Available: {list(self.REASONERS.keys())}")
            cls = jpype.JClass(self.REASONERS[semantics])
            self._reasoner_cache[semantics] = cls()
        return self._reasoner_cache[semantics]

    def analyze_aba_framework(
        self,
        assumptions: List[str],
        rules: List[Dict[str, Any]],
        contraries: Optional[Dict[str, str]] = None,
        semantics: str = "preferred",
    ) -> Dict[str, Any]:
        """Analyze an ABA framework.

        Args:
            assumptions: List of assumption names.
            rules: List of dicts with 'head' and 'body' (list of strings).
            contraries: Dict mapping assumption -> its contrary.
            semantics: Semantics to use (preferred, stable, complete, well_founded, ideal).

        Returns:
            Dict with extensions and statistics.
        """
        try:
            theory = self.AbaTheory()

            # Add assumptions
            for asm_name in assumptions:
                prop = self.Proposition(asm_name)
                assumption = self.Assumption(prop)
                theory.add(assumption)

            # Add contraries (assumption -> contrary mapping)
            if contraries:
                for asm_name, contrary_name in contraries.items():
                    asm_prop = self.Proposition(asm_name)
                    contrary_prop = self.Proposition(contrary_name)
                    assumption = self.Assumption(asm_prop)
                    assumption.setConclusion(contrary_prop)

            # Add rules
            for rule_def in rules:
                head_name = rule_def.get("head", "")
                body_names = rule_def.get("body", [])
                head = self.Proposition(head_name)
                rule = self.InferenceRule()
                rule.setConclusion(head)
                for body_name in body_names:
                    rule.addPremise(self.Proposition(body_name))
                theory.add(rule)

            # Get extensions using chosen semantics
            reasoner = self._get_reasoner(semantics)
            extensions = reasoner.getModels(theory)

            # Convert to Python
            ext_list = []
            for ext in extensions:
                ext_elements = [str(elem) for elem in ext]
                ext_list.append(sorted(ext_elements))

            return {
                "semantics": semantics,
                "extensions": sorted(ext_list),
                "assumptions": sorted(assumptions),
                "rules_count": len(rules),
                "statistics": {
                    "assumptions_count": len(assumptions),
                    "rules_count": len(rules),
                    "extensions_count": len(ext_list),
                },
            }
        except jpype.JException as e:
            logger.error(f"Java exception in ABA analysis: {e}")
            raise RuntimeError(f"ABA analysis failed: {e}") from e

    def parse_aba_file(self, file_path: str, semantics: str = "preferred") -> Dict[str, Any]:
        """Parse an ABA framework from a file and analyze it.

        Args:
            file_path: Path to .aba file.
            semantics: Semantics to use.

        Returns:
            Dict with analysis results.
        """
        try:
            parser = self.AbaParser()
            parser.setFormulaParser(self.PlParser())
            theory = parser.parseBeliefBaseFromFile(file_path)

            reasoner = self._get_reasoner(semantics)
            extensions = reasoner.getModels(theory)

            ext_list = []
            for ext in extensions:
                ext_elements = [str(elem) for elem in ext]
                ext_list.append(sorted(ext_elements))

            return {
                "semantics": semantics,
                "source": file_path,
                "extensions": sorted(ext_list),
                "statistics": {
                    "extensions_count": len(ext_list),
                },
            }
        except jpype.JException as e:
            logger.error(f"Java exception parsing ABA file: {e}")
            raise RuntimeError(f"ABA file parsing failed: {e}") from e
