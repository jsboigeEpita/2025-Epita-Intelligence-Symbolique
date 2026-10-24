"""
Chargement de la taxonomie des sophismes Argumentum.

La taxonomie est vendorée dans ``argumentation_analysis/data/`` et sa provenance
est épinglée dans ``argumentum_taxonomy_provenance.json``.
``get_taxonomy_path()`` rend ce fichier. S'il manque, il le télécharge depuis le
dépôt Argumentum, au commit épinglé. ``validate_taxonomy_file()`` en vérifie l'en-tête, et
``TaxonomyLoader`` le lit en une liste de dictionnaires.

Le module n'a pas de mode simulé (#2346). Il en avait un, commandé par un global
``USE_MOCK`` que rien n'écrivait : ce mode rendait un échantillon de cinq
sophismes inventés, et ``TaxonomyLoader`` y retombait en silence quand la
lecture du vrai fichier échouait. Un test qui veut une autre taxonomie remplace
``get_taxonomy_path``.
"""

import codecs
import csv
import hashlib
import json
import os
import logging
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote
from typing import Dict, List, Optional
from argumentation_analysis.paths import DATA_DIR

logger = logging.getLogger(__name__)

# La copie vendorée
TAXONOMY_FILE = DATA_DIR / "argumentum_fallacies_taxonomy.csv"
# Le commit amont, le chemin et l'empreinte de la copie vendorée
PROVENANCE_FILE = DATA_DIR / "argumentum_taxonomy_provenance.json"
# Borne du téléchargement, en secondes
DOWNLOAD_TIMEOUT = 60


def pinned_taxonomy_source():
    """L'URL du fichier au commit amont épinglé, et l'empreinte attendue.

    ``(url, sha1)``. ``sha1`` est celle du contenu sans BOM, la forme sous
    laquelle la copie vendorée est stockée (``upstream_content_sha1_no_bom``).
    """
    pin = json.loads(PROVENANCE_FILE.read_text(encoding="utf-8"))["fallacies"]
    url = "https://raw.githubusercontent.com/{}/{}/{}".format(
        pin["upstream_repo"], pin["upstream_commit"], quote(pin["upstream_path"])
    )
    return url, pin["upstream_content_sha1_no_bom"]


def get_taxonomy_path() -> Path:
    """
    Le chemin du fichier de taxonomie des sophismes.

    Rend la copie vendorée si elle existe. Sinon, la télécharge au commit
    amont épinglé dans ``PROVENANCE_FILE`` (bibliothèque ``requests``),
    retire le BOM, vérifie que le contenu a l'empreinte de la provenance,
    puis l'écrit et la rend. Un contenu d'une autre empreinte n'est pas
    écrit (#2346) : ``master`` amont évolue, et la copie écrite doit être
    celle que garde ``tests/unit/scripts/test_argumentum_taxonomy_integrity.py``.

    Returns:
        Path: Chemin vers le fichier de taxonomie

    Raises:
        ImportError: ``requests`` n'est pas installé et le fichier manque
        ValueError: Le contenu téléchargé n'a pas l'empreinte épinglée
        Exception: Le téléchargement a échoué
    """
    if TAXONOMY_FILE.exists():
        logger.info(
            f"Fichier de taxonomie par défaut trouvé localement: {TAXONOMY_FILE}"
        )
        return TAXONOMY_FILE

    url, expected_sha1 = pinned_taxonomy_source()
    logger.info(f"Téléchargement de la taxonomie depuis {url}")
    try:
        import requests

        response = requests.get(url, timeout=DOWNLOAD_TIMEOUT)
        response.raise_for_status()

        content = response.content
        if content.startswith(codecs.BOM_UTF8):
            content = content[len(codecs.BOM_UTF8) :]
        sha1 = hashlib.sha1(content).hexdigest()
        if sha1 != expected_sha1:
            raise ValueError(
                f"Taxonomie téléchargée depuis {url} : empreinte {sha1}, "
                f"la provenance épingle {expected_sha1}. Fichier non écrit."
            )

        # Écrit à côté puis remplace : une écriture interrompue ne laisse pas
        # un fichier tronqué que le prochain appel prendrait pour la copie.
        partial = TAXONOMY_FILE.with_name(TAXONOMY_FILE.name + ".part")
        try:
            partial.write_bytes(content)
            os.replace(partial, TAXONOMY_FILE)
        finally:
            partial.unlink(missing_ok=True)

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


# --- #3224 — a fallacy label that names the taxonomy branch -----------------
#
# The Act III prompt rebuilt from the R1110 state carried the detection as
# « Effet cigogne (famille Erreur de raisonnement) » — the leaf and the root,
# but not the branch « Causalité douteuse » (4.1) that names the category the
# Act I question asked about, so the reader could answer the causal half "no"
# while the evidence held a causal detection. One father for the three label
# sites (act3_conclusion_plugin, act2_narrative_plugin ×2) and for the reading
# check that catches the contradiction: resolve the stored dotted path against
# the vendored taxonomy and render the node NAMES — the dotted address itself
# still never enters the evidence (#2031).


@lru_cache(maxsize=4)
def _taxonomy_node_names(csv_path: str) -> Dict[str, str]:
    """``path`` -> the node's French name (``text_fr``), read once per file.

    Keyed by the resolved file path, so a test swapping ``get_taxonomy_path``
    to another file reads that file, not a stale cache. The returned dict is
    shared through the cache — callers must not mutate it.
    """
    index: Dict[str, str] = {}
    try:
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                path = (row.get("path") or "").strip()
                name = (row.get("text_fr") or "").strip()
                if path and name:
                    index[path] = name
    except OSError as exc:
        logger.debug("taxonomy node names unreadable at %s: %s", csv_path, exc)
    return index


