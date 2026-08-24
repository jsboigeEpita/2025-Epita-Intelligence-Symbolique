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

import logging
import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

MAVEN_CENTRAL = "https://repo1.maven.org/maven2"
TWEETY_GROUP = "org.tweetyproject"
TWEETY_AGGREGATOR = "tweety-full"
# Non-Central artifacts of the closure (jspf:core, gurobi, isula) are served only
# from here. Alive (200) as of #1874, unlike the removed /builds/ fat-jar channel.
TWEETY_MVN_REPO = "https://tweetyproject.org/mvn/"

# Measured on 1.31 (2026-08-24), so the floor is calibrated on real values rather
# than a guess: the full closure is **155** jars (50 Tweety + 105 third-party), and
# excluding `org.tweetyproject:web` leaves **76** (49 Tweety + 27 third-party) --
# `web` is what transitively pulls the whole servlet/JSON stack, and dropping it
# costs exactly one Tweety module. A probe exercising the bipolar frameworks was
# verified identical on both. Anything far below 76 means the copy stopped early.
MIN_EXPECTED_JARS = 40


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


def count_module_jars(target_dir: Path) -> int:
    """Number of jars present, ignoring the thin aggregator.

    ``dependency:copy-dependencies`` also deposits ``…tweety-full-<v>.jar``, which
    holds **zero** classes. Counting it would let a 1-jar directory look like a
    successful assembly -- the same shape #1880 fixed on the loader side.
    """
    return len(
        [
            jar
            for jar in target_dir.glob("*.jar")
            if f"{TWEETY_AGGREGATOR}-" not in jar.name
        ]
    )


def is_already_assembled(target_dir: Path, minimum: int = MIN_EXPECTED_JARS) -> bool:
    """True when the directory already holds a usable classpath (fat or assembled)."""
    if not target_dir.is_dir():
        return False
    if any(target_dir.glob("*-with-dependencies.jar")):
        return True
    return count_module_jars(target_dir) >= minimum


# ------------------------------------------------------------------------- I/O


def maven_executable() -> Optional[str]:
    """Path to mvn, or None. Windows ships it as ``mvn.cmd``."""
    return shutil.which("mvn") or shutil.which("mvn.cmd")


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
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "MAVEN_OPTS": os.environ.get("MAVEN_OPTS", "")},
            )
        except subprocess.TimeoutExpired as exc:
            raise AssemblyError(
                f"Assemblage Tweety {version}: depassement de {timeout}s."
            ) from exc

        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-25:]
            raise AssemblyError(
                f"Assemblage Tweety {version} echoue (mvn rc={proc.returncode}).\n"
                "Rappel #1874: 1.26 et 1.28 ne sont PAS constructibles depuis "
                "Central (agregat publie, modules absents) -- verifier la version "
                "avant de suspecter le reseau.\n" + "\n".join(tail)
            )

    count = count_module_jars(target_dir)
    if count < MIN_EXPECTED_JARS:
        raise AssemblyError(
            f"Assemblage Tweety {version}: seulement {count} jar(s) de module "
            f"copie(s), moins que le plancher {MIN_EXPECTED_JARS}. Un classpath "
            "partiel demarre la JVM et fait echouer chaque import -- refus "
            "explicite plutot qu'un succes mince."
        )
    logger.info("Assemblage Tweety %s: %d jars de module copies.", version, count)
    return count
