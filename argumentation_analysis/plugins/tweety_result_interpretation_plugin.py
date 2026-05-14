"""TweetyResultInterpretationPlugin — Tweety formal results to NL narrative.

Interprets formal analysis results (Dung extensions, FOL models, ASPIC attacks,
ranking scores, belief revisions) into human-readable NL explanations.
Provides both template-based (no LLM) and LLM-ready @kernel_function methods.

Issue #476: Semantic plugin TweetyResultInterpretationPlugin.
"""

import json
import logging
from typing import Dict, List, Optional

from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template-based interpreters (no LLM required)
# ---------------------------------------------------------------------------


def _interpret_dung(extensions: Dict, arguments: List[str] = None) -> str:
    """Generate NL interpretation of Dung framework analysis."""
    parts = []
    args_text = f"{len(arguments)} arguments" if arguments else "des arguments"

    if "grounded" in extensions:
        grounded = extensions["grounded"]
        if isinstance(grounded, dict):
            grounded = grounded.get("set", [])
        if grounded:
            parts.append(
                f"L'extension groundee (acceptee sans controversy) contient "
                f"{len(grounded)} argument(s): {', '.join(str(a) for a in grounded[:10])}."
            )
        else:
            parts.append("Aucun argument n'est accepte dans l'extension groundee.")

    if "preferred" in extensions:
        pref = extensions["preferred"]
        if isinstance(pref, dict):
            pref = pref.get("set", [])
        if pref:
            parts.append(
                f"L'extension preferee contient {len(pref)} argument(s)."
            )

    if "stable" in extensions:
        stable = extensions["stable"]
        if isinstance(stable, dict):
            stable = stable.get("set", [])
        if stable:
            parts.append(
                f"L'extension stable identifie {len(stable)} argument(s) accepte(s)."
            )

    if not parts:
        parts.append(f"Analyse Dung completee sur {args_text}.")

    return " ".join(parts)


def _interpret_fol(result: Dict) -> str:
    """Generate NL interpretation of FOL reasoning result."""
    accepted = result.get("accepted", False)
    query = result.get("query", "")
    message = result.get("message", result.get("result", ""))

    if accepted:
        return (
            f"La requete '{query}' est acceptee (deductible de l'ensemble de croyances). "
            f"{message}"
        )
    return (
        f"La requete '{query}' n'est pas acceptee. {message}"
    )


def _interpret_aspic(result: Dict) -> str:
    """Generate NL interpretation of ASPIC+ analysis."""
    parts = []

    strict = result.get("strict_rules", [])
    defeasible = result.get("defeasible_rules", [])
    attacks = result.get("attacks", [])

    if strict:
        parts.append(f"{len(strict)} regle(s) stricte(s) identifiee(s).")
    if defeasible:
        parts.append(f"{len(defeasible)} regle(s) defaisable(s) identifiee(s).")
    if attacks:
        parts.append(f"{len(attacks)} attaque(s) entre arguments.")

    if not parts:
        parts.append("Analyse ASPIC completee.")

    return " ".join(parts)


def _interpret_ranking(result: Dict) -> str:
    """Generate NL interpretation of ranking semantics."""
    rankings = result.get("rankings", result.get("scores", {}))
    if isinstance(rankings, list):
        rankings = {str(i): v for i, v in enumerate(rankings)}

    if not rankings:
        return "Classement des arguments complete."

    sorted_items = sorted(rankings.items(), key=lambda x: float(x[1]) if isinstance(x[1], (int, float)) else 0, reverse=True)
    top = sorted_items[:5]
    parts = [f"Top arguments: {', '.join(f'{k} ({v})' for k, v in top)}."]
    return " ".join(parts)


def _interpret_belief_revision(result: Dict) -> str:
    """Generate NL interpretation of belief revision."""
    parts = []
    removed = result.get("removed_beliefs", [])
    added = result.get("added_beliefs", [])
    revised = result.get("revised_beliefs", [])

    if removed:
        parts.append(f"{len(removed)} croyance(s) retiree(s).")
    if added:
        parts.append(f"{len(added)} croyance(s) ajoutee(s).")
    if revised:
        parts.append(f"{len(revised)} croyance(s) revisee(s).")

    if not parts:
        parts.append("Aucune revision de croyance necessaire.")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Plugin class
# ---------------------------------------------------------------------------


