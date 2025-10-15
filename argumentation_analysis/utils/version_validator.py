from importlib import metadata
from packaging.version import parse

MIN_SK_VERSION = "1.3.0"


def validate_semantic_kernel_version():
    """
    Vérifie que la version de semantic-kernel installée est compatible.

    Lève une ImportError si la version n'est pas conforme aux exigences
    minimales du projet pour éviter l'utilisation de mocks ou de code de
    compatibilité pour des versions obsolètes.
    """
    try:
        installed_version_str = metadata.version("semantic-kernel")
        installed_version = parse(installed_version_str)
        min_version = parse(MIN_SK_VERSION)

        if installed_version < min_version:
            raise ImportError(
                f"Version de semantic-kernel ({installed_version_str}) est obsolète. "
                f"Ce projet requiert au minimum la version {MIN_SK_VERSION}. "
                "Veuillez mettre à jour votre environnement."
            )
        # print(f"Validation réussie: semantic-kernel version {installed_version_str} est compatible (>= {MIN_SK_VERSION}).")

    except metadata.PackageNotFoundError:
        raise ImportError(
            "Le package 'semantic-kernel' n'est pas installé. "
            "Veuillez l'installer dans votre environnement."
        )


# Exécution de la validation à l'import du module
# validate_semantic_kernel_version()
