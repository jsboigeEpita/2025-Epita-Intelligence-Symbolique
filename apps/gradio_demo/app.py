#!/usr/bin/env python3
"""Gradio live demo — soutenance argumentation analysis.

Launch:
    python apps/gradio_demo/app.py

Requires: gradio (pip install gradio)
"""

import asyncio
import json
import sys
import time
from pathlib import Path

try:
    import gradio as gr
except ImportError:
    print("Install gradio first: pip install gradio")
    sys.exit(1)

# Ensure project root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "argumentation_analysis"))
sys.path.insert(0, str(REPO_ROOT / "project_core"))

from dotenv import load_dotenv

load_dotenv(REPO_ROOT / ".env")

# Pre-built sample texts from scenarios
SAMPLES = {
    "Politique": (REPO_ROOT / "examples" / "scenarios" / "politics.txt").read_text(encoding="utf-8")[:2000],
    "Science": (REPO_ROOT / "examples" / "scenarios" / "science.txt").read_text(encoding="utf-8")[:2000],
    "Media": (REPO_ROOT / "examples" / "scenarios" / "media.txt").read_text(encoding="utf-8")[:2000],
    "Philosophie": (REPO_ROOT / "examples" / "scenarios" / "philosophy.txt").read_text(encoding="utf-8")[:2000],
}


def _extract_fallacies(state: dict) -> str:
    fallacies = state.get("identified_fallacies", [])
    if isinstance(fallacies, list) and fallacies:
        lines = []
        for f in fallacies:
            if isinstance(f, dict):
                name = f.get("fallacy_type", f.get("name", str(f)))
                conf = f.get("confidence", f.get("score", ""))
                lines.append(f"- **{name}** (confiance: {conf})")
            else:
                lines.append(f"- {f}")
        return "\n".join(lines)
    count = state.get("fallacy_count", 0)
    return f"Nombre de sophismes detectes: {count}"


def _extract_arguments(state: dict) -> str:
    args = state.get("arguments", state.get("extracted_arguments", []))
    if isinstance(args, list) and args:
        lines = []
        for i, a in enumerate(args, 1):
            if isinstance(a, dict):
                text = a.get("text", a.get("content", str(a)))[:200]
                role = a.get("role", a.get("type", ""))
                lines.append(f"**Arg {i}** [{role}]: {text}...")
            else:
                lines.append(f"**Arg {i}**: {str(a)[:200]}")
        return "\n\n".join(lines)
    count = state.get("argument_count", 0)
    return f"Arguments extraits: {count}"


def _extract_formal(state: dict) -> str:
    sections = []
    for key in ("propositional_analysis", "fol_analysis_results", "modal_analysis",
                "dung_framework", "jtms_state", "atms_contexts"):
        val = state.get(key)
        if val and val not in ([], {}, "", None):
            if isinstance(val, dict):
                sections.append(f"### {key}\n```json\n{json.dumps(val, indent=2, ensure_ascii=False, default=str)[:1000]}\n```")
            elif isinstance(val, list):
                sections.append(f"### {key}\n" + "\n".join(f"- {v}" for v in val[:10]))
            else:
                sections.append(f"### {key}\n{str(val)[:500]}")
    return "\n\n".join(sections) if sections else "Pas de resultats formels."


def _extract_counter_args(state: dict) -> str:
    ca = state.get("counter_arguments", [])
    if isinstance(ca, list) and ca:
        lines = []
        for c in ca:
            if isinstance(c, dict):
                strat = c.get("strategy", c.get("type", ""))
                target = c.get("target_argument", "")
                text = c.get("text", c.get("content", str(c)))[:300]
                lines.append(f"**{strat}** → {target}\n{text}")
            else:
                lines.append(f"- {str(c)[:300]}")
        return "\n\n".join(lines)
    return "Pas de contre-arguments generes."


def _extract_quality(state: dict) -> str:
    scores = state.get("quality_scores", state.get("argument_quality", {}))
    if isinstance(scores, dict) and scores:
        lines = []
        for k, v in scores.items():
            if isinstance(v, (int, float)):
                lines.append(f"- **{k}**: {v:.2f}")
            elif isinstance(v, dict):
                for kk, vv in v.items():
                    if isinstance(vv, (int, float)):
                        lines.append(f"- **{k}/{kk}**: {vv:.2f}")
        return "\n".join(lines) if lines else str(scores)[:500]
    return "Pas de scores de qualite."


