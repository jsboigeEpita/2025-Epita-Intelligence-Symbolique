"""#2106 — le provisioning des outils portables vise la racine ``libs/``.

Historique : ``scripts/utils/provision_tools.py`` provisionnait dans
``argumentation_analysis/libs/`` — racine parallèle de 621 Mo, 0 fichier
tracké, 0 lecteur (carte mesurée #2106, contre-vérifiée ai-01). Le repoint
aligne ce provisionneur sur le frère majoritaire
(``project_core/environment/tool_installer.py`` → ``project_root / "libs"``)
et sur ``jvm_setup`` (tous les lecteurs vérifiés résolvent la racine).

Né-rouge exécuté avant le repoint : ``tools_target_dir`` n'existait pas et
``NATIVE_LIBS_DIR`` résolvait vers ``libs/tweety/tweety/native`` (segment
``tweety`` doublé) au lieu des DLLs SAT trackées dans ``libs/native``.
"""

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]

SPEC = importlib.util.spec_from_file_location(
    "provision_tools", REPO / "scripts" / "utils" / "provision_tools.py"
)
assert SPEC and SPEC.loader
provision_tools = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(provision_tools)


def test_provisioning_target_is_repo_root_libs():
    target = provision_tools.tools_target_dir(REPO)
    assert target == REPO / "libs"
    assert target.name == "libs"
    # jamais la racine parallèle argumentation_analysis/libs/
    assert "argumentation_analysis" not in target.parts


def test_paths_module_agrees_on_the_same_libs_root():
    from argumentation_analysis.paths import LIBS_DIR, NATIVE_LIBS_DIR

    # LIBS_DIR (nom historique) vaut libs/tweety : son parent doit être la
    # cible du provisioning.
    assert LIBS_DIR.parent == provision_tools.tools_target_dir(REPO)
    # NATIVE_LIBS_DIR doit viser les DLLs SAT trackées dans libs/native,
    # pas le segment tweety doublé ni libs/tweety/native (inexistant).
    assert NATIVE_LIBS_DIR == REPO / "libs" / "native"


def test_tracked_native_dlls_live_at_the_declared_dir():
    from argumentation_analysis.paths import NATIVE_LIBS_DIR

    assert (NATIVE_LIBS_DIR / "picosat.dll").is_file()


def test_settings_native_dir_matches_the_same_root():
    from argumentation_analysis.config.settings import settings

    assert settings.jvm.native_libs_dir == Path("libs") / "native"
