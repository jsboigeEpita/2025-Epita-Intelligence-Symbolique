"""FP-16 #1231 — re-run formal matrix post-#1230 + enumerate ALL remaining
MlParser-illegal modal constructs in one diagnostic pass (Epic #1191).

#1230 (main ``b5023ca8``) normalizes MlParser-illegal predicate names: every
atom not matching the predicate grammar ``[a-zA-Z][a-zA-Z0-9]*`` is mapped to a
fresh legal ``mpN`` symbol, consistently across ``type(...)`` declarations and
formula bodies. This harness measures whether the modal cell finally moves
``degraded``/``error`` → ``real-verdict`` on the 3 real corpora end-to-end — and
if it still degrades, breaks the one-residual-per-round loop by enumerating the
FULL remaining illegal set at once (scope step 3 of the issue).

How the anti-loop enumeration works: ``MlParser.parseBeliefBase`` raises on the
FIRST illegal construct and ``is_modal_kb_consistent`` catches it → ``valid=None``
— so a plain re-run only ever surfaces ONE rejection per corpus. To get the whole
set, this harness:
  1. runs the real spectacular+full pipeline per corpus (the DoD matrix re-run),
  2. takes the modal phase output's real ``formulas`` (the ``nl_to_logic``
     translations the pipeline actually built its KB from),
  3. replays them through a VERBATIM copy of the #1230 KB-construction logic
     (kept byte-aligned with ``_invoke_modal_logic``'s nl-path),
  4. validates the resulting belief base against the LIVE ``MlParser`` — first the
     whole KB (matching the pipeline's ``valid``), then each ``type(...)``
     declaration and each formula INDIVIDUALLY — so every rejection is captured,
     not just the first the parser hit.

Privacy HARD (R463 lesson — sharp): ParserException / "Illegal characters"
excerpts echo raw corpus tokens verbatim — a leak BY CONSTRUCTION. This harness
NEVER emits a real token: each illegal construct is classified by *type*
(leading-digit / accented / underscore / multi-word / other-punctuation /
reserved-token) with the real token held only in-memory. The corpus redact-filter
from the FP-5 runner is reused over all stdout/logging. Raw per-construct dumps
(if any) stay gitignored under ``evaluation/results/fp5/``.

Anti-pendule: do NOT relabel ``degraded`` as ``real-verdict`` without a captured
solver verdict; do NOT skip-everywhere. If modal still can't decide, the FULL
enumerated residual set IS the deliverable.
"""

import os
import re
import sys
import json
import asyncio
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Reuse the FP-5 runner's redact infra, classifier, CAPABILITIES, CORPORA and
# corpus loader — the matrix half of this harness IS the FP-5 matrix, so importing
# guarantees identical classification. (Importing also installs the redact stream
# + .env load as a module side effect — intended.)
import run_fp5_formal_matrix as fp5  # noqa: E402

RESULTS_DIR = fp5.RESULTS_DIR

# ── #1230 KB construction — VERBATIM copy of _invoke_modal_logic's nl-path ──
# Kept byte-aligned with argumentation_analysis/orchestration/invoke_callables.py
# (~5763-5850). The enumeration is only faithful if this matches production; any
# drift here would measure a different KB than the pipeline builds.
_KEYWORD_ATOMS = {
    "forall",
    "exists",
    "true",
    "false",
    "type",
    "prop",
    "and",
    "or",
    "not",
    "implies",
}
_ATOM_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_MLPARSER_LEGAL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9]*$")


