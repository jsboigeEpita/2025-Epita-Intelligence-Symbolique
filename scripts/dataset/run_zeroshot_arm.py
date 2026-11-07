"""#2841 — the zero-shot arm of the corpus campaign.

One call per document: the SAME documents (``expand_corpus``, same
``--max-chars``), the SAME model (canonical resolver — never a raw env
read, #2352) and the SAME input text as the pipeline arm. The answer is
kept IN FULL under the gitignored results directory.

Why this producer exists (measured in #2841): the existing instruments
could not answer the mandate — ``run_capstone_c1`` truncates the zero-shot
input to ``text[:8000]`` while the pipeline receives far more, and
``_scrub_baseline`` keeps only the answer's LENGTH, so nothing was left to
read; ``measure_both_paths_vs_zeroshot`` compares against a reference
recorded on a retired model as counts; ``zero_shot_surplus`` never runs a
zero-shot at all.

Usage (PYTHONPATH is required — the repo root is not on sys.path for a
plain script run):

    PYTHONPATH=. python scripts/dataset/run_zeroshot_arm.py \
        [--max-chars 0] [--timeout 600] [--max-completion-tokens 32000] \
        [--skip-existing] [--dry-run]

Output (gitignored — ``argumentation_analysis/evaluation/results/`` is
ignored by default):

    argumentation_analysis/evaluation/results/zeroshot_2841/
        <opaque_id>.json — provenance header + the FULL answer

The environment stamp (#2282) is printed at the end of the run, like the
batch runner's.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

RESULTS_DIR = (
    REPO_ROOT / "argumentation_analysis" / "evaluation" / "results" / "zeroshot_2841"
)
DATASET_PATH = (
    REPO_ROOT / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"
)

# #3460 — the completion cap, a flag with a default that leaves room for a
# thinking model. Panel B measured 2 of 10 Sonnet answers stopping at
# ``finish_reason: "length"`` on the old 16 000 hardcode: Sonnet bills its
# hidden thinking as completion tokens (#3096 measured ~44 % of a
# completion), so a cap sized for luna (largest 11 781) cuts a thinking
# model's visible answer in half.
DEFAULT_MAX_COMPLETION_TOKENS = 32000
# A 200 answer that stopped here is TRUNCATED, not ok: counted apart, and
# the run exits non-zero (#3460 — raising the cap alone is not enough; the
# UNSIGNALLED truncation is what falsified the measure).
TRUNCATION_FINISH_REASONS = ("length", "max_tokens")

# The analyst prompt is the campaign's starting point, verbatim from the
# existing instrument (#2841: "start from ZEROSHOT_PROMPT in
# run_capstone_c1.py"). Imported, not copied — a copy would drift. Since the
# #2841 retouche it lives in a side-effect-free module, so importing it no
# longer triggers run_capstone_c1's sys.path/chdir/load_dotenv at import time.
from scripts.dataset.zeroshot_prompt import ZEROSHOT_PROMPT  # noqa: E402
from scripts.dataset.run_corpus_batch import (  # noqa: E402
    expand_corpus,
    parse_doc_ids,
)


def load_definitions() -> List[Dict[str, Any]]:
    """Load the encrypted dataset in-memory (#2841 rule 5: never persist)."""
    from dotenv import load_dotenv

    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
    from argumentation_analysis.core.io_manager import load_extract_definitions

    load_dotenv(REPO_ROOT / ".env")
    passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
    if not passphrase:
        raise SystemExit("TEXT_CONFIG_PASSPHRASE not set in .env")
    key = derive_encryption_key(passphrase)
    if not key:
        raise SystemExit("Failed to derive encryption key")
    return load_extract_definitions(
        config_file=DATASET_PATH,
        b64_derived_key=key.decode("utf-8"),
        raise_on_decrypt_error=True,
    )


def resolve_arm_endpoint() -> Dict[str, str]:
    """Route, key and model through the CANONICAL resolver (#2352).

    The pipeline arm resolves through it, so the zero-shot arm must too —
    a raw env read would measure a model production may substitute away.
    """
    from argumentation_analysis.core.llm_service import resolve_chat_endpoint

    api_key, base_url, model_id = resolve_chat_endpoint()
    if not api_key:
        raise SystemExit("no API key resolved — the zero-shot arm needs a real LLM")
    return {"api_key": api_key, "base_url": base_url, "model_id": model_id}


def build_prompt(
    doc_text: str, source_metadata: Optional[Dict[str, Any]] = None
) -> str:
    """The zero-shot prompt on the FULL text — no [:8000] cut.

    The cut was run_capstone_c1's token-budget compromise and is precisely
    what made its baseline unreadable against the pipeline arm (#2841).
    If the context window forces a cut, the CAMPAIGN applies the same cut
    to both arms and states it — not this producer silently.
    """
    prompt = ZEROSHOT_PROMPT.format(text=doc_text)
    if source_metadata is None:
        return prompt
    header = json.dumps(source_metadata, ensure_ascii=False, sort_keys=True)
    return f"Métadonnées de la source : {header}\n\n{prompt}"


def build_payload(
    model_id: str,
    doc_text: str,
    max_completion_tokens: int = DEFAULT_MAX_COMPLETION_TOKENS,
    source_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """One call, no tools, answer allowed to run long."""
    return {
        "model": model_id,
        "messages": [
            {"role": "user", "content": build_prompt(doc_text, source_metadata)}
        ],
        "max_completion_tokens": max_completion_tokens,
    }


def provenance_header(
    model_id: str,
    base_url: str,
    max_chars: int,
    max_completion_tokens: int = DEFAULT_MAX_COMPLETION_TOKENS,
) -> Dict[str, Any]:
    """#2353: the render cites its reproducing command; this is its source."""
    git_head = os.environ.get("GITHUB_SHA", "")
    if not git_head:
        try:
            import subprocess

            git_head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            ).stdout.strip()
        except OSError:
            git_head = "unavailable"
    from urllib.parse import urlparse

    return {
        "producer": "scripts/dataset/run_zeroshot_arm.py (#2841)",
        "campaign": "#2841 zero-shot arm",
        "model": model_id,
        "base_url_host": urlparse(base_url).hostname,
        "max_chars": max_chars,
        "max_completion_tokens": max_completion_tokens,
        "git_head": git_head,
        "command": (
            "PYTHONPATH=. python scripts/dataset/run_zeroshot_arm.py"
            f" --max-chars {max_chars}"
            f" --max-completion-tokens {max_completion_tokens}"
        ),
    }


async def call_zeroshot(
    endpoint: Dict[str, str],
    doc_text: str,
    timeout: int,
    max_completion_tokens: int = DEFAULT_MAX_COMPLETION_TOKENS,
    source_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """One live call; the verdict (status, body head) is returned, never
    swallowed — a failed document is counted failed, not absent (#2841)."""
    import httpx

    payload = build_payload(
        endpoint["model_id"], doc_text, max_completion_tokens, source_metadata
    )
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{endpoint['base_url'].rstrip('/')}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {endpoint['api_key']}"},
        )
    record: Dict[str, Any] = {"status_code": response.status_code}
    if response.status_code == 200:
        body = response.json()
        choice = (body.get("choices") or [{}])[0]
        record["answer"] = choice.get("message", {}).get("content", "")
        record["finish_reason"] = choice.get("finish_reason")
        record["usage"] = body.get("usage", {})
    else:
        record["error_body_head"] = response.text[:500]
    return record


async def run_arm(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="#2841 zero-shot arm")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=0,
        help="Same cut as the pipeline arm (0 = no limit, the campaign's value)",
    )
    parser.add_argument(
        "--timeout", type=int, default=600, help="Per-doc timeout seconds"
    )
    parser.add_argument(
        "--max-completion-tokens",
        type=int,
        default=DEFAULT_MAX_COMPLETION_TOKENS,
        help=(
            f"Completion cap (default {DEFAULT_MAX_COMPLETION_TOKENS}). A "
            "thinking model bills its hidden tokens as completion "
            "(#3096): a cap sized for a non-thinking model cuts the "
            "visible answer — a truncated answer is printed TRUNCATED, "
            "counted apart and fails the run (#3460)"
        ),
    )
    # #3375 — the v1 panel: the same selection as the pipeline arm, parsed by
    # the same helper, so the two populations cannot drift (#2841 rule 4).
    parser.add_argument(
        "--doc-ids",
        default=None,
        help="Comma/whitespace separated document ids — the panel, in order",
    )
    parser.add_argument(
        "--panel-file",
        default=None,
        help="File with one document id per line ('#' comments, blanks ignored)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip documents whose output file already exists (resume)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the ladder (ids, lengths) and exit — no network",
    )
    parser.add_argument(
        "--with-source-header",
        action="store_true",
        help="Prepend the pipeline's source metadata; write to a separate results directory",
    )
    args = parser.parse_args(argv)

    definitions = load_definitions()
    docs, omitted_sources, skipped_too_long = expand_corpus(
        definitions, args.max_chars, parse_doc_ids(args.doc_ids, args.panel_file)
    )

    # The honest denominator, before any call (#1903/#1919 discipline).
    print(f"source definitions: {len(definitions)}", flush=True)
    print(f"omitted sources (no document): {len(omitted_sources)}", flush=True)
    print(f"skipped too long: {skipped_too_long}", flush=True)
    print(f"candidate documents: {len(docs)}", flush=True)

    if args.dry_run:
        for doc in docs:
            print(f"  {doc['opaque_id']}  chars={len(doc['full_text'])}")
        return 0

    results_dir = (
        RESULTS_DIR.with_name(RESULTS_DIR.name + "_with_header")
        if args.with_source_header
        else RESULTS_DIR
    )
    results_dir.mkdir(parents=True, exist_ok=True)
    endpoint = resolve_arm_endpoint()
    header = provenance_header(
        endpoint["model_id"],
        endpoint["base_url"],
        args.max_chars,
        max_completion_tokens=args.max_completion_tokens,
    )
    if args.with_source_header:
        header["command"] += " --with-source-header"
        header["source_header"] = True
    print(f"model: {endpoint['model_id']}", flush=True)
    print(f"max_completion_tokens: {args.max_completion_tokens}", flush=True)

    attempted = 0
    ok = 0
    truncated = 0
    failed = 0
    t_start = time.time()
    for doc in docs:
        out_path = results_dir / f"{doc['opaque_id']}.json"
        if args.skip_existing and out_path.exists():
            print(f"[{doc['opaque_id']}] skip (existing)", flush=True)
            continue
        attempted += 1
        t0 = time.time()
        try:
            kwargs = {"max_completion_tokens": args.max_completion_tokens}
            if args.with_source_header:
                kwargs["source_metadata"] = doc["metadata"]
            record = await call_zeroshot(
                endpoint, doc["full_text"], args.timeout, **kwargs
            )
        except Exception as exc:  # network-level failure: named, never silent
            record = {"status_code": 0, "error_body_head": repr(exc)}
        elapsed = round(time.time() - t0, 1)
        entry = {
            "provenance": header,
            "opaque_id": doc["opaque_id"],
            "chars_in": len(doc["full_text"]),
            "elapsed_seconds": elapsed,
            **record,
        }
        out_path.write_text(
            json.dumps(entry, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        if record.get("status_code") == 200 and record.get("answer"):
            # #3460 — a 200 answer that stopped at the cap is NOT ok: the
            # baseline was cut before its conclusion, and grading it as a
            # whole answer biases every verdict toward the pipeline.
            if str(record.get("finish_reason") or "") in TRUNCATION_FINISH_REASONS:
                truncated += 1
                completion_tokens = (record.get("usage") or {}).get("completion_tokens")
                print(
                    f"[{doc['opaque_id']}] TRUNCATED at "
                    f"{completion_tokens} completion tokens "
                    f"(finish_reason={record.get('finish_reason')}) "
                    f"in {elapsed}s — raise --max-completion-tokens (#3460)",
                    flush=True,
                )
            else:
                ok += 1
                print(f"[{doc['opaque_id']}] ok in {elapsed}s", flush=True)
        else:
            failed += 1
            print(
                f"[{doc['opaque_id']}] FAILED status={record.get('status_code')} "
                f"in {elapsed}s — {record.get('error_body_head', '')[:120]}",
                flush=True,
            )

    print(
        f"attempted: {attempted}  ok: {ok}  truncated: {truncated}  "
        f"failed: {failed}",
        flush=True,
    )
    print(f"wall: {round(time.time() - t_start, 1)}s", flush=True)

    # #2282: the stamp says which model answered.
    from argumentation_analysis.evaluation.env_manifest import (
        environment_manifest,
        render_environment_stamp,
    )

    print(render_environment_stamp(environment_manifest()), flush=True)
    # #3460 — a truncated answer fails the run: the panel B print
    # (« attempted: 10  ok: 10  failed: 0 » with 2 answers cut at the cap)
    # is the failure this line refuses to repeat.
    return 0 if failed == 0 and truncated == 0 else 1


def main() -> int:
    return asyncio.run(run_arm())


if __name__ == "__main__":
    sys.exit(main())
