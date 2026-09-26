# -*- coding: utf-8 -*-
"""JVM startup for the jpype_tweety workers (#2610).

Each worker used to build its own classpath from a single file,
``libs/tweety/org.tweetyproject.tweety-full-*-with-dependencies.jar``. That
fat JAR is no longer provisioned (#1874), and the eight copies of the lookup
went red together. The workers now start the JVM the way production does:
``jvm_setup.initialize_jvm`` builds the classpath from the jars present
(#2246, #2367) and picks the JDK. ``tests/`` holds no second builder.
"""

from argumentation_analysis.core.jvm_setup import initialize_jvm


def start_jvm() -> None:
    """Start the JVM through production, or raise. A running JVM is reused."""
    if not initialize_jvm():
        raise RuntimeError(
            "jvm_setup.initialize_jvm() returned False: the JVM did not start. "
            "Its log above names the cause (classpath, JDK, Tweety version)."
        )
