"""BO-2b #1493 — Preuve E2E : Dashboard React × backend × run democratech réel.

Stratégie anti-théâtre (#1019) :
- Le payload exporté dans `dashboard_data.json` PROVIENT d'un run réel de
  `run_deliberation_workflow` (via `ProposalStore`). Pas de fixtures statiques.
- Si l'env est cassé (JVM/LLM), `_run_pipeline` dégrade en stub honnête —
  la dégradation EST capturée, pas masquée (cf. `degraded` flag).

Anti-pendule :
- Ne réécrit aucun composant React (câblage déjà OK).
- Ne lance PAS de navigateur / Puppeteer / WebSocket réel.
- Le rendu DOM est laissé au navigateur ; ici on sérialise juste le payload
  que le dashboard consommerait.

Privacy HARD #1491 :
- PROPOSITION = chess-club budget synthétique (domaine public, déjà utilisé
  dans `test_deliberation_genuine_verdict.py`). Aucun raw_text / full_text /
  verbatim du corpus chiffré. IDs opaques (`prop_<8hex>`) sur toute surface.

Sortie (gitignored via `evaluation/results/`) :
- ``dashboard_data.json`` : payload JSON-safe du store après run (proposal
  enrichie + deliberation result + capabilities + votes). Sera consommé par
  ``scripts/render_bo2b_dashboard_static.py`` pour produire un snapshot
  HTML statique du dashboard via ReactDOMServer (preuve visuelle).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict

# --- Bootstrap path so this script runs from any cwd --------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from api.proposal_models import (  # noqa: E402
    ProposalCreate,
    VoteCreate,
)
from api.proposal_service import (  # noqa: E402
    ProposalStore,
    run_deliberation_workflow,
)

logger = logging.getLogger("proof_bo2b_dashboard")

# Synthetic, domain-public proposition (no raw_text from the encrypted corpus).
# Mirrors `tests/integration/api/test_deliberation_genuine_verdict.py::PROPOSITION`
# to keep the BO-2b proof and the BO-2 API proof on the same input.
PROPOSITION = (
    "Le club d'echecs dispose d'un budget participatif de 2000 euros. "
    "Trois options divergentes s'affrontent. "
    "Option A : organiser un tournoi inter-villes avec buffet et prix pour 2000 "
    "euros, ce qui augmentera la visibilite du club et recrutera de nouveaux membres. "
    "Option B : investir les 2000 euros en materiel pedagogique, echiquiers neufs, "
    "horloges et supports de cours, car les echiquiers actuels sont uses. "
    "Option C : un format hybride, 1000 euros pour un tournoi reduit et 1000 euros "
    "pour le materiel pedagogique, equilibre entre visibilite et pedagogie."
)

# Opaque proposal ID (8 hex). Avoids leaking real-source IDs on any surface.
OPAQUE_AUTHOR = "prop_" + hashlib.sha256(b"synthetic_chess_club_budget_v1").hexdigest()[:8]


def _opaque_id(seed: str) -> str:
    """Return an 8-hex opaque ID derived from ``seed`` (privacy HARD)."""
    return "prop_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]


def _serialize_proposal(p) -> Dict[str, Any]:
    """Coerce a ``Proposal`` pydantic model into a JSON-safe dict.

    Mirrors ``ProposalStore._jsonable`` (private) but kept local so this
    script has zero coupling to store internals beyond the public API.
    """
    return {
        "id": p.id,
        "title": p.title,
        "text": p.text,
        "author": p.author,
        "tags": list(p.tags or []),
        "submitted_at": p.submitted_at.isoformat() if p.submitted_at else None,
        "status": p.status.value if hasattr(p.status, "value") else str(p.status),
    }


def _serialize_deliberation(d) -> Dict[str, Any]:
    return {
        "id": d.id,
        "proposal_id": d.proposal_id,
        "workflow": d.workflow,
        "status": d.status.value if hasattr(d.status, "value") else str(d.status),
        "started_at": d.started_at.isoformat() if d.started_at else None,
        "completed_at": d.completed_at.isoformat() if d.completed_at else None,
        "results": d.results,
        "error": d.error,
    }


async def run_democratech_flow(store: ProposalStore) -> Dict[str, Any]:
    """Execute one full proposal→deliberate→vote cycle on the in-memory store.

    Returns a JSON-safe payload suitable for the React dashboard's initial
    state (proposal + deliberation + vote + analysis results). Mirrors what
    ``GET /api/proposals/{id}`` + ``GET /api/deliberate/{id}/status`` would
    return after a successful run.
    """
    # 1. Create proposal (synthetic chess-club).
    proposal_in = ProposalCreate(
        text=PROPOSITION,
        author=OPAQUE_AUTHOR,
        title="Chess-club budget 2000 EUR (synthetic)",
        tags=["budget", "synthetic", "bo-2b"],
    )
    proposal = store.create_proposal(proposal_in)

    # 2. Add 3 synthetic votes (one per option) to feed the governance phase.
    #    The real democratech workflow reads these to compute the verdict.
    #    `position` MUST be one of 'pour' / 'contre' / 'abstention' (Pydantic literal).
    for voter_seed, position in (
        ("voter_alpha", "pour"),
        ("voter_beta", "contre"),
        ("voter_gamma", "pour"),
    ):
        vote = VoteCreate(
            voter_id=_opaque_id(voter_seed),
            position=position,
        )
        store.add_vote(proposal.id, vote)

    # 3. Start a real democratech deliberation (the store updates status
    #    through PENDING → ANALYZING → DECIDED). The workflow tries the
    #    UnifiedPipeline first; on any ImportError / Exception it falls
    #    back to a stub with a ``note`` field — captured honestly below.
    created = store.create_deliberation(
        proposal_id=proposal.id,
        workflow="democratech",
    )
    # `create_deliberation` returns the full DeliberationStatusResponse, not
    # the bare id — extract it here.
    delib_id = created.id if hasattr(created, "id") else str(created)

    # 4. Run the workflow (background task in the API; here we await it
    #    directly so the proof script is reproducible end-to-end).
    await run_deliberation_workflow(
        store=store,
        delib_id=delib_id,
        proposal_text=PROPOSITION,
        workflow="democratech",
        options={},
    )

    # 5. Re-fetch enriched state.
    final_proposal = store.get_proposal(proposal.id)
    final_delib = store.get_deliberation(delib_id)
    votes = store.get_votes(proposal.id)
    results = final_proposal.analysis_results if final_proposal else None

    # 6. Extract the governance verdict marker (if present) — BO-2 #1472 honest.
    gov_output = (
        (results or {})
        .get("phases", {})
        .get("democratic_vote", {})
        .get("output", {})
    )
    verdict = gov_output.get("governance_verdict") or {}
    decided_firsthand = bool(gov_output.get("governance_decided_firsthand"))
    degraded = bool(gov_output.get("degraded"))

    return {
        "proposal": _serialize_proposal(final_proposal),
        "deliberation": _serialize_deliberation(final_delib),
        "votes": [
            (
                {**v.model_dump(mode="json"), "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None}
                if hasattr(v, "model_dump") else {**dict(v), "recorded_at": None}
            )
            for v in votes
        ],
        "results": results,
        "governance_verdict": verdict,
        "governance_decided_firsthand": decided_firsthand,
        "degraded": degraded,
        "provenance": {
            "script": "scripts/proof_bo2b_dashboard_e2e.py",
            "workflow": "democratech",
            "synthetic": True,
            "domain": "chess_club_budget",
            "privacy": "opaque_ids",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "evaluation" / "results" / "bo2b_dashboard_proof" / "dashboard_data.json",
        help="Output JSON path (gitignored).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress INFO logs.",
    )
    args = parser.parse_args()

    if not args.quiet:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    args.output.parent.mkdir(parents=True, exist_ok=True)

    store = ProposalStore()
    t0 = time.monotonic()
    payload = asyncio.run(run_democratech_flow(store))
    elapsed = time.monotonic() - t0

    # Honest status line (anti-théâtre #1019 — degraded is a VALID outcome).
    verdict_status = (
        "DECIDED" if payload["governance_decided_firsthand"]
        else "DEGRADED" if payload["degraded"]
        else "STUB"
    )

    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"[BO-2b #1493] Wrote {args.output} ({verdict_status}, {elapsed:.2f}s)")
    print(f"[BO-2b #1493] Proposal: {payload['proposal']['id']} (synthetic, opaque ID)")
    print(f"[BO-2b #1493] Deliberation: {payload['deliberation']['id']} -> {payload['deliberation']['status']}")
    print(f"[BO-2b #1493] Votes: {len(payload['votes'])}")
    if payload["governance_decided_firsthand"]:
        print(f"[BO-2b #1493] Verdict: {payload['governance_verdict'].get('decision', '?')}")
    elif payload["degraded"]:
        print("[BO-2b #1493] Deliberation degraded (env or pipeline unavailable) — verdict honest-absent.")
    else:
        print("[BO-2b #1493] Stub pipeline ran (no LLM path). Verdict absent.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