def _extract_narrative(state: dict) -> str:
    narrative = state.get("narrative_synthesis", state.get("synthesis", ""))
    if isinstance(narrative, str) and narrative:
        return narrative[:2000]
    if isinstance(narrative, dict):
        return json.dumps(narrative, indent=2, ensure_ascii=False, default=str)[:2000]
    return "Pas de synthese narrative."


async def _run_analysis(text: str, workflow: str):
    from argumentation_analysis.orchestration.unified_pipeline import run_unified_analysis
    return await run_unified_analysis(text, workflow_name=workflow)


def analyze(text: str, workflow: str):
    """Run analysis and return tab contents."""
    if not text.strip():
        yield (
            "Erreur: texte vide", "", "", "", "", "",
            "Collez un texte argumentatif et cliquez Analyser."
        )
        return

    t0 = time.perf_counter()
    yield (
        "⏳ Analyse en cours...", "", "", "", "", "",
        f"Workflow: {workflow} | Lancement du pipeline..."
    )

    try:
        results = asyncio.run(_run_analysis(text, workflow))
    except Exception as e:
        yield (
            f"❌ Erreur: {e}", "", "", "", "", "",
            f"Erreur pendant l'analyse: {e}"
        )
        return

    elapsed = round(time.perf_counter() - t0, 1)
    state = results.get("state_snapshot", {})

    # Try to get richer state from unified_state
    unified = results.get("unified_state")
    if unified is not None:
        try:
            full = unified.get_state_snapshot(summarize=False)
            if full:
                state = full
        except Exception:
            pass

    status = f"✅ Analyse terminee en {elapsed}s"
    if results.get("partial"):
        status = f"⚠️ Analyse partielle ({elapsed}s) — certaines phases ont echoue"

    yield (
        status,
        _extract_arguments(state),
        _extract_fallacies(state),
        _extract_formal(state),
        _extract_counter_args(state),
        _extract_quality(state),
        _extract_narrative(state),
    )


# ---- Gradio UI ----

with gr.Blocks(
    title="Analyse Argumentative Multi-Agents",
    theme=gr.themes.Soft(),
) as demo:
    gr.Markdown(
        "# Analyse Argumentative Multi-Agents\n"
        "Intelligence Symbolique — EPITA 2025\n\n"
        "Collez un texte argumentatif ou selectionnez un scenario, puis cliquez **Analyser**."
    )

    with gr.Row():
        with gr.Column(scale=2):
            text_input = gr.Textbox(
                label="Texte a analyser",
                lines=12,
                placeholder="Collez ici un discours, editorial, ou argument...",
            )
            with gr.Row():
                workflow_choice = gr.Dropdown(
                    choices=["light", "standard", "spectacular"],
                    value="light",
                    label="Workflow",
                )
                sample_btn = gr.Dropdown(
                    choices=list(SAMPLES.keys()),
                    label="Charger scenario",
                )
            analyze_btn = gr.Button("Analyser", variant="primary", size="lg")
            status_output = gr.Markdown("")

        with gr.Column(scale=3):
            with gr.Tabs():
                with gr.TabItem("Arguments"):
                    args_output = gr.Markdown("")
                with gr.TabItem("Sophismes"):
                    fallacies_output = gr.Markdown("")
                with gr.TabItem("Logique Formelle"):
                    formal_output = gr.Markdown("")
                with gr.TabItem("Contre-Arguments"):
                    counter_output = gr.Markdown("")
                with gr.TabItem("Qualite"):
                    quality_output = gr.Markdown("")
                with gr.TabItem("Synthese"):
                    narrative_output = gr.Markdown("")

    # Wire up sample loading
    def load_sample(name):
        return SAMPLES.get(name, "")

    sample_btn.change(
        fn=load_sample,
        inputs=[sample_btn],
        outputs=[text_input],
    )

    # Wire up analysis
    analyze_btn.click(
        fn=analyze,
        inputs=[text_input, workflow_choice],
        outputs=[
            status_output,
            args_output,
            fallacies_output,
            formal_output,
            counter_output,
            quality_output,
            narrative_output,
        ],
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