def _build_modal_kb_1230(nl_formulas: "list[str]") -> "tuple[str, list[str], list[str]]":
    """Reproduce the #1230 nl-path: sanitize → map illegal atoms to mpN →
    declare type(atom). Returns (belief_set_str, declarations, kb_formulas)."""
    kb_formulas: "list[str]" = list(nl_formulas)
    try:
        from argumentation_analysis.agents.core.logic.pl_formula_sanitizer import (
            PLFormulaSanitizer,
        )

        sanitizer = PLFormulaSanitizer()
        san_result = sanitizer.sanitize_batch(nl_formulas)
        if san_result.sanitized_formulas:
            kb_formulas = san_result.sanitized_formulas
    except Exception:
        pass

    _legal_atoms = {
        tok
        for f in kb_formulas
        for tok in _ATOM_RE.findall(str(f))
        if tok not in _KEYWORD_ATOMS and _MLPARSER_LEGAL_RE.match(tok)
    }
    _atom_symbol: "dict[str, str]" = {}
    _symbol_counter = 0

    def _legal_symbol(atom: str) -> str:
        nonlocal _symbol_counter
        if atom in _KEYWORD_ATOMS or _MLPARSER_LEGAL_RE.match(atom):
            return atom
        if atom not in _atom_symbol:
            _symbol_counter += 1
            candidate = f"mp{_symbol_counter}"
            while candidate in _legal_atoms:
                _symbol_counter += 1
                candidate = f"mp{_symbol_counter}"
            _atom_symbol[atom] = candidate
        return _atom_symbol[atom]

    kb_formulas = [
        _ATOM_RE.sub(lambda m: _legal_symbol(m.group(0)), str(f)) for f in kb_formulas
    ]
    _seen: "dict[str, None]" = {}
    for f in kb_formulas:
        for tok in _ATOM_RE.findall(str(f)):
            if tok not in _KEYWORD_ATOMS and tok not in _seen:
                _seen[tok] = None
    declarations = [f"type({atom})" for atom in _seen]
    belief_set_str = "\n".join(declarations + [str(f) for f in kb_formulas])
    return belief_set_str, declarations, kb_formulas


# ── Construct classification (opaque — never emits a real token) ──
_TWEETY_RESERVED = _KEYWORD_ATOMS | {"type"}


def _classify_construct(tok: str) -> str:
    """Classify an MlParser-illegal token by construct TYPE (privacy: the token
    itself is never returned/logged, only its class)."""
    if _MLPARSER_LEGAL_RE.match(tok):
        return "legal"
    if tok and tok[0].isdigit():
        return "leading-digit"
    if any(ord(c) > 127 for c in tok):
        return "accented/non-ascii"
    if "_" in tok:
        return "underscore"  # should be 0 post-#1230
    if any(c.isspace() for c in tok):
        return "multi-word"
    if tok in _TWEETY_RESERVED:
        return "reserved-token"
    return "other-punctuation"


def _illegal_tokens_in(text: str) -> "list[str]":
    """All whitespace/operator-delimited tokens in a formula body that are NOT
    MlParser-legal predicate identifiers (and not pure modal/logical operators)."""
    # split on operators + parens + whitespace; keep word-ish chunks
    raw = re.split(r"[\s()\[\]<>!&|=>~,;]+", text)
    bad = []
    for t in raw:
        t = t.strip()
        if not t or t in _KEYWORD_ATOMS:
            continue
        if _MLPARSER_LEGAL_RE.match(t):
            continue
        bad.append(t)
    return bad


def _enumerate_modal_rejections(
    nl_formulas: "list[str]", modal_parser, jpype_mod
) -> dict:
    """Replay the #1230 KB through the live MlParser; enumerate EVERY remaining
    illegal construct.

    Two complementary signals:
      * ``kb_parses`` — the AUTHORITATIVE decidability signal: does the full
        constructed belief base parse? This matches the pipeline's modal
        ``valid`` non-None-ness (same formulas, same #1230 construction, same
        ``parseBeliefBase``). True ⇒ modal decides.
      * ``illegal_by_type`` — a STATIC scan of the constructed KB for any
        predicate-position token that violates the MlParser grammar
        ``[a-zA-Z][a-zA-Z0-9]*`` after the #1230 mpN-substitution. When #1230
        fully covers the corpus this is empty and agrees with ``kb_parses=True``;
        when a residual class survives (a construct ``_atom_re`` never captured —
        accents, leading digits, stray punctuation), ``kb_parses=False`` and this
        lists the FULL residual set by type — the anti-loop deliverable.

    A lone ``type(...)`` line is NOT a valid standalone belief base (MlParser
    needs formulas too), so we do NOT test declarations individually (that gave
    false "bad declaration" positives). The whole-KB parse + static token scan is
    both correct and faithful. No raw token ever leaves this function — only
    construct *types*.
    """
    belief_set_str, declarations, kb_formulas = _build_modal_kb_1230(nl_formulas)
    StringReader = jpype_mod.JClass("java.io.StringReader")

    whole_parses = True
    parse_error_class = None
    try:
        modal_parser.parseBeliefBase(StringReader(belief_set_str))
    except Exception as e:  # privacy: class name only — the message echoes tokens
        whole_parses = False
        parse_error_class = type(e).__name__

    # Static residual scan over the CONSTRUCTED KB (post #1230 substitution).
    distinct_illegal: "set[str]" = set()  # in-memory only, never emitted
    for decl in declarations:
        m = re.match(r"^type\((.+)\)$", decl)
        if m and not _MLPARSER_LEGAL_RE.match(m.group(1)):
            distinct_illegal.add(m.group(1))
    for f in kb_formulas:
        for tok in _illegal_tokens_in(str(f)):
            distinct_illegal.add(tok)

    type_counts: "dict[str, int]" = {}
    for tok in distinct_illegal:
        cls = _classify_construct(tok)
        type_counts[cls] = type_counts.get(cls, 0) + 1

    return {
        "kb_parses": whole_parses,
        "parse_error_class": parse_error_class,
        "n_declarations": len(declarations),
        "n_formulas": len(kb_formulas),
        "distinct_illegal_constructs": len(distinct_illegal),
        "illegal_by_type": type_counts,  # opaque: construct-type → count
    }


