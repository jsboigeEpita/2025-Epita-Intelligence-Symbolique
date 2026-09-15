"""#2248 — `utils/update_encrypted_config.py`: message honnête + chaîne producteur vivante.

Deux propriétés, mesurées sur `a6041e00` :

1. **Le garde nomme la variable qu'il teste réellement** (né-rouge). Le garde interne
   testait `settings.encryption_key` (alias `ENCRYPTION_KEY`, `config/settings.py`) tout
   en annonçant `TEXT_CONFIG_PASSPHRASE` — une variable **présente** dans le `.env`
   canonique. L'opérateur suivant le message ne pouvait pas réparer la panne.
2. **Le chemin d'entrée n'est PAS mort** : `restore_config.py` écrit exactement le chemin
   que `update_encrypted_config.py` lit, et son absence du dépôt est **voulue**
   (gitignoré — le fichier porte du contenu dataset en clair). Ces deux tests épinglent la
   mesure : un futur « nettoyage » du chemin qui *paraît* mort rougit ici.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
TOOL = REPO_ROOT / "argumentation_analysis" / "utils" / "update_encrypted_config.py"
PRODUCER = REPO_ROOT / "argumentation_analysis" / "utils" / "restore_config.py"
GITIGNORE = REPO_ROOT / "argumentation_analysis" / ".gitignore"

# Le chemin d'entrée, en composants — partagé producteur/consommateur.
INPUT_PATH_PARTS = (
    "argumentation_analysis",
    "utils",
    "extract_repair",
    "docs",
    "extract_sources_updated.json",
)


def _tool_source() -> str:
    return TOOL.read_text(encoding="utf-8")


def _key_guard_message() -> str:
    """Le message du garde qui teste `encryption_key` (et non la passphrase)."""
    source = _tool_source()
    match = re.search(
        r'print\(\s*f?"[^"]*chiffrement[^"]*disponible[^"]*"',
        source,
        flags=re.IGNORECASE,
    )
    assert match is not None, (
        "le garde 'clé de chiffrement n'est pas disponible' est introuvable — "
        "si le garde a été reformulé, mettre ce test à jour AVEC la mesure"
    )
    return match.group(0)


def test_guard_message_names_the_variable_actually_tested():
    """Né-rouge : le message doit nommer l'alias réel de `settings.encryption_key`.

    L'alias est DÉRIVÉ du modèle (pas recopié) : un renommage de la clé fait rougir ce
    test au lieu de laisser un message périmé passer.
    """
    from argumentation_analysis.config.settings import settings

    alias = type(settings).model_fields["encryption_key"].alias
    assert alias, "`encryption_key` n'a plus d'alias de variable d'environnement"

    message = _key_guard_message()
    assert alias in message, (
        f"le garde teste `encryption_key` (alias {alias!r}) mais son message nomme "
        f"une autre variable : {message!r}"
    )
    assert "TEXT_CONFIG_PASSPHRASE" not in message, (
        "le garde nomme TEXT_CONFIG_PASSPHRASE, qui est l'alias de "
        "`settings.passphrase` — pas de la clé testée ici"
    )


def test_input_path_is_the_restore_config_producer_output():
    """Épingle la chaîne : le chemin lu par l'outil est écrit par `restore_config.py`.

    Sans ce test, un futur lecteur conclut « chemin mort » (fichier absent du dépôt) et
    retire le seul producteur/consommateur de la chaîne — la leçon #2120 appliquée dans
    l'autre sens : mesurer les DEUX bouts avant de trancher vivant/mort.
    """
    tool_source = _tool_source()
    producer_source = PRODUCER.read_text(encoding="utf-8")
    for part in INPUT_PATH_PARTS:
        assert f'"{part}"' in tool_source, f"composant {part!r} absent du consommateur"
        assert (
            f'"{part}"' in producer_source
        ), f"composant {part!r} absent du producteur"


def test_absent_input_is_explained_by_the_gitignore():
    """L'absence du fichier dans le dépôt est VOULUE : il est gitignoré (contenu en clair)."""
    if not GITIGNORE.exists():
        pytest.skip("gitignore de argumentation_analysis/ absent de cet arbre")
    ignored = {
        line.strip()
        for line in GITIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    assert "extract_repair/docs/extract_sources_updated.json" in ignored or (
        "extract_sources_updated.json" in ignored
    ), (
        "le fichier d'entrée n'est plus gitignoré — vérifier s'il peut désormais entrer "
        "dans le dépôt (il porte du contenu dataset en clair) avant de relâcher ce test"
    )
