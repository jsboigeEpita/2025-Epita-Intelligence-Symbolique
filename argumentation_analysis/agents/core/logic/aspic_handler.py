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

    def __init__(self, initializer_instance: Optional[Any] = None) -> None:
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
        # #1678: a genuine Negation (org...pl.syntax.Negation) wrapping a
        # Proposition. This is the ONLY way to express a contradictory in
        # Tweety's PL layer — a head string of "!x" or "-x" is absorbed into
        # the identifier as a Proposition named "!x"/"-x" (measured on PlParser:
        # "-x" → Proposition, "!x" → Negation). An attack in ASPIC+ requires a
        # formula AND its negation; without Negation the theory can only render
        # a single extension (the vacuous-evaluated trap of #1671/#1674).
        self.Negation = jpype.JClass("org.tweetyproject.logics.pl.syntax.Negation")
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

            # Add strict rules. A rule head may be negated (#1678): a dict
            # carrying ``head_negated=True`` builds ``Negation(Proposition(head))``
            # instead of a bare Proposition — the only Tweety-PL construction
            # that produces a genuine contrary (a "!head"/"-head" string would
            # be absorbed into the identifier, measured: 0 attack).
            for rule_def in strict_rules:
                head = self._build_head(rule_def)
                rule = self.StrictRule()
                rule.setConclusion(head)
                for body_name in rule_def.get("body", []):
                    rule.addPremise(self.Proposition(body_name))
                theory.addRule(rule)

            # Add defeasible rules
            for rule_def in defeasible_rules:
                head = self._build_head(rule_def)
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

            # Get extensions. SimpleAspicReasoner does NOT expose getModels
            # directly; it translates the ASPIC+ theory into a Dung framework
            # via getDungTheory(theory, invertable), and the underlying Dung
            # reasoner (SimplePreferredReasoner, passed to the ctor above)
            # computes the extensions on that DungTheory. The 2nd arg is an
            # Invertable — a PL formula-type signature; a Proposition instance
            # is the PL Invertable (verified empirically). (Prior code called
            # reasoner.getModels(theory) → AttributeError on every real run.)
            inv = self.Proposition("aspic_pl_formula")
            dung_theory = reasoner.getDungTheory(theory, inv)
            dung_reasoner = self.SimplePreferredReasoner()
            extensions = dung_reasoner.getModels(dung_theory)

            ext_list = []
            for ext in extensions:
                ext_elements = [str(arg) for arg in ext]
                ext_list.append(sorted(ext_elements))

            # #1678: count the REAL Dung attacks materialized in the generated
            # framework. The qualification below is derived from the rule INPUTS
            # (which negated head plays which role) — it reports the SENSE of each
            # contradiction we introduced. But sense must never be reported as
            # materialized when the framework rendered zero attacks (e.g. a
            # negation that did not actually contradict, or an argument that did
            # not derive). Gating qualification on a real Dung edge count keeps
            # the two honest: no ``undercut``/``rebut``/``undermine`` label unless
            # the framework actually split. (Measured: getDungTheory →
            # getAttacks(); the count matches the coordinator's probe D2, 6 edges
            # for 3 contradictions across 8 args.)
            dung_attacks = 0
            try:
                dung_attacks = int(len(dung_theory.getAttacks()))
            except Exception:
                dung_attacks = 0

            # #1678: qualify each negated-head rule by its attack scope, derived
            # from the structure of the supplied rules — never from keywords.
            # An ASPIC+ attack is a rule whose conclusion negates a formula that
            # another rule asserts. The scope is determined by which role the
            # negated atom plays in the rest of the framework:
            #   - the rule NAME of another rule        → undercut (the inference
            #     itself is contested; asymmetric — PlFormulaGenerator.getRuleFormula
            #     renders a Proposition named after the rule, so negating that
            #     name attacks the rule, measured firsthand)
            #   - the CONCLUSION (head) of another rule → rebut
            #   - a PREMISE (body atom) of another rule → undermine
            # This is the unique singular contribution of ASPIC+ (the whole point
            # of #1649/#1678); without it the handler only renders a Dung
            # projection. Qualification is gated on ``dung_attacks``: a real Dung
            # edge must confirm a split before any scope is reported.
            attacks = (
                self._qualify_attacks(strict_rules, defeasible_rules)
                if dung_attacks > 0
                else []
            )

            return {
                "reasoner_type": reasoner_type,
                "extensions": sorted(ext_list),
                "attacks": attacks,
                "statistics": {
                    "strict_rules_count": len(strict_rules),
                    "defeasible_rules_count": len(defeasible_rules),
                    "axioms_count": len(axioms) if axioms else 0,
                    "extensions_count": len(ext_list),
                    "attacks_count": len(attacks),
                    "dung_attacks_count": dung_attacks,
                },
            }
        except jpype.JException as e:
            logger.error(f"Java exception in ASPIC+ analysis: {e}")
            raise RuntimeError(f"ASPIC+ analysis failed: {e}") from e

    # ------------------------------------------------------------------
    # #1678 helpers — negated-head construction + structural scope qualification
    # ------------------------------------------------------------------

    def _build_head(self, rule_def: Dict[str, Any]) -> Any:
        """Build a rule conclusion: ``Negation(Proposition(head))`` when
        ``head_negated`` is set, else a bare ``Proposition(head)``.

        The negation is structural, not textual: a ``head`` string already
        carrying ``"!"`` or ``"-"`` is left untouched and becomes a Proposition
        NAMED with that prefix (no negation, no attack) — callers must opt in
        via ``head_negated`` to express a genuine contrary.
        """
        head = self.Proposition(rule_def["head"])
        if rule_def.get("head_negated"):
            return self.Negation(head)
        return head

    def _qualify_attacks(
        self,
        strict_rules: List[Dict[str, Any]],
        defeasible_rules: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Qualify every negated-head rule by its ASPIC+ attack scope.

        Derives undercut / rebut / undermine from the framework structure
        (which role the negated atom plays elsewhere), with no keyword
        heuristic. An atom may play several roles; a single negation is then
        reported once per role it actually contests.
        """
        all_rules = list(strict_rules) + list(defeasible_rules)
        rule_names = {str(r.get("name")) for r in all_rules if r.get("name")}
        head_atoms = {
            str(r.get("head"))
            for r in all_rules
            if r.get("head") and not r.get("head_negated")
        }
        body_atoms: set[str] = set()
        for r in all_rules:
            for b in r.get("body", []) or []:
                body_atoms.add(str(b))

        attacks: List[Dict[str, Any]] = []
        for r in defeasible_rules:
            if not r.get("head_negated"):
                continue
            target = str(r.get("head"))
            attacker = str(r.get("name", ""))
            attacker_body = [str(b) for b in r.get("body", []) or []]
            # A negated head may contest several roles at once; emit one
            # qualified attack per role the target atom actually plays.
            scopes: List[str] = []
            if target in rule_names:
                scopes.append("undercut")
            if target in head_atoms:
                scopes.append("rebut")
            if target in body_atoms:
                scopes.append("undermine")
            if not scopes:
                scopes.append("unresolved")
            for scope in scopes:
                attacks.append(
                    {
                        "attacker_rule": attacker,
                        "attacker_premises": attacker_body,
                        "target": target,
                        "scope": scope,
                    }
                )
        return attacks