#: A stored taxonomy path is dotted and numeric; the synthesizer also builds
#: ``fallacy/<family>/<type>`` strings (deep_synthesis_agent) which are not
#: addresses in this file.
_DOTTED_PATH_RE = re.compile(r"\d+(?:\.\d+)*")


def taxonomy_chain(taxonomy_path: str) -> Optional[List[str]]:
    """The node NAMES a detection sits under: root, branch, leaf.

    The chain is capped at three levels — root (first segment), branch
    (second), leaf (the full path); a deeper path drops its middles, which
    still names the category the reader needs. A path that resolves to no
    row, or that is not a dotted numeric address, yields ``None``: the caller
    keeps its own label rather than a guess.
    """
    raw = (taxonomy_path or "").strip()
    if not raw or not _DOTTED_PATH_RE.fullmatch(raw):
        return None
    try:
        index = _taxonomy_node_names(str(get_taxonomy_path()))
    except Exception:
        # A label or a reading check must never crash a render on taxonomy
        # I/O (a missing file triggers the loader's download path). The
        # caller keeps its own label — the same no-guess fallback as an
        # unknown path.
        logger.warning("taxonomy unavailable; keeping the two-level label")
        return None
    if not index:
        return None
    segments = raw.split(".")
    wanted = [segments[0]]
    if len(segments) >= 2:
        wanted.append(".".join(segments[:2]))
    wanted.append(raw)
    names: List[str] = []
    for node_path in wanted:
        name = index.get(node_path)
        if not name:
            return None
        # A depth-2 path's branch IS its leaf — the chain says it once.
        if not names or names[-1] != name:
            names.append(name)
    return names


#: #3224 — a node token NAMES a category only when it is distinctive within
#: the taxonomy: at most this many of the vendored node names carry it.
#: Measured over the 1 408 ``text_fr`` names (word extraction ``[A-Za-zÀ-ÿ]{4,}``
#: lowercased): 1 535 of 1 573 tokens (97,6 %) sit at df ≤ 5 — the taxonomy's
#: own vocabulary is a long tail — then 29 tokens live between 6 and 11 and
#: seven spikes stand alone above (question 13, erreur 21, argument 44,
#: sophisme 76, effet 86, appel 125, preuve 18). The bar keeps the carriers
#: the true positive rode (causalité 5, généralisation 5, dilemme 1,
#: cigogne 1, douteuse 2) and drops every word one ordinary sentence away
#: from a false flag: the R1110b render flagged « aucun … identifié » on the
#: node « Sophisme psychogénétique » through « sophisme » alone — a class
#: word, not a category name. The bar is DERIVED from the file (document
#: frequency over its own names), not from an enumerated stoplist.
DISTINCTIVE_NODE_DF_MAX = 5

_NODE_WORD_RE = re.compile(r"[A-Za-zÀ-ÿ]{4,}")


@lru_cache(maxsize=4)
def _taxonomy_node_token_df(csv_path: str) -> Dict[str, int]:
    """Token -> how many node names carry it, read once per file.

    A stopword is left in on purpose: its df is high, so the bar drops it
    without this module re-encoding the reader's stoplist — the join filters
    node tokens through the READER's tokenizer first, this map only measures
    the file.
    """
    df: Dict[str, int] = {}
    index = _taxonomy_node_names(csv_path)
    for name in index.values():
        for token in {t.lower() for t in _NODE_WORD_RE.findall(name)}:
            df[token] = df.get(token, 0) + 1
    return df


def taxonomy_token_df(token: str) -> Optional[int]:
    """How many of the taxonomy's node names carry ``token`` (#3224).

    ``None`` when the taxonomy is unreadable — the caller then treats the
    token as NOT distinctive (a check that cannot measure says nothing),
    which is unreachable in practice: nodes only exist once the index read.
    """
    try:
        df = _taxonomy_node_token_df(str(get_taxonomy_path()))
    except Exception:
        return None
    if not df:
        return None
    return df.get((token or "").lower(), 0)


def fallacy_taxonomy_label(
    fallacy_type: str,
    family: str,
    taxonomy_path: Optional[str],
    *,
    quoted: bool = False,
) -> str:
    """The label the three evidence sites print for one detection.

    A resolvable path renders the type under its taxonomy ancestors —
    « Effet cigogne (Erreur de raisonnement > Causalité douteuse) » — so the
    branch names the category. A detection without a usable path keeps
    today's label, with no guess.

    The record's own ``family`` is never silenced: when it says something the
    taxonomy's root does not (a reconciled or free-text family), both travel —
    « (famille X — Erreur de raisonnement > …) ». When it merely repeats the
    root, it is not printed twice. ``quoted`` is typography only (the Act II
    movement line quotes the name); it never changes what is named.
    """
    head = f"« {fallacy_type} »" if quoted else fallacy_type
    chain = taxonomy_chain(taxonomy_path or "")
    if not chain:
        return f"{head} (famille {family})"
    ancestors = chain[:-1]
    if not ancestors:
        return f"{head} (famille {chain[0]})"
    chain_text = " > ".join(ancestors)
    recorded = str(family or "").strip()
    if (
        not recorded
        or recorded.lower() in ("inconnu", "unknown")
        or recorded.lower() == chain[0].strip().lower()
    ):
        return f"{head} ({chain_text})"
    return f"{head} (famille {recorded} — {chain_text})"


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
