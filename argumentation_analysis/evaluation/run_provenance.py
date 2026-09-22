"""Run provenance stamped next to state dumps (#2045).

Les dumps d'état étaient adressés par un hash opaque sans aucune provenance
de run : impossible de relier un artefact rendu à l'état qui l'a produit
sans balayer les dumps à la main. Ces fonctions assemblent le bloc de
provenance que chaque écriture d'état (signature de batch, méta de juge)
porte désormais à côté de l'état : horodatage UTC, SHA de code, identité
de modèle, paramètres de run.

Tout est identifiant opaque — jamais de nom de source ni de contenu de
corpus (la contrainte de confidentialité s'applique à ce bloc par
construction, puisqu'il relie précisément un run à sa source).
"""

from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def now_utc_iso() -> str:
    """Horodatage UTC ISO-8601 (seconde)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def code_sha() -> Optional[str]:
    """SHA court du commit HEAD, ou None hors dépôt git / git indisponible.

    None (plutôt qu'une exception) : un dump doit toujours s'écrire, même
    si la version de code est indisponible — la clé reste présente avec
    sa valeur nulle, l'absence de valeur est lisible comme telle.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def chat_model_id() -> Optional[str]:
    """Identité résolue du modèle de chat, ou None si aucun LLM configuré.

    Rend le modèle que le résolveur canonique rendrait (#2352/#2370) — sous
    bascule OpenRouter ou substitution #1930, la variable brute nomme un
    modèle que le run n'a pas utilisé (fausse provenance). None (et non le
    défaut du résolveur) quand aucune clé n'est configurée : un défaut rendu
    serait une provenance fantôme sur un artefact.
    """
    from argumentation_analysis.core.llm_service import resolve_chat_endpoint

    api_key, _base_url, model_id = resolve_chat_endpoint()
    return model_id if api_key else None


def provenance_block(params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Bloc de provenance de run à écrire à côté d'un dump d'état (#2045).

    Inclut le manifest environnemental (#2282) : chaque axe optionnel est
    probé (started/not_started + reason) et stampé à côté de la signature.
    Une campagne qui a rendu sur une JVM morte est nommée comme telle, pas
    lue comme « ok » (#2276).
    """
    from argumentation_analysis.evaluation.env_manifest import environment_manifest

    block: Dict[str, Any] = {
        "run_started_utc": now_utc_iso(),
        "code_sha": code_sha(),
        "chat_model_id": chat_model_id(),
        "environment": environment_manifest(),
    }
    if params:
        block["params"] = dict(params)
    return block


def file_sha256(path: Path) -> str:
    """SHA-256 d'un fichier — relie un méta à SON dump d'état (intégrité + lien)."""
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()
