# This file makes the 'scripts/analysis' subdirectory a package, consistent with
# sibling scripts/* subpackages (core, apps, setup, narrative_reporting, ...).
# Removing the ambiguity around the top-level `scripts` package (issue #1293):
# an explicit __init__ here ensures `scripts.analysis.*` resolves deterministically
# against the repo-root `scripts/` package rather than a same-named shadow.
