"""Tests for BO-2b #1493 proof script + static dashboard render.

Two contract levels (no LLM / no JVM / no browser):

1. **Static câblage contract** — proposalApi.js in React must call each
   FastAPI endpoint that proposal_endpoints.py exposes. We assert by static
   read+grep that the URL paths match (8 endpoints / 8 client functions).

2. **Runtime flow contract** — `proof_bo2b_dashboard_e2e.py` runs the full
   propose→vote→deliberate cycle through `ProposalStore` (no FastAPI) and
   serializes a JSON-safe payload. We assert the shape and privacy markers
   (opaque IDs, synthetic label).

3. **Render contract** — `render_bo2b_dashboard_static.py` consumes the
   payload and emits an HTML snapshot. We assert it parses, contains the
   opaque ID, and respects the decided/degraded branches.

Privacy HARD #1491:
- The PROPOSITION is synthetic (chess-club budget, already used in
  `test_deliberation_genuine_verdict.py`). No raw_text from the encrypted
  corpus leaks anywhere.
- IDs on disk are opaque (`prop_<8hex>`).
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import types
from typing import Any, Dict

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
PROPOSAL_API = REPO_ROOT / "services" / "web_api" / "interface-web-argumentative" / "src" / "services" / "proposalApi.js"
PROPOSAL_ENDPOINTS = REPO_ROOT / "api" / "proposal_endpoints.py"
PROOF_SCRIPT = REPO_ROOT / "scripts" / "proof_bo2b_dashboard_e2e.py"
RENDER_SCRIPT = REPO_ROOT / "scripts" / "render_bo2b_dashboard_static.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_module(path: pathlib.Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec and spec.loader, f"Could not build importlib spec for {path}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# 1) Static câblage contract
# ---------------------------------------------------------------------------


class TestStaticCablageContract:
    """The 8 React `proposalApi.js` functions must hit 8 backend endpoints."""

    @pytest.fixture(scope="class")
    def api_src(self) -> str:
        return PROPOSAL_API.read_text(encoding="utf-8")

    @pytest.fixture(scope="class")
    def endpoints_src(self) -> str:
        return PROPOSAL_ENDPOINTS.read_text(encoding="utf-8")

    def test_propose_endpoint_wired(self, api_src: str, endpoints_src: str) -> None:
        assert "/api/propose" in api_src
        assert re.search(r'@proposal_router\.post\(\s*"/propose"', endpoints_src)

    def test_proposals_list_endpoint_wired(self, api_src: str, endpoints_src: str) -> None:
        assert "/api/proposals" in api_src
        assert re.search(r'@proposal_router\.get\(\s*"/proposals"', endpoints_src)

    def test_proposal_get_endpoint_wired(self, api_src: str, endpoints_src: str) -> None:
        # /api/proposals/{id} in client, /proposals/{proposal_id} in router.
        assert re.search(r"/api/proposals/\$\{", api_src)
        assert re.search(r'@proposal_router\.get\(\s*"/proposals/\{proposal_id\}"', endpoints_src)

    def test_vote_endpoint_wired(self, api_src: str, endpoints_src: str) -> None:
        assert "/vote" in api_src
        assert "/vote" in endpoints_src

    def test_deliberate_endpoint_wired(self, api_src: str, endpoints_src: str) -> None:
        assert "/api/deliberate" in api_src
        assert re.search(r'@proposal_router\.post\(\s*"/deliberate"', endpoints_src)

    def test_deliberation_status_endpoint_wired(self, api_src: str, endpoints_src: str) -> None:
        assert re.search(r"/api/deliberate/.*status", api_src)
        assert re.search(r'@proposal_router\.get\(\s*"/deliberate/\{delib_id\}/status"', endpoints_src)

    def test_capabilities_endpoint_wired(self, api_src: str, endpoints_src: str) -> None:
        assert "/api/capabilities" in api_src
        assert re.search(r'@proposal_router\.get\(\s*"/capabilities"', endpoints_src)

    def test_custom_workflow_endpoint_wired(self, api_src: str, endpoints_src: str) -> None:
        assert "/api/workflow/custom" in api_src
        assert re.search(r'@proposal_router\.post\(\s*"/workflow/custom"', endpoints_src)

    def test_npm_run_build_documented_in_readme(self) -> None:
        readme = (REPO_ROOT / "services" / "web_api" / "interface-web-argumentative" / "README.md").read_text(
            encoding="utf-8"
        )
        assert "npm run build" in readme
        # BO-2b DoD #1 satisfied.


# ---------------------------------------------------------------------------
# 2) Runtime proof contract — uses ProposalStore directly (no FastAPI)
# ---------------------------------------------------------------------------


class TestProofRuntimeContract:
    @pytest.fixture(scope="class")
    def proof_mod(self) -> types.ModuleType:
        return _load_module(PROOF_SCRIPT, "proof_bo2b_1493")

    def test_module_imports(self, proof_mod: types.ModuleType) -> None:
        assert hasattr(proof_mod, "run_democratech_flow")
        assert hasattr(proof_mod, "PROPOSITION")
        assert hasattr(proof_mod, "_opaque_id")
        assert hasattr(proof_mod, "_serialize_proposal")

    def test_opaque_id_format(self, proof_mod: types.ModuleType) -> None:
        oid = proof_mod._opaque_id("test_seed")
        assert oid.startswith("prop_")
        assert len(oid) == 13  # "prop_" + 8 hex
        # Determinism (replay-cache friendly).
        assert oid == proof_mod._opaque_id("test_seed")
        assert oid != proof_mod._opaque_id("other_seed")

    def test_proposition_is_synthetic(self, proof_mod: types.ModuleType) -> None:
        """No leakage from the encrypted corpus."""
        text = proof_mod.PROPOSITION
        # The synthetic chess-club marker.
        assert "club d'echecs" in text or "chess" in text.lower()
        assert "2000 euros" in text
        # Privacy HARD: forbidden fields MUST NOT appear (no full_text etc.).
        for forbidden in ("raw_text", "full_text", "verbatim"):
            assert forbidden not in text, f"Privacy leak: {forbidden!r} in PROPOSITION"

    def test_run_democratech_flow_produces_payload(self, proof_mod: types.ModuleType) -> None:
        from api.proposal_service import ProposalStore

        store = ProposalStore()
        payload = asyncio.run(proof_mod.run_democratech_flow(store))

        # Required keys (consumed by the React dashboard).
        assert "proposal" in payload
        assert "deliberation" in payload
        assert "votes" in payload
        assert "results" in payload
        assert "governance_verdict" in payload
        assert "governance_decided_firsthand" in payload
        assert "degraded" in payload
        assert "provenance" in payload

        # Provenance markers.
        prov = payload["provenance"]
        assert prov["synthetic"] is True
        assert prov["privacy"] == "opaque_ids"
        assert prov["workflow"] == "democratech"

        # Author MUST be an opaque ID.
        assert payload["proposal"]["author"].startswith("prop_")

        # 3 synthetic votes.
        assert len(payload["votes"]) == 3

        # Deliberation status is one of the known enum values.
        status = payload["deliberation"]["status"]
        assert status in ("pending", "analyzing", "decided", "completed", "failed")

    def test_json_roundtrip(self, proof_mod: types.ModuleType, tmp_path: pathlib.Path) -> None:
        """The payload MUST be JSON-serializable end-to-end (FastAPI safe)."""
        from api.proposal_service import ProposalStore

        store = ProposalStore()
        payload = asyncio.run(proof_mod.run_democratech_flow(store))
        out = tmp_path / "dashboard_data.json"
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        reloaded = json.loads(out.read_text(encoding="utf-8"))
        assert reloaded["proposal"]["id"] == payload["proposal"]["id"]


# ---------------------------------------------------------------------------
# 3) Render contract — payload → HTML snapshot
# ---------------------------------------------------------------------------


class TestRenderContract:
    @pytest.fixture(scope="class")
    def render_mod(self) -> types.ModuleType:
        return _load_module(RENDER_SCRIPT, "render_bo2b_1493")

    def test_module_imports(self, render_mod: types.ModuleType) -> None:
        assert hasattr(render_mod, "render")

    def test_render_decided_payload(self, render_mod: types.ModuleType) -> None:
        payload = {
            "proposal": {
                "id": "abc12345",
                "title": "Chess-club budget",
                "text": "Le club d'echecs dispose de 2000 euros...",
                "author": "prop_deadbeef",
                "tags": ["budget", "synthetic"],
                "submitted_at": "2026-07-19T10:00:00",
                "status": "decided",
            },
            "deliberation": {
                "id": "del00001",
                "proposal_id": "abc12345",
                "workflow": "democratech",
                "status": "completed",
                "started_at": "2026-07-19T10:00:01",
                "completed_at": "2026-07-19T10:00:05",
                "results": None,
                "error": None,
            },
            "votes": [
                {"voter_id": "prop_aaaa1111", "position": "for"},
                {"voter_id": "prop_bbbb2222", "position": "against"},
                {"voter_id": "prop_cccc3333", "position": "for"},
            ],
            "results": {},
            "governance_verdict": {"decision": "Option C (hybride)", "score": 0.67},
            "governance_decided_firsthand": True,
            "degraded": False,
            "provenance": {
                "script": "scripts/proof_bo2b_dashboard_e2e.py",
                "workflow": "democratech",
                "domain": "chess_club_budget",
                "privacy": "opaque_ids",
                "synthetic": True,
            },
        }
        html_out = render_mod.render(payload)
        # Privacy markers MUST appear in the rendered HTML.
        assert "abc12345" in html_out
        assert "prop_deadbeef" in html_out
        # Anti-théâtre: the "decided" badge class must be present.
        assert "badge decided" in html_out
        assert "Option C" in html_out
        # DO NOT leak raw_text / full_text in any branch.
        assert "raw_text" not in html_out

    def test_render_degraded_payload(self, render_mod: types.ModuleType) -> None:
        payload = {
            "proposal": {
                "id": "abc99999",
                "title": "Synthetic",
                "text": "...",
                "author": "prop_dec0000",
                "tags": [],
                "submitted_at": "2026-07-19T10:00:00",
                "status": "pending",
            },
            "deliberation": {
                "id": "del00002",
                "proposal_id": "abc99999",
                "workflow": "democratech",
                "status": "failed",
                "started_at": "2026-07-19T10:00:01",
                "completed_at": "2026-07-19T10:00:02",
                "results": None,
                "error": "Pipeline unavailable",
            },
            "votes": [],
            "results": None,
            "governance_verdict": {},
            "governance_decided_firsthand": False,
            "degraded": True,
            "provenance": {"script": "x", "workflow": "y", "domain": "z", "privacy": "opaque_ids", "synthetic": True},
        }
        html_out = render_mod.render(payload)
        # Honest absent: degraded branch visible.
        assert "dégradé" in html_out.lower() or "degraded" in html_out.lower()
        assert "badge degraded" in html_out


# ---------------------------------------------------------------------------
# 4) CLI smoke (no LLM): the proof script must run end-to-end and exit 0
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_proof_script_cli_runs(tmp_path: pathlib.Path) -> None:
    """`python scripts/proof_bo2b_dashboard_e2e.py --output <tmp>` exits 0."""
    out_path = tmp_path / "data.json"
    result = subprocess.run(
        [
            sys.executable,
            str(PROOF_SCRIPT),
            "--output",
            str(out_path),
            "--quiet",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"proof script failed:\nSTDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )
    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["provenance"]["synthetic"] is True
    assert payload["proposal"]["author"].startswith("prop_")