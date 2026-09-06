"""French singular/plural agreement, computed from the count (#2046).

The « N truc(s) » gabarit is a solver-output marker the readability gate
itself tracks as machinery (#1908, ``_MORPHOLOGY_S_RE``): whatever surface it
reaches — evidence prompt, degradation motif, gate reason, appendix — the
reader receives « 1 inférence » / « 3 inférences », never the parenthetical
alternation. The count is at hand at every interpolation site, so the
agreement is computed here instead of left to a « (s) ».

Sites that also need verb agreement (était/étaient, survit/survivent) keep
their ternary at the call site — this helper carries the noun phrase only.
"""

from __future__ import annotations


def accord(n: int, singulier: str, pluriel: str | None = None) -> str:
    """« 1 inférence » / « 3 inférences » — number + agreed noun phrase."""
    if pluriel is None:
        pluriel = singulier + "s"
    return f"{n} {singulier if n == 1 else pluriel}"
