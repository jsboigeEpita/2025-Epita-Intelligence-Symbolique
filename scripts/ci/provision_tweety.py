"""Provision the Tweety classpath on a cache miss (#1874).

Thin on purpose: the ordering (existing classpath -> legacy fat jar -> Maven
assembly) lives in ``download_tweety_jars`` because that is the path production
actually takes. A CI-only copy of that logic would be a second surface to keep
true.

Exits non-zero on failure. A partial classpath is worse than none: it starts a
JVM where every Tweety import fails, and the run then reports SKIPS instead of an
error -- the silent shape the #1385 guard exists to catch.
"""

import sys
from pathlib import Path

# `python scripts/ci/x.py` met scripts/ci/ dans sys.path[0], pas la racine du
# depot, et l'environnement CI n'installe aucune copie editable du paquet
# (environment.yml n'a pas de `-e .`). Sans cette ligne, l'import ci-dessous
# leve ModuleNotFoundError en CI tout en passant en local, ou un install
# editable resident masque le probleme -- mesure #1874.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from argumentation_analysis.core.jvm_setup import download_tweety_jars


def failure_annotation() -> str:
    """GitHub workflow command orienting the reader (#1874 point 5, retuned by #1959).

    The named cause already lives in the AssemblyError chain, but it sits
    mid-log: whoever lands on the red run page sees only "Process completed
    with exit code 1" and restarts the investigation from zero. This is the
    annotation-surface copy, and it must go to STDOUT -- GitHub parses
    ``::error::`` from stdout only.
    """
    return (
        "::error::Approvisionnement Tweety echoue. Le closure par defaut est "
        "servi a 74/74 par Maven Central: tweetyproject.org/mvn/ n'est plus un "
        "hote requis depuis #1959, donc ne pas partir enqueter dessus. Les trois "
        "artefacts qu'il servait seul (jspf:core, gurobi:gurobi, isula:isula) "
        "sont exclus par defaut -- s'ils reapparaissent dans l'erreur, la cause "
        "est que tweety_excluded_modules a ete vide ou surcharge. Sinon "
        "distinguer dans le log complet: (1) version non constructible = "
        "Could not FIND artifact org.tweetyproject...; (2) transport en "
        "panne sur Central = Could not TRANSFER ... Connection reset."
    )


def main() -> int:
    if download_tweety_jars():
        return 0
    print(failure_annotation())
    sys.stderr.write(
        "Approvisionnement Tweety echoue. La cause nommee est dans les lignes "
        "au-dessus (Maven absent, version non assemblable, reseau). Ne pas "
        "relancer a l'identique en esperant un resultat different.\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
