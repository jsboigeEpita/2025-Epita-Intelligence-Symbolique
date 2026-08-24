"""Print the cache key for the Java toolchain (#1874).

Derived from settings rather than duplicated in the workflow. A second copy of
the version in YAML is one more declaration to drift out of sync, and #1874 is
precisely a story about a coordinate that moved upstream while everything
downstream kept quoting the old one.

The key encodes what the cached bytes depend on: the Tweety version, the pins,
the exclusions, and the portable JDK coordinates -- `portable_jdk/` is cached
alongside `libs/tweety/`. Change any of them and the key changes, the cache
misses, and the closure is rebuilt from Maven Central with no human step and
nothing to republish.

This is deliberately NOT keyed on a hosted artifact. A pinned upstream artifact
is exactly what died in #1874; a coordinate-keyed cache is self-healing.
"""

import hashlib
import sys

from argumentation_analysis.config.settings import settings


def cache_key() -> str:
    j = settings.jvm
    material = "|".join(
        [
            j.tweety_version,
            j.tweety_pinned_modules or "",
            j.tweety_excluded_modules or "",
            j.jdk_version,
            j.jdk_build,
        ]
    )
    # The versions stay legible so a human reading the cache list can tell
    # entries apart; the digest carries the pins, which contain ":" and "," --
    # characters cache keys handle poorly.
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]
    return f"tweety{j.tweety_version}-jdk{j.jdk_version}+{j.jdk_build}-{digest}"


if __name__ == "__main__":
    sys.stdout.write(cache_key())
