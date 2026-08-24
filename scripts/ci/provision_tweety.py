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

from argumentation_analysis.core.jvm_setup import download_tweety_jars


def main() -> int:
    if download_tweety_jars():
        return 0
    sys.stderr.write(
        "Approvisionnement Tweety echoue. La cause nommee est dans les lignes "
        "au-dessus (Maven absent, version non assemblable, reseau). Ne pas "
        "relancer a l'identique en esperant un resultat different.\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
