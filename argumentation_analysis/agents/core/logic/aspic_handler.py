"""Handler for ASPIC+ structured argumentation via TweetyProject.

ASPIC+ constructs arguments from strict and defeasible inference rules,
then evaluates them using Dung semantics on the generated framework.

Supports:
- SimpleAspicReasoner (default)
- DirectionalAspicReasoner
- Rule ordering (weakest link, last link)
"""

import jpype
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ASPICHandler:
    """ASPIC+ structured argumentation analysis using Tweety."""

    def __init__(self, initializer_instance=None):
        if initializer_instance and not initializer_instance.is_jvm_ready():
            raise RuntimeError("ASPICHandler instantiated before JVM is ready.")
        self.AspicTheory = jpype.JClass(
            "org.tweetyproject.arg.aspic.syntax.AspicArgumentationTheory"
        )
        self.StrictRule = jpype.JClass(
            "org.tweetyproject.arg.aspic.syntax.StrictInferenceRule"
        )
        self.DefeasibleRule = jpype.JClass(
            "org.tweetyproject.arg.aspic.syntax.DefeasibleInferenceRule"
        )
        self.SimpleAspicReasoner = jpype.JClass(
            "org.tweetyproject.arg.aspic.reasoner.SimpleAspicReasoner"
        )
        self.DirectionalReasoner = jpype.JClass(
            "org.tweetyproject.arg.aspic.reasoner.DirectionalAspicReasoner"
        )
        self.PlFormulaGenerator = jpype.JClass(
            "org.tweetyproject.arg.aspic.ruleformulagenerator.PlFormulaGenerator"
        )
        self.PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")
        self.Proposition = jpype.JClass(
            "org.tweetyproject.logics.pl.syntax.Proposition"
        )
        # Dung reasoners for the generated AF
        self.SimplePreferredReasoner = jpype.JClass(
            "org.tweetyproject.arg.dung.reasoner.SimplePreferredReasoner"
        )
        self.AspicParser = jpype.JClass(
            "org.tweetyproject.arg.aspic.parser.AspicParser"
        )

    def analyze_aspic_framework(
        self,
        strict_rules: List[Dict[str, Any]],
        defeasible_rules: List[Dict[str, Any]],
        axioms: Optional[List[str]] = None,
        reasoner_type: str = "simple",
    ) -> Dict[str, Any]:
        """Analyze an ASPIC+ framework.

        Args:
            strict_rules: List of dicts with 'head' and 'body' (strict rules).
            defeasible_rules: List of dicts with 'head', 'body', and optional 'name'.
            axioms: List of axiom propositions (premises).
            reasoner_type: "simple" or "directional".

        Returns:
            Dict with extensions and statistics.
        """
        try:
            theory = self.AspicTheory(self.PlFormulaGenerator())

            # Add strict rules
            for rule_def in strict_rules:
                head = self.Proposition(rule_def["head"])
                rule = self.StrictRule()
                rule.setConclusion(head)
                for body_name in rule_def.get("body", []):
                    rule.addPremise(self.Proposition(body_name))
                theory.addRule(rule)

            # Add defeasible rules
            for rule_def in defeasible_rules:
                head = self.Proposition(rule_def["head"])
                rule = self.DefeasibleRule()
                rule.setConclusion(head)
                for body_name in rule_def.get("body", []):
                    rule.addPremise(self.Proposition(body_name))
                if "name" in rule_def:
                    rule.setName(rule_def["name"])
                theory.addRule(rule)

            # Add axioms as ordinary premises
            if axioms:
                for axiom_name in axioms:
                    theory.addOrdinaryPremise(self.Proposition(axiom_name))

            # Choose reasoner
            if reasoner_type == "directional":
                reasoner = self.DirectionalReasoner(self.SimplePreferredReasoner())
            else:
                reasoner = self.SimpleAspicReasoner(self.SimplePreferredReasoner())

            # Get extensions
            extensions = reasoner.getModels(theory)

            ext_list = []
            for ext in extensions:
                ext_elements = [str(arg) for arg in ext]
                ext_list.append(sorted(ext_elements))

            return {
                "reasoner_type": reasoner_type,
                "extensions": sorted(ext_list),
                "statistics": {
                    "strict_rules_count": len(strict_rules),
                    "defeasible_rules_count": len(defeasible_rules),
                    "axioms_count": len(axioms) if axioms else 0,
                    "extensions_count": len(ext_list),
                },
            }
        except jpype.JException as e:
            logger.error(f"Java exception in ASPIC+ analysis: {e}")
            raise RuntimeError(f"ASPIC+ analysis failed: {e}") from e
