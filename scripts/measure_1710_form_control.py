"""#1710 discriminant control — does the inventory FORM starve the attack axes?

Paired measurement (same text, same model, ONLY the extraction-prompt form
framing varies) that isolates the variable the Epic #1644 / issue #1710
prediction names:

  * BASELINE  = the production ``_invoke_fact_extraction`` prompt verbatim
                (cues act-descriptions: "arg description", "noting rhetorical
                strategies used").
  * FORCED    = same call shape / model / determinism / JSON schema / lang
                clause, ONLY the form framing changed to demand finite-verb
                PROPOSITIONS (truth-conditional claims), not act-descriptions.

For each (corpus, form) the argument inventory is extracted once, then the
five structured-arg translators run over it. Per axis we record the 3-state
distinction the R805 amendment requires:

  * raw=0            -> famine_proposal  (the model proposed none)
  * raw>0, kept=0    -> famine_match     (proposed, all dropped at validation)
  * kept>0           -> renders          (the axis produces)

raw/kept come from the EXISTING instrument ``_log_translation_yield`` (wrapped
here for capture — no new probe added to production). ASPIC contradictions /
undercuts come from the existing #1649 diagnostics warning.

Anti-pendules honored:
  * The attack-axis translator prompts are NOT touched (synthetic control R789
    proved they are alive). Only the upstream extraction prompt framing varies.
  * No attack is fabricated: translators validate every relation against the
    real inventory (production behaviour, unchanged).

Privacy HARD: corpus text is loaded in-memory from the encrypted dataset;
outputs land under evaluation/results/real_analysis/ (GITIGNORED). Arg samples
are truncated and never reach a git/PR/dashboard surface. Opaque IDs
(corpus_A/B/C) on every GitHub-indexed surface.

Usage:
    conda run -n projet-is-roo-new --no-capture-output python scripts/measure_1710_form_control.py --corpus B
    conda run -n projet-is-roo-new --no-capture-output python scripts/measure_1710_form_control.py --corpus B --n 3
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

# Load .env (mirrors run_real_analysis.py — root .env wins).
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
from argumentation_analysis.core.io_manager import load_extract_definitions
from argumentation_analysis.orchestration import structured_arg_translator as tr
from argumentation_analysis.orchestration.structured_arg_translator import (
    translate_to_aba_contraries,
    translate_to_aspic_rules,
    translate_to_bipolar_supports,
    translate_to_setaf_attacks,
    translate_to_weighted_attacks,
)
from argumentation_analysis.orchestration.invoke_callables import (
    _EXTRACTION_MAX_ATTEMPTS,
    _EXTRACTION_MAX_TOKENS,
    _guarded_chat_completion,
    _get_determinism_params,
    _get_openai_client,
    _normalize_items_with_quotes,
    _parse_json_from_llm,
)

DATASET_PATH = Path("argumentation_analysis/data/extract_sources.json.gz.enc")
CORPUS_SRC_IDX = {"A": 11, "B": 3, "C": 2}
RESULTS_DIR = Path("argumentation_analysis/evaluation/results/real_analysis")

# ---------------------------------------------------------------------------
# Existing-instrument capture (wrap _log_translation_yield + the #1649 warning).
# No new probe is added to production code; we only observe what it already emits.
# ---------------------------------------------------------------------------
_yield_records: List[Dict[str, int]] = []
_aspic_diag: Dict[str, int] = {}
_orig_yield = tr._log_translation_yield


def _capture_yield(
    axis: str, data: object, raw_keys: Tuple[str, ...], kept: int
) -> None:
    raw = sum(tr._raw_count(data, k) for k in raw_keys)
    _yield_records.append(
        {"axis": axis, "raw": raw, "kept": kept, "dropped": raw - kept}
    )
    return _orig_yield(axis, data, raw_keys, kept)


tr._log_translation_yield = _capture_yield

# Parse the ASPIC #1649 diagnostics warning for the contradictions / undercuts
# channels specifically (the aggregate yield folds them into ASPIC+ total).
_DIAG_RE = re.compile(
    r"proposed\s+(\d+)\s+contradiction\(s\)\s+\(kept\s+(\d+).*?"
    r"and\s+(\d+)\s+undercut\(s\)\s+\(kept\s+(\d+)",
    re.IGNORECASE | re.DOTALL,
)


class _DiagHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        if "#1649 diagnostics" in msg:
            m = _DIAG_RE.search(msg)
            if m:
                _aspic_diag["contradictions_raw"] = int(m.group(1))
                _aspic_diag["contradictions_kept"] = int(m.group(2))
                _aspic_diag["undercuts_raw"] = int(m.group(3))
                _aspic_diag["undercuts_kept"] = int(m.group(4))


_unified_logger = logging.getLogger("UnifiedPipeline")
_unified_logger.addHandler(_DiagHandler())
_unified_logger.setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Prompts. BASELINE is copied VERBATIM from _invoke_fact_extraction
# (invoke_callables.py:5939-5953). FORCED changes ONLY the form framing
# (act-description -> finite-verb proposition); JSON schema, source_quote
# requirement, fallacy-exclusion and the language clause are identical.
# ---------------------------------------------------------------------------
def _lang_clause(text: str) -> str:
    try:
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _detect_language,
        )

        _lang = _detect_language(text)
        _lang_names = {"de": "German", "fr": "French", "en": "English"}
        if _lang in _lang_names and _lang != "en":
            return (
                f" The source text is in {_lang_names[_lang]}. Analyze it in "
                f"its original language and extract ALL distinct arguments and "
                f"claims with the SAME thoroughness as you would for English — "
                f"do not under-extract because the text is non-English. Keep "
                f"the 'text' descriptions in {_lang_names[_lang]}."
            )
    except Exception:
        pass
    return ""


_JSON_SHAPE = (
    " Respond with ONLY a JSON object:\n"
    '{"arguments": [{"text": "...", "source_quote": "exact quote..."}], '
    '"claims": [{"text": "...", "source_quote": "exact quote..."}], '
    '"summary": "brief analysis summary"}'
)

# Verbatim production body (invoke_callables.py:5939-5948 prefix).
_BASELINE_BODY = (
    "You are an expert argument analyst. Extract the key arguments "
    "and verifiable claims from the text. "
    "For each argument and claim, include the exact quote from the "
    "source text that supports it (verbatim, max 150 chars). "
    "Do NOT detect fallacies — that is handled by a separate specialist. "
    "Focus on: (1) identifying distinct argumentative positions, "
    "(2) extracting factual claims that can be verified, "
    "(3) noting rhetorical strategies used (without labeling them as fallacies)."
)

# FORCED: identical contract, ONLY the form framing changes.
_FORCED_BODY = (
    "You are an expert argument analyst. Extract the PROPOSITIONS that the "
    "text asserts. A proposition is a truth-conditional claim with a finite "
    "verb stating something the speaker asserts to be TRUE or FALSE — a "
    "statement another proposition could confirm or contradict. "
    "CRITICAL: write the proposition CONTENT (what is claimed), NOT a "
    "description of what the speaker does. Do NOT write speech-act "
    "descriptions such as 'Affirms ...', 'Argues ...', 'Uses metaphor ...', "
    "'Positions ...', 'Opens by ...' — write the claim itself (e.g. 'Growth "
    "will exceed 3%', 'Policy X causes outcome Y'). Two propositions can "
    "support or attack each other; two act-descriptions cannot. "
    "For each argument and claim, include the exact quote from the "
    "source text that supports it (verbatim, max 150 chars). "
    "Do NOT detect fallacies — that is handled by a separate specialist. "
    "Focus on: (1) extracting distinct truth-conditional propositions, "
    "(2) extracting factual claims that can be verified, "
    "(3) preserving the propositional CONTENT, not the speech act."
)

FORMS: Dict[str, str] = {
    "baseline_act": _BASELINE_BODY,
    "forced_proposition": _FORCED_BODY,
}

# Axis label returned by _log_translation_yield -> our short key.
TRANSLATORS = [
    ("bipolar", "Bipolar", translate_to_bipolar_supports),
    ("aba", "ABA", translate_to_aba_contraries),
    ("aspic", "ASPIC+", translate_to_aspic_rules),
    ("setaf", "SetAF", translate_to_setaf_attacks),
    ("weighted", "Weighted", translate_to_weighted_attacks),
]


def load_corpus_text(label: str, max_chars: int = 3000, offset: int = 0) -> str:
    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    entry = defs[CORPUS_SRC_IDX[label]]
    text = entry.get("full_text", "") or ""
    return text[offset : offset + max_chars]


async def extract_inventory(
    text: str, body: str, lang_clause: str
) -> Tuple[List[Dict[str, Any]], str]:
    """One extraction attempt-loop mirroring _invoke_fact_extraction exactly.

    Same client, determinism params, json_object mode, max_tokens, config-reject
    handling, parse + normalize. Only ``system_content`` (the form framing) is
    controlled by the caller.
    """
    system_content = body + lang_clause + _JSON_SHAPE
    client, model_id = _get_openai_client()
    if client is None:
        return [], "no-openai-client"
    det_params = _get_determinism_params()
    use_json_mode = True
    use_max_tokens = _EXTRACTION_MAX_TOKENS > 0
    last_reason = "no-parse"
    for attempt in range(1, _EXTRACTION_MAX_ATTEMPTS + 1):
        kw: Dict[str, Any] = dict(det_params)
        if use_json_mode:
            kw["response_format"] = {"type": "json_object"}
        if use_max_tokens:
            kw["max_tokens"] = _EXTRACTION_MAX_TOKENS
        try:
            resp = await _guarded_chat_completion(
                client,
                model=model_id,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": text[:3000]},
                ],
                **kw,
            )
            data = _parse_json_from_llm(resp.choices[0].message.content or "")
            if data:
                args = _normalize_items_with_quotes(data.get("arguments", []))
                return args, data.get("summary", "")
            last_reason = f"no-json(attempt={attempt})"
        except Exception as e:
            low = str(e).lower()
            dropped = False
            if use_json_mode and ("response_format" in low or "json_object" in low):
                use_json_mode = False
                dropped = True
            if use_max_tokens and (
                "max_tokens" in low or "max_completion_tokens" in low
            ):
                use_max_tokens = False
                dropped = True
            if dropped:
                continue
            last_reason = f"call-error({type(e).__name__}:{attempt})"
    return [], f"extraction-failed({last_reason})"


def _state(raw: int, kept: int) -> str:
    if raw == 0:
        return "famine_proposal"
    if kept == 0:
        return "famine_match"
    return "renders"


async def measure_corpus(
    label: str, n: int, model_id: str, offset: int = 0
) -> Dict[str, Any]:
    text = load_corpus_text(label, offset=offset)
    lang_clause = _lang_clause(text)
    print(
        f"[1710] corpus {label}@offset={offset}: {len(text)} chars ; lang_clause={'yes' if lang_clause else 'no'}"
    )

    out: Dict[str, Any] = {
        "corpus": label,
        "offset": offset,
        "model": model_id,
        "n": n,
        "forms": {},
    }
    for form_name, body in FORMS.items():
        runs = []
        for i in range(n):
            t0 = time.time()
            args, summary = await extract_inventory(text, body, lang_clause)
            arg_texts = [
                a["text"] for a in args if isinstance(a, dict) and a.get("text")
            ]
            axes: Dict[str, Any] = {}
            for key, _label, fn in TRANSLATORS:
                _yield_records.clear()
                _aspic_diag.clear()
                try:
                    res = await fn(text, arg_texts)
                    kept = (
                        len(res.relations)
                        if isinstance(res.relations, (list, dict))
                        else 0
                    )
                except Exception as e:
                    axes[key] = {
                        "cause": f"exception:{type(e).__name__}",
                        "raw": None,
                        "kept": None,
                        "state": "exception",
                    }
                    continue
                yr = _yield_records[-1] if _yield_records else {"raw": 0, "kept": 0}
                raw = yr["raw"]
                entry = {
                    "cause": res.cause,
                    "raw": raw,
                    "kept": kept,
                    "state": _state(raw, kept),
                }
                if key == "aspic":
                    entry["contradictions_raw"] = _aspic_diag.get(
                        "contradictions_raw", 0
                    )
                    entry["contradictions_kept"] = _aspic_diag.get(
                        "contradictions_kept", 0
                    )
                    entry["undercuts_raw"] = _aspic_diag.get("undercuts_raw", 0)
                axes[key] = entry
            elapsed = time.time() - t0
            runs.append(
                {
                    "draw": i + 1,
                    "n_args": len(arg_texts),
                    "elapsed_s": round(elapsed, 1),
                    "extraction_status": summary[:80],
                    # Truncated samples stay in the GITIGNORED artifact only.
                    "args_sample": [a[:45] for a in arg_texts[:3]],
                    "axes": axes,
                }
            )
            print(
                f"   [{form_name}] draw {i+1}/{n}: {len(arg_texts)} args, {elapsed:.1f}s"
            )
            for key, _label, _fn in TRANSLATORS:
                a = axes[key]
                extra = ""
                if key == "aspic":
                    extra = f" (contrad raw={a.get('contradictions_raw')} kept={a.get('contradictions_kept')})"
                print(
                    f"        {a['state']:<16} {key:<9} raw={a['raw']} kept={a['kept']}{extra}"
                )
        out["forms"][form_name] = runs
    return out


def render_table(result: Dict[str, Any]) -> str:
    label = result["corpus"]
    n = result["n"]
    lines = [
        f"\n=== #1710 form control — corpus {label} (n={n} per form, model={result['model']}) ===",
        "Each cell: state(raw/kept). state ∈ {renders, famine_match, famine_proposal}.",
        "",
        f"{'axis':<10} {'baseline_act':<22} {'forced_proposition':<22}",
        "-" * 56,
    ]
    # aggregate draws (max, to surface any signal across stochastic draws).
    for key, _label, _fn in TRANSLATORS:
        cells = []
        for form_name in ("baseline_act", "forced_proposition"):
            runs = result["forms"][form_name]
            best = max((r["axes"][key]["kept"] for r in runs), default=0)
            raws = [r["axes"][key]["raw"] for r in runs]
            kepts = [r["axes"][key]["kept"] for r in runs]
            cells.append(f"{_state(max(raws), best):<16}({max(raws)}/{best})")
        lines.append(f"{key:<10} {cells[0]:<22} {cells[1]:<22}")
    return "\n".join(lines)


async def main_async(label: str, n: int, offset: int = 0) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    _client, model_id = _get_openai_client()
    if not model_id:
        model_id = "(unresolved)"
    print(f"[1710] model_id = {model_id}")
    t0 = time.time()
    result = await measure_corpus(label, n, model_id, offset=offset)
    result["date_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result["wall_s"] = round(time.time() - t0, 1)
    print(render_table(result))

    suffix = f"{label}_off{offset}" if offset else label
    out_path = RESULTS_DIR / f"measure_1710_form_control_{suffix}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n[1710] artifact (gitignored) -> {out_path}")


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--corpus", choices=list(CORPUS_SRC_IDX), default="B")
    p.add_argument(
        "--n", type=int, default=1, help="draws per form (LLM is stochastic)"
    )
    p.add_argument(
        "--offset",
        type=int,
        default=0,
        help="char offset to read the corpus from (truncation control: "
        "corpus_B offset 0 is a TOC, offset 30000+ is real prose)",
    )
    a = p.parse_args()
    asyncio.run(main_async(a.corpus, a.n, a.offset))


if __name__ == "__main__":
    main()
