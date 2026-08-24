"""#1874: reassemble the Tweety classpath from Maven Central via copy-dependencies.

tweetyproject.org removed /builds/ (the fat-jar host), so the JVM classpath must be
rebuilt from Maven Central. This drives the committed POM (scripts/setup/tweety-maven.xml)
with `mvn dependency:copy-dependencies`, then drops the jars into the production lib dir
(default ``libs/tweety/``, read by jvm_setup.initialize_jvm via settings.jvm.tweety_libs_dir).

Version source of truth is the POM (properties ``tweety.version`` = 1.31 global,
``bipolar.version`` = 1.30 pinned for arg:bipolar) — this script does NOT hardcode them.
It reads them back from the POM only to echo a summary, never to drive the build (Maven
consumes them from the POM itself).

Layout note: the assembly has NO ``*-with-dependencies.jar``, so jvm_setup._build_tweety_classpath
loads ALL jars in the dir (#1874 Piège 2 fix). The script therefore removes any existing
top-level ``*.jar`` in the output (the old fat jars and stale module jars) before
assembling, so the assembly-mode is actually active. Sub-directories (native/, tweety/)
and their contents are preserved.

Prerequisites: Maven 3.9.x and a JDK 17 (JAVA_HOME). The native solver binaries
(minisat/picosat/lingeling .dll/.so) ride along inside the sat/adf jars, so no extra step.
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
POM_PATH = PROJECT_ROOT / "scripts" / "setup" / "tweety-maven.xml"
DEFAULT_OUTPUT = PROJECT_ROOT / "libs" / "tweety"


def _parse_pom_versions(pom_path: Path) -> dict:
    tree = ET.parse(pom_path)
    props = tree.getroot().find(".//{http://maven.apache.org/POM/4.0.0}properties")
    if props is None:
        raise RuntimeError(f"No <properties> in {pom_path}")
    versions = {child.tag.split("}")[-1]: child.text for child in props}
    return versions


def _find_maven(explicit: str | None) -> str:
    if explicit:
        return explicit
    env_home = os.environ.get("MAVEN_HOME") or os.environ.get("M2_HOME")
    if env_home:
        for name in ("mvn", "mvn.cmd"):
            cand = Path(env_home) / "bin" / name
            if cand.exists():
                return str(cand)
    which = shutil.which("mvn") or shutil.which("mvn.cmd")
    if which:
        return which
    raise RuntimeError(
        "Maven not found. Set MAVEN_HOME/M2_HOME or pass --maven, or use a Maven "
        "binary (e.g. apache-maven-3.9.10) downloaded to a local path."
    )


def _clean_jars(output: Path, dry_run: bool) -> int:
    removed = 0
    if not output.exists():
        return 0
    for jar in output.glob("*.jar"):
        if dry_run:
            logger.info("would remove %s", jar.name)
        else:
            jar.unlink()
        removed += 1
    if removed:
        logger.info("removed %d existing jar(s) from %s", removed, output)
    return removed


def _verify(output: Path, versions: dict) -> None:
    tweety_ver = versions["tweety.version"]
    bipolar_ver = versions["bipolar.version"]
    # The 1.30 bipolar (evidential-capable) jar must be present, and its 1.31 twin absent.
    bipolar_130 = output / f"org.tweetyproject.arg.bipolar-{bipolar_ver}.jar"
    bipolar_131 = output / f"org.tweetyproject.arg.bipolar-{tweety_ver}.jar"
    evidential_cls = (
        "org/tweetyproject/arg/bipolar/syntax/EvidentialArgumentationFramework.class"
    )
    grounded = (
        "org/tweetyproject/arg/bipolar/reasoner/evidential/GroundedReasoner.class"
    )

    logger.info("expected bipolar %s, aggregator %s", bipolar_ver, tweety_ver)
    if not bipolar_130.exists():
        logger.warning("MISSING pinned jar %s", bipolar_130.name)
    if bipolar_131.exists():
        logger.warning(
            "pinned-override FAILED: %s is present; evidential could be gone",
            bipolar_131.name,
        )

    # Verify the evidential classes are actually inside the bipolar jar (the discriminator).
    if bipolar_130.exists():
        import zipfile

        with zipfile.ZipFile(bipolar_130) as zf:
            names = set(zf.namelist())
        if evidential_cls in names and grounded in names:
            logger.info("evidential classes present in %s (OK)", bipolar_130.name)
        else:
            logger.warning("evidential classes NOT found in %s", bipolar_130.name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--maven", help="Path to mvn (default: MAVEN_HOME/M2_HOME/PATH)."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Target dir for assembled jars (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print, do not run.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    versions = _parse_pom_versions(POM_PATH)
    logger.info(
        "POM versions: tweety=%s bipolar=%s",
        versions["tweety.version"],
        versions["bipolar.version"],
    )

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    _clean_jars(output, args.dry_run)

    if args.dry_run:
        logger.info("dry-run: would run mvn copy-dependencies into %s", output)
        return 0

    mvn = _find_maven(args.maven)
    cmd = [
        mvn,
        "-f",
        str(POM_PATH),
        "dependency:copy-dependencies",
        f"-DoutputDirectory={output}",
        "-Dmdep.prependGroupId=true",
        "-DincludeScope=runtime",
        "-q",
    ]
    logger.info("running: %s", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.error("mvn failed (rc=%d):\n%s", proc.returncode, proc.stderr)
        return proc.returncode

    jars = sorted(output.glob("*.jar"))
    logger.info("assembled %d jar(s) into %s", len(jars), output)
    _verify(output, versions)
    return 0


if __name__ == "__main__":
    sys.exit(main())
