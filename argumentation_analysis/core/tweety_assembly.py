"""Assemble the Tweety classpath from Maven Central (#1874).

Why this module exists
----------------------
``download_tweety_jars`` used to fetch a single fat jar from
``https://tweetyproject.org/builds/{version}/``. That path now **404s**: upstream
removed the ``/builds/`` directory, so ``libs/tweety/`` stays empty on a fresh
runner, the JVM refuses to start, and the whole suite skips. Measured on #1874:

* ``tweetyproject.org/builds/`` -- **404**, the fat-jar channel is gone.
* ``tweetyproject.org/mvn/`` -- **alive (200)**, declared in Tweety's *parent* POM
  and therefore inherited by every module. It serves three artifacts that Maven
  Central does not have (``jspf:core``, ``gurobi:gurobi``, ``isula:isula``), so it
  is still load-bearing for a full build even though it is not our download source.
* **Maven Central carries 1.18 through 1.31**, immutably, with no
  ``-with-dependencies`` classifier at any version.

So the *library* did not disappear -- its *packaging* did. Assembling the classpath
from Central is therefore the durable path, and it needs no third-party hosting.

Two traps this module is shaped around, both measured rather than assumed
----------------------------------------------------------------------
1. **The aggregator resolves while its parts do not.** ``tweety-full:1.28`` exists
   on Central and declares 47 modules at 1.28 -- none of which are published.
   "Does version X exist?" answers YES and the build still fails. Only **1.29,
   1.30 and 1.31** are assemblable; 1.26 and 1.28 are not. :func:`assemble` does
   not try to pre-validate that -- it lets Maven fail and reports the real cause,
   because a version check that reads the aggregator would answer YES again.
2. **1.31 deletes a capability we expose.** ``org.tweetyproject.arg:bipolar`` drops
   from 86 to 16 classes at 1.31: the whole evidential family disappears with no
   successor, and ``framework_type=evidential`` is a documented option of a
   registered ``@kernel_function``. Hence :data:`DEFAULT_PIN_SPEC`-style pinning --
   a module may be held at an older version inside an otherwise-newer closure.
   Measured working: 1.31 + ``bipolar:1.30`` loads and *computes*; 1.31 alone
   fails to initialise. Maven's nearest-definition-wins rule makes a direct
   declaration beat the transitive one, which is why the pin is emitted as a
   first-class ``<dependency>``.

Everything that can be decided without the network is a pure function, so the
tests do not need Maven, a JVM, or an internet connection.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

MAVEN_CENTRAL = "https://repo1.maven.org/maven2"
TWEETY_GROUP = "org.tweetyproject"
TWEETY_AGGREGATOR = "tweety-full"
# Non-Central artifacts of the closure (jspf:core, gurobi, isula) are served only
# from here. Alive (200) as of #1874, unlike the removed /builds/ fat-jar channel.
TWEETY_MVN_REPO = "https://tweetyproject.org/mvn/"

# Retries for TRANSIENT transport failures only.
#
# Deliberately NOT `-Dmaven.wagon.http.retryHandler.count`: that property is read by
# the Wagon transport, and Maven 3.9 resolves through the *native* transport by
# default. Measured on 3.9.10 -- `mvn -X dependency:resolve` prints
# `Using transporter HttpTransporter`, so the Wagon knob is read by nobody and the
# flag would be a declaration with no reader (#1019 family). A loop around the
# subprocess is transport-agnostic and, unlike a CLI flag, can be tested offline.
MVN_TRANSIENT_RETRIES = 3
MVN_RETRY_BACKOFF_S = 5

# Substrings that mean "the bytes did not arrive", as opposed to "the coordinate does
# not exist". Lowercased before matching.
MVN_TRANSIENT_MARKERS = (
    "could not transfer artifact",
    "connection reset",
    "connection timed out",
    "read timed out",
    "transfer failed",
    "checksum validation failed",
)


def is_transient_failure(output: str) -> bool:
    """True when mvn failed to move bytes rather than failed to find a coordinate.

    Load-bearing subtlety, from the actual failure on CI run 32776186323: the log
    carried BOTH markers at once --

        Could not transfer artifact jspf:core:jar:1.0.2 from/to tweety-mvn ...
            Connection reset
        Could not find artifact jspf:core:jar:1.0.2 in central

    because Maven asks Central first (absent there, by design -- jspf:core, gurobi and
    isula are only on tweetyproject.org/mvn/) and only then the Tweety repository,
    which is where the socket dropped. A classifier that short-circuits on
    "could not find" would therefore call the real transport outage *permanent* and
    refuse to retry it -- the exact opposite of what is needed.

    So the rule is presence of a transport marker, never absence of the other one.
    The unbuildable-version trap (1.26 / 1.28) emits "Could not find artifact" with
    no transport marker, and is refused at once.
    """
    return any(m in output.lower() for m in MVN_TRANSIENT_MARKERS)


# The floor is compared to `count_module_jars`, which counts **Tweety module jars at
# the asked version** -- not the closure total. Calibrating it on the total was a
# field-and-its-reader mismatch: `60` was derived from closures of 155 / 149 / 76
# *jars*, then read against a number that is 48. It could never be cleared, and a
# healthy assembly raised "seulement 48 jar(s) de module ... moins que le plancher
# 60" with 153 jars sitting on disk (measured 2026-08-24, from the local .m2 in 2s,
# so no network was involved). The version filter that made the reader mean this
# arrived later than the calibration, and the comment was not moved with it.
#
# Counting modules rather than jars is also the *stabler* invariant, which is what
# made the old calibration so awkward. Third-party volume swings with exclusions --
# 105 jars with the full closure, 27 once `org.tweetyproject:web` is excluded (it
# transitively pulls the whole servlet/JSON stack) -- while the Tweety module count
# barely moves:
#
#     1.29, no exclusion   : 153 jars =  49 Tweety (48 modules + aggregator) + 104
#     1.31, no exclusion   : 155 jars =  50 Tweety + 105 third-party
#     1.31, `web` excluded :  76 jars =  49 Tweety +  27 third-party
#
# So a floor at 40 clears every supported shape with room to spare and still catches
# a copy that stopped early (a third of the modules missing). It is a backstop, not
# the main guard -- an interrupted run is caught by INCOMPLETE_MARKER below, which
# survives a kill that raises nothing to catch.
MIN_EXPECTED_JARS = 40

# Written before mvn runs, removed only once the floor check passes. A timeout or
# a Ctrl-C leaves it behind, so the *next* process refuses the wreckage instead of
# booting a JVM on a half-copied classpath. Cleaning up in an ``except`` clause
# would not cover the kill path, which is the likely one.
INCOMPLETE_MARKER = ".assembly-incomplete"

# Written next to the jars once the assembly clears the floor, and cached with
# them. It records what this assembly actually produced, so a cache restore can
# be compared to an EXACT count instead of to MIN_EXPECTED_JARS -- a floor of 60
# calibrated well under the real closure (149 jars measured on CI run
# 32768195554), which therefore accepts a restore that lost most of its jars.
ASSEMBLY_MANIFEST = ".assembly-manifest.json"


class AssemblyError(RuntimeError):
    """Assembly failed. The message names the actual cause, never a generic one."""


# ----------------------------------------------------------------- pure functions


def parse_pin_spec(spec: str) -> Dict[str, str]:
    """Parse ``"g:a:v,g2:a2:v2"`` into ``{"g:a": "v", "g2:a2": "v2"}``.

    Empty/blank input yields an empty mapping -- the common case, since a pin is
    only needed when the target version removes something we consume.

    Raises ValueError on a malformed entry rather than silently dropping it: a pin
    that quietly does not apply would reinstate exactly the capability loss it was
    added to prevent, and nothing downstream would notice.
    """
    pins: Dict[str, str] = {}
    for raw in (spec or "").split(","):
        entry = raw.strip()
        if not entry:
            continue
        parts = entry.split(":")
        if len(parts) != 3 or not all(p.strip() for p in parts):
            raise ValueError(
                f"pin invalide {entry!r}: attendu 'groupId:artifactId:version' "
                "(separes par des virgules)"
            )
        group, artifact, version = (p.strip() for p in parts)
        pins[f"{group}:{artifact}"] = version
    return pins


def parse_exclude_spec(spec: str) -> List[Tuple[str, str]]:
    """Parse ``"g:a,g2:a2"`` into ``[("g", "a"), ("g2", "a2")]``."""
    out: List[Tuple[str, str]] = []
    for raw in (spec or "").split(","):
        entry = raw.strip()
        if not entry:
            continue
        parts = entry.split(":")
        if len(parts) != 2 or not all(p.strip() for p in parts):
            raise ValueError(
                f"exclusion invalide {entry!r}: attendu 'groupId:artifactId'"
            )
        out.append((parts[0].strip(), parts[1].strip()))
    return out


def render_assembly_pom(
    version: str,
    pins: Optional[Dict[str, str]] = None,
    excludes: Optional[Sequence[Tuple[str, str]]] = None,
) -> str:
    """Build the throwaway POM whose dependency closure is the Tweety classpath.

    Pinned modules are emitted **before** the aggregator and as direct
    dependencies: Maven resolves version conflicts by nearest definition, so a
    direct ``bipolar:1.30`` wins over the ``bipolar:1.31`` that ``tweety-full:1.31``
    pulls transitively. Emitting them as ``<dependencyManagement>`` would work too,
    but a direct declaration also survives someone later reordering the file.

    Exclusions are attached to the aggregator, which is where the unwanted module
    is pulled from.
    """
    pins = pins or {}
    excludes = list(excludes or [])

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<project xmlns="http://maven.apache.org/POM/4.0.0"',
        '         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
        '         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 '
        'http://maven.apache.org/xsd/maven-4.0.0.xsd">',
        "  <modelVersion>4.0.0</modelVersion>",
        f"  <groupId>{TWEETY_GROUP}.assembly</groupId>",
        "  <artifactId>tweety-classpath</artifactId>",
        "  <version>1.0.0</version>",
        "  <packaging>pom</packaging>",
        # Declared explicitly rather than relied upon: Tweety's parent POM already
        # carries this repository, and three artifacts of the closure resolve from it
        # and nowhere else -- verified by reading `_remote.repositories` in the local
        # cache, which records `tweety-mvn` for jspf:core, gurobi and isula. Inheriting
        # it works today, but #1874 exists precisely because an upstream URL moved, and
        # inheritance makes our build depend on a file we do not control. (Merged from
        # po-2025's scripts/setup/tweety-maven.xml:43-48 in PR #1884.)
        "  <repositories>",
        "    <repository>",
        "      <id>tweety-mvn</id>",
        f"      <url>{TWEETY_MVN_REPO}</url>",
        "    </repository>",
        "  </repositories>",
        "  <dependencies>",
    ]

    # Pins first -- nearest definition wins, and reading order documents intent.
    for coord in sorted(pins):
        group, artifact = coord.split(":", 1)
        lines += [
            "    <!-- pin #1874: held back deliberately; see tweety_assembly.py -->",
            "    <dependency>",
            f"      <groupId>{group}</groupId>",
            f"      <artifactId>{artifact}</artifactId>",
            f"      <version>{pins[coord]}</version>",
            "    </dependency>",
        ]

    lines += [
        "    <dependency>",
        f"      <groupId>{TWEETY_GROUP}</groupId>",
        f"      <artifactId>{TWEETY_AGGREGATOR}</artifactId>",
        f"      <version>{version}</version>",
    ]
    if excludes:
        lines.append("      <exclusions>")
        for group, artifact in excludes:
            lines += [
                "        <exclusion>",
                f"          <groupId>{group}</groupId>",
                f"          <artifactId>{artifact}</artifactId>",
                "        </exclusion>",
            ]
        lines.append("      </exclusions>")
    lines += ["    </dependency>", "  </dependencies>", "</project>"]
    return "\n".join(lines) + "\n"


def pinned_versions_in_pom(pom_xml: str) -> Dict[str, str]:
    """Read back ``{"groupId:artifactId": version}`` from a rendered POM.

    Used by the tests as a *decoding* check: rendering and re-reading with an
    independent parser catches a template that produces plausible-looking XML
    which Maven would nonetheless resolve differently than intended.
    """
    root = ET.fromstring(pom_xml)
    ns = {"m": "http://maven.apache.org/POM/4.0.0"}
    out: Dict[str, str] = {}
    for dep in root.findall("./m:dependencies/m:dependency", ns):
        group = dep.findtext("m:groupId", default="", namespaces=ns)
        artifact = dep.findtext("m:artifactId", default="", namespaces=ns)
        version = dep.findtext("m:version", default="", namespaces=ns)
        out[f"{group}:{artifact}"] = version
    return out


def carries_tweety_classes(jar: Path) -> bool:
    """True when ``jar`` actually holds at least one ``org/tweetyproject/**.class``.

    The one question that matters about a candidate classpath entry: a jar the JVM
    cannot load a Tweety class from is not a classpath, whatever it is named. Every
    shape that has bitten this repository -- the 0-class thin aggregator, a 0-byte
    or truncated download keeping the ``-with-dependencies`` name, a directory of
    unrelated jars -- is invisible to a name check and obvious to this one.

    Unreadable or truncated -> False, never an exception: every caller is deciding
    whether to *keep* the candidate, and "cannot read it" is a no.
    """
    try:
        with zipfile.ZipFile(jar) as archive:
            return any(
                name.startswith("org/tweetyproject/") and name.endswith(".class")
                for name in archive.namelist()
            )
    except (zipfile.BadZipFile, OSError):
        return False


def count_module_jars(target_dir: Path, version: Optional[str] = None) -> int:
    """Number of jars present, ignoring the thin aggregator.

    ``dependency:copy-dependencies`` also deposits ``…tweety-full-<v>.jar``, which
    holds **zero** classes. Counting it would let a 1-jar directory look like a
    successful assembly -- the same shape #1880 fixed on the loader side.
    """
    jars = [
        jar
        for jar in target_dir.glob("*.jar")
        if f"{TWEETY_AGGREGATOR}-" not in jar.name
    ]
    if version is not None:
        # A directory left over from an earlier version is not a usable classpath
        # for the one being asked for. Without this, a machine that cached 1.28
        # serves 1.28 forever after the config moves to 1.31.
        jars = [j for j in jars if f"-{version}." in j.name or f"-{version}-" in j.name]
    return len(jars)


def is_already_assembled(
    target_dir: Path,
    minimum: int = MIN_EXPECTED_JARS,
    version: Optional[str] = None,
) -> bool:
    """True when the directory already holds a usable classpath (fat or assembled).

    Three ways this used to say yes when it should not, all of them silent:

    * a run interrupted mid-copy left module jars behind and the next call
      accepted them -- caught now by ``INCOMPLETE_MARKER``;
    * a zero-byte fat jar (an interrupted copy, a ``touch``, a failed restore)
      satisfied the fast path, and the size check inside ``download_file`` was
      never reached because this short-circuits first -- caught now by ``st_size``;
    * a jar of a *different* version satisfied it, so a machine holding 1.28 kept
      serving 1.28 after the config moved on -- caught now by ``version``. Serving
      the wrong version silently is the failure this module exists to prevent,
      inverted: 1.31 removes a family that 1.30 still has.

    ``version=None`` keeps the version-blind behaviour for callers that genuinely
    do not care; production passes it.
    """
    if not target_dir.is_dir():
        return False
    if (target_dir / INCOMPLETE_MARKER).exists():
        logger.warning(
            "%s porte %s: assemblage interrompu, refus de demarrer dessus.",
            target_dir,
            INCOMPLETE_MARKER,
        )
        return False
    for fat in target_dir.glob("*-with-dependencies.jar"):
        if version is not None and version not in fat.name:
            continue
        # `st_size > 0` was the earlier proxy for "usable". It rejects only the
        # 0-byte case; 1 KB of an interrupted 54 MB download passes it, and this
        # branch answers "nothing to do", so the assembly never runs and the JVM
        # then boots on an unusable classpath -- skips, not errors. Measured
        # 2026-08-24: a 1024-byte stub returned True here.
        if carries_tweety_classes(fat):
            return True
        logger.warning(
            "%s porte le nom d'un fat jar mais aucune classe Tweety (%d octet(s)): "
            "assemblage requis.",
            fat.name,
            fat.stat().st_size,
        )
    return count_module_jars(target_dir, version=version) >= minimum


# ------------------------------------------------------------------------- I/O


def maven_executable() -> Optional[str]:
    """Path to mvn, or None. Windows ships it as ``mvn.cmd``.

    ``MAVEN_HOME``/``M2_HOME`` are consulted too. The GitHub Windows runner images
    ship Maven 3.9.16 but their docs do not promise it is on ``PATH``, and a
    machine with Maven installed off-PATH would otherwise report "Maven
    introuvable" while Maven sits right there. Carried over from the ``_find_maven``
    written by po-2025 in #1884.
    """
    found = shutil.which("mvn") or shutil.which("mvn.cmd")
    if found:
        return found
    for var in ("MAVEN_HOME", "M2_HOME"):
        home = os.environ.get(var)
        if not home:
            continue
        for name in ("mvn.cmd", "mvn.bat", "mvn"):
            candidate = Path(home) / "bin" / name
            if candidate.is_file():
                return str(candidate)
    return None


def assemble(
    version: str,
    target_dir: Path,
    pins: Optional[Dict[str, str]] = None,
    excludes: Optional[Sequence[Tuple[str, str]]] = None,
    timeout: int = 900,
) -> int:
    """Copy the Tweety dependency closure into ``target_dir``. Returns the jar count.

    Raises :class:`AssemblyError` with the real cause -- never returns a thin
    success. A degraded classpath is worse than no classpath here: the JVM starts,
    every Tweety import fails, and the suite reports skips instead of an error.
    """
    mvn = maven_executable()
    if mvn is None:
        raise AssemblyError(
            "Maven introuvable dans le PATH. L'assemblage Tweety depuis Maven "
            "Central en depend (l'ancien canal fat-jar tweetyproject.org/builds/ "
            "rend 404). Installez Maven ou fournissez un "
            "*-with-dependencies.jar dans le repertoire des libs."
        )

    target_dir.mkdir(parents=True, exist_ok=True)
    pom_xml = render_assembly_pom(version, pins=pins, excludes=excludes)

    with tempfile.TemporaryDirectory(prefix="tweety-assembly-") as tmp:
        pom_path = Path(tmp) / "pom.xml"
        pom_path.write_text(pom_xml, encoding="utf-8")
        cmd = [
            mvn,
            "-q",
            "-B",
            "-f",
            str(pom_path),
            "dependency:copy-dependencies",
            f"-DoutputDirectory={target_dir.resolve()}",
            # Load-bearing: several Tweety groups publish the same artifactId
            # (e.g. `syntax`-flavoured modules across arg.* and logics.*). Without
            # the groupId prefix the copies overwrite each other and the classpath
            # silently loses modules.
            "-Dmdep.prependGroupId=true",
            "-Dmdep.useRepositoryLayout=false",
            "-Dmdep.overWriteReleases=false",
        ]
        logger.info(
            "Assemblage Tweety %s depuis Maven Central vers %s (pins=%s)",
            version,
            target_dir,
            pins or {},
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / INCOMPLETE_MARKER).write_text(
            "assemblage " + version + " en cours", encoding="utf-8"
        )
        attempts = 0
        while True:
            attempts += 1
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired as exc:
                raise AssemblyError(
                    f"Assemblage Tweety {version}: depassement de {timeout}s."
                ) from exc

            if proc.returncode == 0:
                break
            combined = (proc.stderr or "") + (proc.stdout or "")
            if attempts >= MVN_TRANSIENT_RETRIES or not is_transient_failure(combined):
                break
            logger.warning(
                "Assemblage Tweety %s: echec de transport (tentative %d/%d), "
                "nouvel essai dans %ds.",
                version,
                attempts,
                MVN_TRANSIENT_RETRIES,
                MVN_RETRY_BACKOFF_S,
            )
            time.sleep(MVN_RETRY_BACKOFF_S)

        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-25:]
            raise AssemblyError(
                f"Assemblage Tweety {version} echoue (mvn rc={proc.returncode}).\n"
                "Deux causes connues, a distinguer dans la sortie ci-dessous.\n"
                "  (1) Version non constructible: 1.26 et 1.28 publient un agregat "
                "sans ses modules. La sortie dit alors: Could not FIND artifact "
                "org.tweetyproject...\n"
                "  (2) Transport en panne sur tweetyproject.org/mvn/, seule source de "
                "jspf:core, gurobi et isula. La sortie dit alors: Could not TRANSFER "
                "artifact ... Connection reset -- observe sur le run 32776186323. "
                f"Tentatives effectuees: {attempts}. Le lire ici signifie "
                "que l hote est durablement indisponible, pas qu il a hoquete.\n"
                + "\n".join(tail)
            )

    count = count_module_jars(target_dir, version=version)
    if count < MIN_EXPECTED_JARS:
        raise AssemblyError(
            f"Assemblage Tweety {version}: seulement {count} jar(s) de module "
            f"copie(s), moins que le plancher {MIN_EXPECTED_JARS}. Un classpath "
            "partiel demarre la JVM et fait echouer chaque import -- refus "
            "explicite plutot qu'un succes mince."
        )
    (target_dir / ASSEMBLY_MANIFEST).write_text(
        json.dumps(
            {
                "version": version,
                "module_jars": count,
                "total_jars": len(list(target_dir.glob("*.jar"))),
            }
        ),
        encoding="utf-8",
    )
    (target_dir / INCOMPLETE_MARKER).unlink(missing_ok=True)
    logger.info("Assemblage Tweety %s: %d jars de module copies.", version, count)
    return count
