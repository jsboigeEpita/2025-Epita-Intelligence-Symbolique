"""
Chargement de la taxonomie des sophismes Argumentum.

La taxonomie est vendorée dans ``argumentation_analysis/data/`` et sa provenance
est épinglée dans ``argumentum_taxonomy_provenance.json``.
``get_taxonomy_path()`` rend ce fichier. S'il manque, il le télécharge depuis le
dépôt Argumentum. ``validate_taxonomy_file()`` en vérifie l'en-tête, et
``TaxonomyLoader`` le lit en une liste de dictionnaires.

Le module n'a pas de mode simulé (#2346). Il en avait un, commandé par un global
``USE_MOCK`` que rien n'écrivait : ce mode rendait un échantillon de cinq
sophismes inventés, et ``TaxonomyLoader`` y retombait en silence quand la
lecture du vrai fichier échouait. Un test qui veut une autre taxonomie remplace
``get_taxonomy_path``.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from argumentation_analysis.paths import DATA_DIR

logger = logging.getLogger(__name__)

# URL de la taxonomie des sophismes, pour le téléchargement si le fichier manque
TAXONOMY_URL = "https://raw.githubusercontent.com/ArgumentumGames/Argumentum/master/Cards/Fallacies/Argumentum%20Fallacies%20-%20Taxonomy.csv"
# La copie vendorée
TAXONOMY_FILE = DATA_DIR / "argumentum_fallacies_taxonomy.csv"


def get_taxonomy_path() -> Path:
    """
    Le chemin du fichier de taxonomie des sophismes.

    Rend la copie vendorée si elle existe. Sinon, la télécharge depuis
    ``TAXONOMY_URL`` (bibliothèque ``requests``) et la rend.

    Returns:
        Path: Chemin vers le fichier de taxonomie

    Raises:
        ImportError: ``requests`` n'est pas installé et le fichier manque
        Exception: Le téléchargement a échoué
    """
    if TAXONOMY_FILE.exists():
        logger.info(
            f"Fichier de taxonomie par défaut trouvé localement: {TAXONOMY_FILE}"
        )
        return TAXONOMY_FILE

    # Créer le dossier data s'il n'existe pas
    DATA_DIR.mkdir(exist_ok=True)

    # Téléchargement réel de la taxonomie
    logger.info(f"Téléchargement de la taxonomie depuis {TAXONOMY_URL}")
    try:
        import requests

        response = requests.get(TAXONOMY_URL)
        response.raise_for_status()

        with open(TAXONOMY_FILE, "wb") as f:
            f.write(response.content)

        logger.info(f"Taxonomie téléchargée avec succès: {TAXONOMY_FILE}")
        return TAXONOMY_FILE

    except ImportError:
        logger.error(
            "La bibliothèque 'requests' n'est pas installée. Installation requise pour le téléchargement."
        )
        raise ImportError("Installation manquante: pip install requests")
    except Exception as e:
        logger.error(f"Erreur lors du téléchargement de la taxonomie: {e}")
        raise


# #2141 temps 2: the wide-net funnel is a parameter, not a silent assumption.
# What makes the master/slave funnel real is its *taxonomy source*: without one
# the navigator resolves no candidate and every call degenerates to a one-shot
# full-taxonomy prompt. This selector decides whether a call site hands the
# funnel its taxonomy. The default reproduces the behaviour that predates the
# parameter, so selecting "funnel" is a deliberate, measured opt-in — it turns
# one call into a wide-net plus up to MAX_BRANCHES descents.
TAXONOMY_REGIME_ENV = "TAXONOMY_REGIME"
TAXONOMY_REGIMES = ("one_shot", "funnel")
DEFAULT_TAXONOMY_REGIME = "one_shot"


def get_taxonomy_regime() -> str:
    """The retained fallacy-analysis regime, from ``TAXONOMY_REGIME``.

    ``"one_shot"`` (default) — the call site hands the funnel no taxonomy, so
    the run is a single full-taxonomy prompt.
    ``"funnel"`` — the call site hands the funnel the resolved taxonomy, so the
    wide-net candidate selection and its parallel descent actually run.

    An unrecognised value is *ignored, not honoured*: it warns naming the
    variable and the accepted values, then falls back to the default. Silently
    degrading an unknown selector would make a typo look like a working config.
    """
    raw = os.environ.get(TAXONOMY_REGIME_ENV, "").strip().lower()
    if not raw:
        return DEFAULT_TAXONOMY_REGIME
    if raw not in TAXONOMY_REGIMES:
        logger.warning(
            "%s=%r is not a known regime (accepted: %s) — falling back to %r",
            TAXONOMY_REGIME_ENV,
            raw,
            ", ".join(TAXONOMY_REGIMES),
            DEFAULT_TAXONOMY_REGIME,
        )
        return DEFAULT_TAXONOMY_REGIME
    return raw


def get_taxonomy_source_for_regime(regime: Optional[str] = None) -> Optional[str]:
    """The taxonomy path a call site should hand the funnel, or ``None``.

    ``one_shot`` yields ``None`` — the call site passes no source, exactly as it
    did before this parameter existed. ``funnel`` yields the resolved path.
    Call sites share this one function rather than each re-deriving the rule,
    so the two sites cannot drift apart.
    """
    if regime is None:
        regime = get_taxonomy_regime()
    if regime != "funnel":
        return None
    return str(get_taxonomy_path())


def validate_taxonomy_file():
    """
    Valide le fichier de taxonomie des sophismes.

    - Vérifie que le fichier existe et n'est pas vide
    - Valide la présence des colonnes requises dans l'en-tête
    - Vérifie qu'il y a au moins une ligne de données

    Returns:
        bool: True si le fichier est valide, False sinon
    """
    try:
        taxonomy_path = get_taxonomy_path()

        if os.path.getsize(taxonomy_path) == 0:
            logger.error("Le fichier de taxonomie est vide")
            return False

        with open(taxonomy_path, "r", encoding="utf-8") as f:
            header = f.readline().strip()
            required_columns = ["PK", "nom_vulgarisé", "text_fr"]
            if not all(col in header for col in required_columns):
                logger.error(f"Format d'en-tête incorrect: {header}")
                logger.error(
                    f"Colonnes requises manquantes: {[col for col in required_columns if col not in header]}"
                )
                return False

            data_line = f.readline().strip()
            if not data_line:
                logger.error("Aucune donnée trouvée dans le fichier")
                return False

        logger.info("Validation du fichier de taxonomie réussie")
        return True

    except Exception as e:
        logger.error(f"Erreur lors de la validation du fichier de taxonomie: {e}")
        return False


class TaxonomyLoader:
    """
    Lit la taxonomie des sophismes en une liste de dictionnaires.

    Attributs:
        taxonomy_path (Path): Chemin vers le fichier de taxonomie

    Méthodes:
        load_taxonomy(): Charge la taxonomie des sophismes
    """

    def __init__(self):
        """
        Initialise le chargeur de taxonomie.

        Le chemin du fichier sera déterminé par get_taxonomy_path().
        """
        self.taxonomy_path = None

    def load_taxonomy(self):
        """
        Charge la taxonomie des sophismes depuis le fichier que rend
        ``get_taxonomy_path()``.

        Returns:
            list: Une entrée par ligne non vide du fichier, clés et valeurs
            vides ignorées

        Raises:
            OSError: Le fichier ne se lit pas. L'erreur remonte : une taxonomie
            inventée à sa place passerait pour la vraie (#2346).
        """
        import csv

        logger.info("Chargement de la taxonomie depuis le fichier")
        taxonomy_path = get_taxonomy_path()
        entries = []

        with open(taxonomy_path, "r", encoding="utf-8") as f:
            # Détecter le délimiteur automatiquement
            sample = f.read(1024)
            f.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter

            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                # Normaliser les clés des colonnes
                normalized_row = {}
                for key, value in row.items():
                    if key and value:  # Ignorer les colonnes/valeurs vides
                        normalized_row[key.strip()] = value.strip()

                if normalized_row:  # Seulement ajouter les lignes non-vides
                    entries.append(normalized_row)

        logger.info(f"Taxonomie chargée avec succès: {len(entries)} entrées")
        return entries


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # Test du module
    try:
        taxonomy_path = get_taxonomy_path()
        print(f"Chemin vers la taxonomie: {taxonomy_path}")

        is_valid = validate_taxonomy_file()
        print(f"Fichier valide: {is_valid}")
    except Exception as e:
        print(f"Erreur: {e}")
