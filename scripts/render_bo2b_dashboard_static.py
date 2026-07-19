"""BO-2b #1493 — Static HTML snapshot of the Governance Dashboard payload.

Anti-pendule : ne lance PAS Puppeteer / Playwright / un vrai React render.
Le but est de produire une PREUVE VISUELLE reproductible du payload que le
dashboard consommerait — sans browser, sans bundler, sans cycle npm.

Approche : un template HTML statique (CSS inline) qui reproduit la
disposition du `GovernanceDashboard` (toolbar + sidebar + détail + verdict)
à partir du JSON produit par ``proof_bo2b_dashboard_e2e.py``.

Si quelqu'un veut une capture au pixel près, il peut ouvrir le HTML dans
un navigateur et faire `Ctrl+S`. Mais ce n'est PAS requis pour la preuve :
la structure DOM + les valeurs + les compteurs sont déjà dans le HTML.

Privacy HARD : payload déjà scrubbé (opaque IDs). Aucune valeur du corpus.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parent.parent


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8" />
<title>BO-2b #1493 — Dashboard snapshot (synthetic, opaque IDs)</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; color: #222; }}
  h1 {{ border-bottom: 2px solid #444; padding-bottom: 4px; }}
  .meta {{ background: #f4f4f4; padding: 12px; border-radius: 4px; margin: 12px 0; font-size: 0.9em; }}
  .meta code {{ background: #fff; padding: 1px 4px; border: 1px solid #ddd; }}
  .row {{ display: flex; gap: 16px; }}
  .col {{ flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 4px; background: #fafafa; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 0.85em; font-weight: bold; }}
  .badge.decided {{ background: #5cb85c; color: white; }}
  .badge.degraded {{ background: #f0ad4e; color: white; }}
  .badge.pending, .badge.stub {{ background: #888; color: white; }}
  .vote-bar {{ display: flex; align-items: center; gap: 6px; margin: 4px 0; }}
  .vote-bar-fill {{ height: 14px; }}
  pre {{ background: #fff; padding: 8px; border: 1px solid #ddd; border-radius: 3px; overflow-x: auto; font-size: 0.8em; }}
  .verdict {{ margin: 12px 0; padding: 12px; border-left: 4px solid #5cb85c; background: #eef9ee; }}
  .verdict.degraded {{ border-left-color: #f0ad4e; background: #fef9ef; }}
</style>
</head>
<body>

<h1>Dashboard de Gouvernance — BO-2b #1493 snapshot</h1>

<div class="meta">
  <strong>Source:</strong> <code>{provenance_script}</code><br/>
  <strong>Workflow:</strong> <code>{workflow}</code> ·
  <strong>Domain:</strong> <code>{domain}</code> ·
  <strong>Privacy:</strong> <code>{privacy}</code>
</div>

<div class="row">
  <div class="col">
    <h2>Proposition</h2>
    <p><strong>ID:</strong> <code>{proposal_id}</code></p>
    <p><strong>Titre:</strong> {title}</p>
    <p><strong>Auteur:</strong> <code>{author}</code></p>
    <p><strong>Tags:</strong> {tags_html}</p>
    <p><strong>Statut:</strong> <span class="badge {status_class}">{status_label}</span></p>
    <p><strong>Soumis le:</strong> {submitted_at}</p>
    <details>
      <summary>Texte de la proposition</summary>
      <pre>{text_escaped}</pre>
    </details>
  </div>

  <div class="col">
    <h2>Deliberation</h2>
    <p><strong>ID:</strong> <code>{delib_id}</code></p>
    <p><strong>Workflow:</strong> <code>{delib_workflow}</code></p>
    <p><strong>Statut:</strong> <span class="badge {delib_class}">{delib_status}</span></p>
    <p><strong>Started:</strong> {delib_started}</p>
    <p><strong>Completed:</strong> {delib_completed}</p>
  </div>
</div>

<div class="row">
  <div class="col">
    <h2>Votes ({votes_total})</h2>
    {votes_html}
  </div>

  <div class="col">
    <h2>Verdict de gouvernance</h2>
    {verdict_html}
  </div>
</div>

<h2>Analysis results (extrait)</h2>
<pre>{results_escaped}</pre>

</body>
</html>
"""


def _badge_class(status: str) -> str:
    s = status.lower()
    if s in ("decided", "completed"):
        return "decided"
    if s in ("degraded", "failed", "stub"):
        return "degraded"
    return "pending"