class TweetyResultInterpretationPlugin:
    """Semantic Kernel plugin for interpreting Tweety formal results.

    Provides @kernel_function methods that convert formal analysis output
    (Dung extensions, FOL query results, ASPIC attacks, etc.) into
    human-readable NL explanations.

    Usage:
        kernel.add_plugin(
            TweetyResultInterpretationPlugin(),
            plugin_name="tweety_result_interpretation",
        )
    """

    @kernel_function(
        name="interpret_dung_results",
        description=(
            "Interpreter les resultats d'analyse Dung en langage naturel. "
            "Entree: JSON {'extensions': {'grounded': [...], 'preferred': [...], ...}, "
            "'arguments': [...]}. "
            "Retourne texte NL explicatif."
        ),
    )
    def interpret_dung_results(self, input: str) -> str:
        """Interpret Dung framework analysis results."""
        try:
            params = json.loads(input) if isinstance(input, str) else input
        except (json.JSONDecodeError, TypeError):
            return "Impossible d'interpreter les resultats Dung: JSON invalide."

        extensions = params.get("extensions", {})
        arguments = params.get("arguments", [])
        return _interpret_dung(extensions, arguments)

    @kernel_function(
        name="interpret_fol_results",
        description=(
            "Interpreter les resultats de raisonnement FOL en langage naturel. "
            "Entree: JSON {'accepted': true/false, 'query': '...', 'message': '...'}. "
            "Retourne texte NL explicatif."
        ),
    )
    def interpret_fol_results(self, input: str) -> str:
        """Interpret FOL query results."""
        try:
            params = json.loads(input) if isinstance(input, str) else input
        except (json.JSONDecodeError, TypeError):
            return "Impossible d'interpreter les resultats FOL: JSON invalide."
        return _interpret_fol(params)

    @kernel_function(
        name="interpret_aspic_results",
        description=(
            "Interpreter les resultats d'analyse ASPIC+ en langage naturel. "
            "Entree: JSON avec regles strictes/defaisables et attaques. "
            "Retourne texte NL explicatif."
        ),
    )
    def interpret_aspic_results(self, input: str) -> str:
        """Interpret ASPIC+ analysis results."""
        try:
            params = json.loads(input) if isinstance(input, str) else input
        except (json.JSONDecodeError, TypeError):
            return "Impossible d'interpreter les resultats ASPIC: JSON invalide."
        return _interpret_aspic(params)

    @kernel_function(
        name="interpret_ranking_results",
        description=(
            "Interpreter les resultats de classement d'arguments en langage naturel. "
            "Entree: JSON avec scores/classements. "
            "Retourne texte NL avec top arguments."
        ),
    )
    def interpret_ranking_results(self, input: str) -> str:
        """Interpret ranking semantics results."""
        try:
            params = json.loads(input) if isinstance(input, str) else input
        except (json.JSONDecodeError, TypeError):
            return "Impossible d'interpreter les resultats de classement: JSON invalide."
        return _interpret_ranking(params)

    @kernel_function(
        name="interpret_belief_revision_results",
        description=(
            "Interpreter les resultats de revision de croyances. "
            "Entree: JSON avec croyances retirees/ajoutees/revisees. "
            "Retourne texte NL explicatif."
        ),
    )
    def interpret_belief_revision_results(self, input: str) -> str:
        """Interpret belief revision results."""
        try:
            params = json.loads(input) if isinstance(input, str) else input
        except (json.JSONDecodeError, TypeError):
            return "Impossible d'interpreter les resultats: JSON invalide."
        return _interpret_belief_revision(params)

    @kernel_function(
        name="interpret_full_analysis",
        description=(
            "Synthese NL globale de tous les resultats formels. "
            "Entree: JSON avec sous-resultats dung, fol, aspic, ranking, belief_revision. "
            "Retourne synthese NL multi-paragraphes."
        ),
    )
    def interpret_full_analysis(self, input: str) -> str:
        """Generate a full NL synthesis of all formal analysis results."""
        try:
            params = json.loads(input) if isinstance(input, str) else input
        except (json.JSONDecodeError, TypeError):
            return "Impossible de generer la synthese: JSON invalide."

        sections = []

        if "dung" in params:
            sections.append(
                "**Analyse Dung**: " + _interpret_dung(
                    params["dung"].get("extensions", {}),
                    params["dung"].get("arguments", []),
                )
            )

        if "fol" in params:
            sections.append(
                "**Raisonnement FOL**: " + _interpret_fol(params["fol"])
            )

        if "aspic" in params:
            sections.append(
                "**Analyse ASPIC+**: " + _interpret_aspic(params["aspic"])
            )

        if "ranking" in params:
            sections.append(
                "**Classement**: " + _interpret_ranking(params["ranking"])
            )

        if "belief_revision" in params:
            sections.append(
                "**Revision des croyances**: "
                + _interpret_belief_revision(params["belief_revision"])
            )

        if not sections:
            return "Aucun resultat formel a interpreter."

        return "\n\n".join(sections)

    @kernel_function(
        name="write_interpretation_to_state",
        description=(
            "Ecrire l'interpretation NL dans l'etat d'analyse. "
            "Entree: JSON {'interpretation': '...', 'section': 'narrative_synthesis'}. "
            "Retourne confirmation."
        ),
    )
    def write_interpretation_to_state(self, input: str, state: object = None) -> str:
        """Write interpretation results to analysis state."""
        if state is None:
            return json.dumps({"error": "No state provided"})

        try:
            params = json.loads(input) if isinstance(input, str) else input
        except (json.JSONDecodeError, TypeError):
            return json.dumps({"error": "Invalid JSON input"})

        interpretation = params.get("interpretation", "")
        if not interpretation:
            return json.dumps({"error": "Empty interpretation"})

        # Try to write to state's narrative_synthesis or add_extract
        written = False
        add_extract = getattr(state, "add_extract", None)
        if callable(add_extract):
            add_extract("formal_interpretation", interpretation)
            written = True

        return json.dumps({
            "written": written,
            "length": len(interpretation),
        })
