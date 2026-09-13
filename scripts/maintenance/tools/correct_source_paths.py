import argumentation_analysis.core.environment
import hashlib
import json
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def _fingerprint(value: str) -> str:
    """sha256[:16] of a config value — the only form a migration target takes here.

    Rule 7 (#2168/#2187): a label mapping 1:1 to one encrypted document never
    enters a tracked file, and this repo is GitHub-indexed. A migration script
    that enumerates the records it targets publishes the census the encryption
    protects — "the script needs the label to match" is not a license. Each
    target is therefore keyed by the digest of the value its config entry
    carries, and the predicate is exactly the one it replaced. Stated rather
    than hidden: a descriptive label is dictionary-recoverable from its digest,
    so this removes PUBLICATION, not knowledge.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


# Targets keyed by digest, never by the label. The first map is keyed on the
# ``source_name`` two entries carried; the second on the ``source_id`` a third
# carries. Priority follows the original if/elif chain: a name match wins.
_NEW_PATH_BY_SOURCE_NAME = {
    "51fa94b1b628bc4a": "discours_attal_20240130.txt",
    "eafce0b03af0ab29": "rapport_ia_2024.txt",
}
_NEW_PATH_BY_SOURCE_ID = {
    "45b64451b8432c0f": "https://www.gutenberg.org/files/1657/1657-0.txt",
}

# Définir le chemin du fichier d'entrée
input_config_path = Path("_temp/config_source_removed.json")
# Définir le chemin du fichier de sortie
output_config_path = Path("_temp/config_paths_corrected_v2.json")

logging.info(f"Lecture du fichier d'entrée : {input_config_path}")
# Charger les données depuis input_config_path
try:
    with open(input_config_path, "r", encoding="utf-8") as f:
        sources_data = json.load(f)
except FileNotFoundError:
    logging.error(f"Le fichier d'entrée {input_config_path} n'a pas été trouvé.")
    exit()
except json.JSONDecodeError:
    logging.error(f"Le fichier d'entrée {input_config_path} n'est pas un JSON valide.")
    exit()

# Itérer sur chaque source dans les données chargées
for source in sources_data:
    source_name = source.get("source_name")
    source_id = source.get("source_id")
    logging.info(f"Traitement de la source ID: {source_id}, Nom: {source_name}")

    modified = False
    old_path = source.get("path", "N/A")

    new_path = _NEW_PATH_BY_SOURCE_NAME.get(_fingerprint(source_name or ""))
    if new_path is None:
        new_path = _NEW_PATH_BY_SOURCE_ID.get(_fingerprint(source_id or ""))

    if new_path is not None and source.get("path") != new_path:
        logging.info(f"Modification de la source ID: {source_id}, Nom: {source_name}")
        logging.info(f"  Ancien chemin: {old_path}")
        logging.info(f"  Nouveau chemin: {new_path}")
        source["path"] = new_path
        modified = True

    if not modified:
        logging.info(
            f"Aucune modification pour la source ID: {source_id}, Nom: {source_name}"
        )

# Sauvegarder la liste mise à jour des sources dans output_config_path
try:
    with open(output_config_path, "w", encoding="utf-8") as f:
        json.dump(sources_data, f, indent=2, ensure_ascii=False)
    logging.info(f"Modifications sauvegardées avec succès dans {output_config_path}")
except IOError:
    logging.error(
        f"Impossible d'écrire dans le fichier de sortie {output_config_path}."
    )