def _label_fr(status: str) -> str:
    mapping = {
        "pending": "En attente",
        "analyzing": "Analyse en cours",
        "debating": "Débat",
        "voting": "Vote",
        "decided": "Décidé",
        "completed": "Terminé",
        "running": "En cours",
        "failed": "Échec",
        "degraded": "Dégradé",
        "stub": "Stub",
    }
    return mapping.get(status.lower(), status)


def _render_votes(votes: list) -> tuple[str, str]:
    counts = {"pour": 0, "contre": 0, "abstention": 0}
    for v in votes:
        pos = v.get("position", "").lower()
        if pos in ("for", "pour"):
            counts["pour"] += 1
        elif pos in ("against", "contre"):
            counts["contre"] += 1
        elif pos in ("abstain", "abstention"):
            counts["abstention"] += 1
    total = sum(counts.values()) or 1
    bar_colors = {"pour": "#5cb85c", "contre": "#d9534f", "abstention": "#888"}
    rows = []
    for k in ("pour", "contre", "abstention"):
        n = counts[k]
        pct = (n / total) * 100
        rows.append(
            f'<div class="vote-bar">'
            f'<span style="width:80px">{k.capitalize()}</span>'
            f'<div class="vote-bar-fill" style="width:{pct:.1f}%;background:{bar_colors[k]}"></div>'
            f'<span>{n}</span>'
            f'</div>'
        )
    return "\n".join(rows), str(sum(counts.values()))


def _render_verdict(payload: Dict[str, Any]) -> str:
    decided = payload.get("governance_decided_firsthand", False)
    degraded = payload.get("degraded", False)
    verdict = payload.get("governance_verdict") or {}
    if decided:
        decision = verdict.get("decision", "(non précisé)")
        return (
            f'<div class="verdict">'
            f'<p><strong>Décision:</strong> {html.escape(str(decision))}</p>'
            f'<pre>{html.escape(json.dumps(verdict, indent=2, ensure_ascii=False))}</pre>'
            f'</div>'
        )
    if degraded:
        return '<div class="verdict degraded"><p><em>Verdict dégradé (honest-absent).</em> Pipeline ou LLM indisponible localement.</p></div>'
    return '<div class="verdict degraded"><p><em>Stub pipeline — pas de verdict.</em></p></div>'


def render(payload: Dict[str, Any]) -> str:
    p = payload["proposal"]
    d = payload["deliberation"]
    votes_html, votes_total = _render_votes(payload.get("votes", []))
    tags = p.get("tags") or []
    tags_html = " ".join(f'<span class="badge pending">{html.escape(t)}</span>' for t in tags) or "(none)"
    results_raw = json.dumps(payload.get("results") or {}, indent=2, ensure_ascii=False)
    return HTML_TEMPLATE.format(
        provenance_script=payload.get("provenance", {}).get("script", "?"),
        workflow=payload.get("provenance", {}).get("workflow", "?"),
        domain=payload.get("provenance", {}).get("domain", "?"),
        privacy=payload.get("provenance", {}).get("privacy", "?"),
        proposal_id=p.get("id", "?"),
        title=html.escape(p.get("title") or "(sans titre)"),
        author=p.get("author", "?"),
        tags_html=tags_html,
        status_class=_badge_class(p.get("status", "pending")),
        status_label=_label_fr(p.get("status", "pending")),
        submitted_at=p.get("submitted_at") or "?",
        text_escaped=html.escape(p.get("text") or ""),
        delib_id=d.get("id", "?"),
        delib_workflow=d.get("workflow", "?"),
        delib_class=_badge_class(d.get("status", "pending")),
        delib_status=_label_fr(d.get("status", "pending")),
        delib_started=d.get("started_at") or "?",
        delib_completed=d.get("completed_at") or "(en cours)",
        votes_total=votes_total,
        votes_html=votes_html,
        verdict_html=_render_verdict(payload),
        results_escaped=html.escape(results_raw),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=REPO_ROOT / "evaluation" / "results" / "bo2b_dashboard_proof" / "dashboard_data.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "evaluation" / "results" / "bo2b_dashboard_proof" / "dashboard_snapshot.html",
    )
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    html_out = render(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_out, encoding="utf-8")
    print(f"[BO-2b #1493] Wrote {args.output} ({len(html_out)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
