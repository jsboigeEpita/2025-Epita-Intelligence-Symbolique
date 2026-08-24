"""Assert the restored/assembled Tweety classpath is usable (#1874).

Runs on the cache-HIT path, where the assembly never runs and therefore never
checks anything. ``actions/cache`` reports a hit for whatever it stored; if that
was a partial or corrupted assembly, nothing else says so, and the failure
surfaces downstream as a *skip storm* rather than an error.

Rewritten after adversarial review of the first version, which could not fail on
the shapes it claimed to catch:

* it re-ran ``is_already_assembled`` -- the SAME predicate production already
  applies -- whose floor is 60 while the real closure is 149 jars, so a restore
  that had lost 89 jars out of 149 was accepted;
* it required only that *some* class be readable, not that any Tweety class be
  present, so a directory of unrelated jars passed;
* worse, its floor comparison got EASIER as the classpath degraded: fewer Tweety
  classes meant a lower observed bytecode major, meant a lower required Java
  release, meant the declared floor cleared it more comfortably. Sensitivity
  inverted -- the check rewarded damage;
* a corrupt jar was printed and skipped, so 148 corrupt jars plus one readable
  one scored a pass.

The criterion is now consumer-shaped: **every Tweety class this repository names
by FQCN must be resolvable in the classpath.** Measured 2026-08-24 against both
fat jars on disk: 120 named classes, 120 present in 1.28 and in 1.29. Losing jars
can only make this harder to satisfy, which is the direction a verification
should run.
"""

import json
import re
import struct
import zipfile
from pathlib import Path

from argumentation_analysis.config.settings import settings
from argumentation_analysis.core import tweety_assembly

CLASS_MAGIC = b"\xca\xfe\xba\xbe"
REPO_ROOT = Path(__file__).resolve().parents[2]

# `"org.tweetyproject.<...>"` string literals in the source. The last segment tells
# a class from a package: Java classes are capitalised, packages are not. Without
# that filter the harvest picks up 9 package literals that are legitimately absent
# from any jar, and the check would fail on a healthy classpath.
FQCN_LITERAL = re.compile(r'"(org\.tweetyproject\.[A-Za-z0-9_.]+)"')

# Measured 2026-08-24: 120 class FQCNs across argumentation_analysis/. The floor is
# a non-vacuity control, not a target -- see `main`.
MIN_HARVESTED_FQCNS = 50


def required_fqcns():
    """Tweety classes production names by FQCN, harvested from the source."""
    found = set()
    for py in (REPO_ROOT / "argumentation_analysis").rglob("*.py"):
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in FQCN_LITERAL.finditer(text):
            fq = m.group(1)
            if fq.rsplit(".", 1)[-1][:1].isupper():
                found.add(fq)
    return found


def class_entries(libs: Path):
    """Every ``.class`` entry across the jars, plus the worst legacy-visible major.

    ``META-INF/versions/N/`` entries are multi-release and invisible to older JVMs,
    so counting them overstates the floor: the 1.28 fat jar carries one major-65
    logback class there and would otherwise read as "needs Java 21".

    A jar that cannot be opened raises. The previous version printed and continued,
    which let a directory of corrupt jars pass on the strength of one readable one.
    """
    names, worst, worst_where = set(), 0, ""
    for jar in sorted(libs.glob("*.jar")):
        try:
            with zipfile.ZipFile(jar) as z:
                for name in z.namelist():
                    if not name.endswith(".class"):
                        continue
                    names.add(name)
                    if name.startswith("META-INF/versions/"):
                        continue
                    head = z.read(name)[:8]
                    if len(head) >= 8 and head[:4] == CLASS_MAGIC:
                        major = struct.unpack(">H", head[6:8])[0]
                        if major > worst:
                            worst, worst_where = major, f"{jar.name}!{name}"
        except (zipfile.BadZipFile, OSError) as exc:
            # stdout like every other verdict here, so the CI log reads in one stream.
            print(
                f"ECHEC: {jar.name} n'est pas un zip lisible ({exc}). Un cache HIT "
                "peut restaurer des jars tronques: les ignorer laisserait passer un "
                "classpath mort."
            )
            raise SystemExit(1)
    return names, worst, worst_where