async def run_corpus(label: str, idx: int, timeout: int, corpus_texts: dict) -> dict:
    """Run the spectacular+full pipeline (DoD matrix re-run), classify all cells
    with the FP-5 classifier, and run the modal anti-loop enumeration."""
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    text = fp5.load_corpus_text(label, idx)
    corpus_texts[label] = text
    print(
        f"[FP-16] doc_{label}: {len(text)} chars | spectacular+full | ceiling {timeout}s"
    )

    t0 = time.time()
    verdict = "UNKNOWN"
    result: dict = {}
    try:
        result = await asyncio.wait_for(
            run_unified_analysis(
                text, workflow_name="spectacular", context={"fallacy_tier": "full"}
            ),
            timeout=float(timeout),
        )
        verdict = "COMPLETED"
    except asyncio.TimeoutError:
        verdict = f"TIMED_OUT_{timeout}s"
        print(f"[FP-16] doc_{label} TIMED OUT after {timeout}s.")
    except Exception as exc:
        verdict = f"ERROR:{type(exc).__name__}"
        print(f"[FP-16] doc_{label} {verdict}: {fp5._redact(str(exc))[:160]}")
    elapsed = time.time() - t0

    # Matrix cells via the SAME classifier as FP-5 (identical classification).
    matrix = {}
    for cap, phase, count_key in fp5.CAPABILITIES:
        cls, ev = fp5._classify_capability(result, phase, count_key)
        matrix[cap] = {"class": cls, "evidence": ev}

    # Modal cell verdict shape (from the real pipeline output).
    modal_pr = fp5._phase(result, "modal")
    modal_out = getattr(modal_pr, "output", None) if modal_pr else None
    modal_valid = modal_out.get("valid") if isinstance(modal_out, dict) else None
    modal_solver = modal_out.get("solver") if isinstance(modal_out, dict) else None
    modal_fabricated_true = bool(
        isinstance(modal_out, dict) and modal_out.get("valid") is True
    )

    # Anti-loop enumeration: replay the REAL modal formulas through #1230 + live MlParser.
    enum: dict = {"ran": False, "reason": "no modal formulas"}
    # Source the KB-input formulas the SAME way production does (#1224, invoke_callables
    # ~5755-5761): the valid ``nl_to_logic`` translations. These exist even when the
    # modal PHASE itself failed (``status=failed``) before exposing its own
    # ``formulas`` — which is precisely the FP-16 case (modal raises on a URL /
    # prose construct). The old path read ``modal_out["formulas"]`` only, so the
    # enumeration never ran on the very corpora where modal can't decide.
    nl_formulas = []
    nl_pr = fp5._phase(result, "nl_to_logic")
    nl_out = getattr(nl_pr, "output", None) if nl_pr else None
    if isinstance(nl_out, dict):
        nl_formulas = [
            str(t["formula"])
            for t in (nl_out.get("translations") or [])
            if isinstance(t, dict) and t.get("is_valid") and t.get("formula")
        ]
    if not nl_formulas and isinstance(modal_out, dict):
        # Fallback: a modal phase that DID expose formulas (direct-KB / older path).
        nl_formulas = [str(f) for f in (modal_out.get("formulas") or []) if str(f).strip()]
    if nl_formulas:
        try:
            import jpype
            from argumentation_analysis.core.jvm_setup import initialize_jvm
            from argumentation_analysis.agents.core.logic.tweety_initializer import (
                TweetyInitializer,
            )

            initialize_jvm()
            initz = TweetyInitializer()
            initz.initialize_modal_components()
            modal_parser = initz.get_modal_parser()
            if modal_parser is not None:
                enum = _enumerate_modal_rejections(nl_formulas, modal_parser, jpype)
                enum["ran"] = True
            else:
                enum = {"ran": False, "reason": "modal parser None"}
        except Exception as exc:
            enum = {"ran": False, "reason": f"{type(exc).__name__}: {fp5._redact(str(exc))[:120]}"}

    metrics = {
        "corpus": f"doc_{label}",
        "verdict": verdict,
        "elapsed_s": round(elapsed, 1),
        "modal_class": matrix["modal"]["class"],
        "modal_valid": modal_valid,
        "modal_solver": modal_solver,
        "modal_fabricated_true": modal_fabricated_true,
        "modal_enumeration": enum,
        "matrix": matrix,
    }

    ts = time.strftime("%Y%m%dT%H%M%S")
    raw_out = RESULTS_DIR / f"fp16_doc{label}_{ts}.json"
    try:
        with open(raw_out, "w", encoding="utf-8") as f:
            json.dump(
                {"metrics": metrics, "state_snapshot": result.get("state_snapshot")},
                f,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        print(f"[FP-16] doc_{label} raw saved -> {raw_out.name} (gitignored)")
    except Exception as exc:
        print(f"[FP-16] doc_{label} raw save failed: {type(exc).__name__}")

    tally: "dict[str, int]" = {}
    for row in matrix.values():
        tally[row["class"]] = tally.get(row["class"], 0) + 1
    print(
        f"[FP-16] doc_{label} DONE: {verdict} ({metrics['elapsed_s']}s) | "
        f"modal={metrics['modal_class']} valid={modal_valid} solver={modal_solver} | "
        f"enum={enum.get('illegal_by_type') if enum.get('ran') else enum.get('reason')} | "
        f"classes={tally}"
    )
    return metrics


async def amain() -> None:
    print("=" * 72)
    print("[FP-16] #1231 modal matrix re-run + illegal-construct enumeration")
    print("=" * 72)
    corpus_texts: dict = {}
    all_metrics = []
    # ``FP16_CORPORA=A`` (comma-separated labels) restricts the run. The modal
    # construct enumeration only needs corpora where the pipeline actually REACHES
    # the modal phase; doc_C/doc_B time out upstream of modal (modal=absent), so
    # re-running just doc_A captures the modal-illegal set without paying their
    # ceilings — and avoids doc_B's JPype hang (asyncio.wait_for can't cancel an
    # in-flight JVM call). Empty/unset = all 3 (the full matrix).
    _only = {c.strip().upper() for c in os.environ.get("FP16_CORPORA", "").split(",") if c.strip()}
    corpora = [c for c in fp5.CORPORA if (not _only or c[0].upper() in _only)]
    if _only:
        print(f"[FP-16] corpus filter FP16_CORPORA={sorted(_only)} -> running {[c[0] for c in corpora]}")
    for label, idx, timeout in corpora:
        try:
            m = await run_corpus(label, idx, timeout, corpus_texts)
        except Exception as exc:
            m = {
                "corpus": f"doc_{label}",
                "verdict": f"FATAL:{type(exc).__name__}",
                "error": fp5._redact(str(exc))[:200],
            }
            print(f"[FP-16] doc_{label} FATAL: {fp5._redact(str(exc))[:160]}")
        all_metrics.append(m)

    agg = RESULTS_DIR / f"fp16_matrix_{time.strftime('%Y%m%dT%H%M%S')}.json"
    with open(agg, "w", encoding="utf-8") as f:
        json.dump(all_metrics, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n[FP-16] aggregate saved -> {agg.name} (gitignored)")

    print("\n" + "=" * 72)
    print("[FP-16] MODAL SUMMARY (post-#1230)")
    print("=" * 72)
    for m in all_metrics:
        e = m.get("modal_enumeration", {})
        print(
            f"  {m.get('corpus')}: class={m.get('modal_class')} "
            f"valid={m.get('modal_valid')} solver={m.get('modal_solver')} "
            f"fabricated_true={m.get('modal_fabricated_true')}"
        )
        if e.get("ran"):
            print(
                f"      KB_parses={e.get('kb_parses')} parse_error={e.get('parse_error_class')} "
                f"decls={e.get('n_declarations')} formulas={e.get('n_formulas')} "
                f"distinct_illegal={e.get('distinct_illegal_constructs')} "
                f"by_type={e.get('illegal_by_type')}"
            )
        else:
            print(f"      enumeration not run: {e.get('reason')}")


if __name__ == "__main__":
    asyncio.run(amain())
