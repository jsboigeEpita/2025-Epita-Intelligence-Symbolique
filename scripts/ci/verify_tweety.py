"""Assert the restored/assembled Tweety classpath is usable (#1874).

Two failures this catches, both otherwise SILENT and both surfacing downstream
as a skip storm rather than an error:

1. **A cache hit that restored a useless directory.** ``actions/cache`` reports a
   hit for whatever it stored; if that was a partial assembly, nothing says so.
   This is the same shape ``INCOMPLETE_MARKER`` guards inside the assembly, moved
   to the one place the assembly never runs -- the hit path.

2. **A JDK too old for the bytecode.** Measured 2026-08-24 across the 1.28 fat
   jar, the 1.29 fat jar and a 1.31 Maven assembly: the highest class-file major
   outside ``META-INF/versions/`` is **59 = Java 15** in all three, carried by a
   real class (``org/tweetyproject/action/grounding/VarsNeqRequirement``), and
   **120 of the 129** Tweety classes this repo names by FQCN are above major 55.
   ``settings.jvm.min_java_version`` nevertheless declared 11. Nothing compared
   the declaration to the bytecode; this is that comparison, in pure Python.

   It does not currently fire in CI, and the reason matters: ``jvm_setup``
   ignores ``JAVA_HOME`` and provisions its own portable JDK 17, so the Java 11
   from ``setup-java`` never reaches the JVM. The declaration is a latent trap --
   a JDK 11 dropped into ``portable_jdk/`` would be *accepted* by the floor and
   then fail every class load -- not today's blocker. Stated plainly so the next
   reader does not mistake this check for the thing that unblocked the gate.
"""

import os
import re
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

from argumentation_analysis.config.settings import settings
from argumentation_analysis.core import tweety_assembly

CLASS_MAGIC = b"\xca\xfe\xba\xbe"


def java_release(major: int) -> int:
    """Class-file major to Java feature release (45 == Java 1.1)."""
    return major - 44


def max_class_major(libs: Path):
    """Highest class-file major a *legacy* JVM would actually try to load.

    ``META-INF/versions/N/`` entries are multi-release and invisible to older
    JVMs, so counting them overstates the floor: the 1.28 fat jar carries one
    major-65 logback class there and would otherwise read as "needs Java 21".
    """
    worst, worst_where = 0, ""
    for jar in sorted(libs.glob("*.jar")):
        try:
            with zipfile.ZipFile(jar) as z:
                for name in z.namelist():
                    if not name.endswith(".class"):
                        continue
                    if name.startswith("META-INF/versions/"):
                        continue
                    head = z.read(name)[:8]
                    if len(head) >= 8 and head[:4] == CLASS_MAGIC:
                        major = struct.unpack(">H", head[6:8])[0]
                        if major > worst:
                            worst, worst_where = major, f"{jar.name}!{name}"
        except zipfile.BadZipFile:
            print(f"  !! {jar.name} n'est pas un zip valide")
    return worst, worst_where


def running_java_major():
    java = "java"
    home = os.environ.get("JAVA_HOME")
    if home and (Path(home) / "bin").is_dir():
        java = str(Path(home) / "bin" / "java")
    try:
        out = subprocess.run(
            [java, "-version"], capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError):
        return None
    blob = (out.stderr or "") + (out.stdout or "")
    m = re.search(r'version "(\d+)(?:\.(\d+))?', blob)
    if not m:
        return None
    first = int(m.group(1))
    # "1.8.0_402" -> 8 ; "17.0.12" -> 17
    return int(m.group(2)) if first == 1 and m.group(2) else first


def main() -> int:
    libs = Path(settings.jvm.tweety_libs_dir)
    version = settings.jvm.tweety_version
    if not libs.is_dir():
        print(f"ECHEC: {libs} n'existe pas.")
        return 1

    jars = sorted(libs.glob("*.jar"))
    modules = tweety_assembly.count_module_jars(libs, version=version)
    print(f"  classpath: {len(jars)} jar(s), {modules} module(s) Tweety en {version}")

    if not tweety_assembly.is_already_assembled(libs, version=version):
        print(
            f"ECHEC: {libs} ne porte pas de classpath utilisable pour {version} "
            f"(ni fat jar, ni assemblage au-dessus du plancher "
            f"{tweety_assembly.MIN_EXPECTED_JARS}). Un cache HIT peut restaurer "
            "un assemblage partiel: c'est exactement ce que ce controle attrape."
        )
        return 1

    worst, where = max_class_major(libs)
    if worst == 0:
        print("ECHEC: aucune classe lisible dans le classpath (jars vides ?).")
        return 1
    needed = java_release(worst)
    running = running_java_major()
    print(
        f"  bytecode max (hors multi-release): major={worst} -> Java {needed}  [{where}]"
    )
    # Informationnel, JAMAIS un critere d'echec -- et ce n'est pas un oubli.
    # `setup-java` pose JAVA_HOME sur Java 11, mais `jvm_setup` IGNORE JAVA_HOME
    # ("Recherche d'un JDK portable pre-existant valide (JAVA_HOME est ignore)")
    # et provisionne son propre JDK 17. Transformer cette ligne en controle dur
    # ferait rougir le job sur un JDK que la JVM n'utilise pas. Le controle qui
    # decide est la comparaison plancher-declare / bytecode, juste en dessous.
    print(
        f"  JVM sur JAVA_HOME: Java {running}  (indicatif: jvm_setup ignore JAVA_HOME)"
    )
    print(
        f"  plancher declare (settings.jvm.min_java_version): {settings.jvm.min_java_version}"
    )

    if settings.jvm.min_java_version < needed:
        print(
            f"ECHEC: le plancher declare ({settings.jvm.min_java_version}) est SOUS "
            f"ce que le bytecode exige (Java {needed}). Un JDK admis par ce plancher "
            "demarre puis echoue chaque chargement de classe -- en skips, pas en "
            "erreur."
        )
        return 1

    print("  OK: classpath non vide pour la version demandee, plancher coherent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