def check_manifest(libs: Path, version: str) -> int:
    """Compare the restored directory to what the assembly recorded producing.

    This is the one count check production does not already make. ``MIN_EXPECTED_JARS``
    is a floor (60) calibrated well under the real closure (149 measured on CI), so it
    cannot see a restore that lost most of its jars. An exact count can.
    """
    manifest = libs / tweety_assembly.ASSEMBLY_MANIFEST
    if not manifest.exists():
        if tweety_assembly.count_module_jars(libs, version=version) == 0:
            print("  (pas de manifeste: classpath fat-jar, jamais assemble ici)")
            return 0
        print(
            f"ECHEC: {libs} porte un assemblage sans "
            f"{tweety_assembly.ASSEMBLY_MANIFEST}. Impossible de distinguer une "
            "restauration complete d'une restauration amputee -- le plancher de "
            "production ne le peut pas non plus."
        )
        return 1
    try:
        recorded = json.loads(manifest.read_text(encoding="utf-8"))
        expected_modules = int(recorded["module_jars"])
        expected_total = int(recorded["total_jars"])
        recorded_version = str(recorded["version"])
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"ECHEC: manifeste illisible ({exc}).")
        return 1

    actual = tweety_assembly.count_module_jars(libs, version=recorded_version)
    total = len(list(libs.glob("*.jar")))
    print(
        f"  manifeste ({recorded_version}): {expected_modules} module(s) / "
        f"{expected_total} jar(s) enregistres, {actual} / {total} presents"
    )
    if actual != expected_modules or total != expected_total:
        print(
            f"ECHEC: la restauration ne correspond pas au manifeste "
            f"({total} jar(s) presents pour {expected_total} enregistres). Un "
            "classpath ampute demarre la JVM et fait echouer chaque import -- en "
            "skips, pas en erreurs."
        )
        return 1
    return 0


def main() -> int:
    libs = Path(settings.jvm.tweety_libs_dir)
    version = settings.jvm.tweety_version
    if not libs.is_dir():
        print(f"ECHEC: {libs} n'existe pas.")
        return 1

    jars = sorted(libs.glob("*.jar"))
    print(f"  classpath: {len(jars)} jar(s) pour Tweety {version}")
    if not jars:
        print("ECHEC: aucun jar.")
        return 1

    if check_manifest(libs, version):
        return 1

    names, worst, where = class_entries(libs)

    wanted = required_fqcns()
    # Non-vacuity control: a harvest of zero would make the next check pass on
    # anything. The instrument must be able to produce a positive before its zero
    # means a thing.
    if len(wanted) < MIN_HARVESTED_FQCNS:
        print(
            f"ECHEC: seulement {len(wanted)} FQCN Tweety recoltes dans les sources "
            f"(>= {MIN_HARVESTED_FQCNS} attendus, 120 mesures le 2026-08-24). Le "
            "controle serait vide: c'est l'instrument qui est casse, pas le classpath."
        )
        return 1

    missing = sorted(f for f in wanted if f.replace(".", "/") + ".class" not in names)
    print(
        f"  FQCN nommes par la production: {len(wanted) - len(missing)}/{len(wanted)}"
    )
    if missing:
        print(
            f"ECHEC: {len(missing)} classe(s) Tweety nommee(s) par la production sont "
            "absentes du classpath. La JVM demarrera et chaque import les concernant "
            "echouera -- en skips, pas en erreurs."
        )
        for f in missing[:10]:
            print(f"    absente: {f}")
        return 1

    if worst == 0:
        print("ECHEC: aucune classe lisible.")
        return 1
    needed = worst - 44
    print(
        f"  bytecode max (hors multi-release): major={worst} -> Java {needed}  [{where}]"
    )
    print(f"  plancher declare: {settings.jvm.min_java_version}")
    if settings.jvm.min_java_version < needed:
        print(
            f"ECHEC: le plancher declare ({settings.jvm.min_java_version}) est SOUS ce "
            f"que le bytecode exige (Java {needed}). Un JDK admis par ce plancher "
            "demarre puis echoue chaque chargement de classe."
        )
        return 1

    print("  OK: classpath complet, classes nommees presentes, plancher coherent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
