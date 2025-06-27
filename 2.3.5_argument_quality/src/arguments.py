from enum import Enum
import re

class ArgumentType(Enum):
    LOGICAL = "Logique (déduction, induction)"
    CAUSAL = "Causalité"
    ANALOGICAL = "Analogie"
    RHETORICAL = "Rhétorique (appel à l'émotion)"
    AUTHORITY = "Argument d'autorité"
    EXAMPLE = "Exemple ou illustration"
    GENERALIZATION = "Généralisation"
    UNKNOWN = "Inconnu"

ARGUMENT_PATTERNS = {
    ArgumentType.CAUSAL: [
        r"\bparce que\b", r"\bcar\b", r"\bentraîne\b", r"\bcause\b", r"\bconduit à\b"
    ],
    ArgumentType.LOGICAL: [
        r"\bsi\b.+\balors\b", r"\bon peut déduire que\b", r"\bil en découle que\b"
    ],
    ArgumentType.ANALOGICAL: [
        r"\bc’est comme\b", r"\bà l’image de\b", r"\bde même que\b"
    ],
    ArgumentType.RHETORICAL: [
        r"\bc’est inadmissible\b", r"\bscandaleux\b", r"\bterrifiant\b"
    ],
    ArgumentType.AUTHORITY: [
        r"\bd’après\b", r"\bselon\b", r"\bl’expert\b", r"\bétudes montrent\b"
    ],
    ArgumentType.EXAMPLE: [
        r"\bpar exemple\b", r"\bcomme le montre\b", r"\btel que\b"
    ],
    ArgumentType.GENERALIZATION: [
        r"\btous\b", r"\btoujours\b", r"\bon dit que\b"
    ]
}
