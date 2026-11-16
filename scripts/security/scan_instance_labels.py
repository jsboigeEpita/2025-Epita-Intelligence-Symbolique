# -*- coding: utf-8 -*-
"""Instance-label privacy probe — the reading side of the runtime derivation (#3575).

Rules 4 and 7 of "Dataset Privacy Discipline" (CLAUDE.md) forbid a document
identifier in any tracked file. ``argumentation_analysis/evaluation/leak_patterns.py``
carries the CLASS half of the detection (generic public vocabulary); the
INSTANCE half — the labels that map 1:1 onto an encrypted document — must
never be listed, so this probe DERIVES it at run time, like
``argumentation_analysis/evaluation/corpus_instance_tokens.py`` does for the
export scrubber (#2187):

* from the encrypted definitions decrypted in memory (rule 5): the ONE
  canonical derivation of ``corpus_instance_tokens`` (#2187) — each
  ``source_name`` whole, plus its capitalised runs — read through
  ``instance_tokens_by_definition`` so the detector and the export scrubber
  share a single father; this probe owns no dataset rule of its own;
* from gitignored recorded panel states (``--from-states``): the players',
  parties' and speaker's names of the persona reads, plus verbatim windows of
  the documents' own text (a --window-character match on normalised text,
  the free-replay quote scan shape of #3613).

Privacy HARD — the output publishes nothing:

* every printed line carries COUNTS and OPAQUE INDICES only (``src3:name0``,
  ``state0:player2:w1``) — never a token's text, and ``Token.__repr__``
  redacts itself so no traceback can leak one either;
* the generic-word filter is MEASURED, not listed: a token whose document
  frequency over the tracked text files reaches ``--df-threshold`` is repo
  vocabulary, not a document label, and is reported as filtered. A curated
  stoplist would have to name the very words rule 7 protects.

Usage::

    # dataset tokens over the whole tracked tree (or over given files)
    python scripts/security/scan_instance_labels.py [--env-file <path>] [FILES ...]

    # recorded-state tokens (players/parties/speaker + text windows); a seat
    # without the passphrase still gates its PR body and diff this way
    python scripts/security/scan_instance_labels.py --from-states <states-dir> FILES ...

Exit codes: 0 clean, 1 hits found (the gate), 2 instrument error — a probe
with no derivable vocabulary, or an unreadable target, is a silent no-op,
the failure mode #2187 rejects, so it refuses to run clean.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

#: Words of a RECORDED state name shorter than this are noise (state channel
#: only; the dataset channel owns no rule — it derives from #2187).
DEFAULT_MIN_WORD_LEN = 6

#: A token found in at least this many tracked text files is repo vocabulary
#: (``df`` = document frequency), not a document label. The threshold is a
#: measurement over the tracked tree, never a list of words.
DEFAULT_DF_THRESHOLD = 10

#: Normalised characters of the documents' own text that count as a verbatim
#: quote (repo-local precedent: the #3613 free-replay scan).
DEFAULT_QUOTE_WINDOW = 28

#: Files whose head contains a NUL byte are binary and never carry a label.
_BINARY_SNIFF = 8192

_NON_ALNUM = re.compile(r"[^a-z0-9]+")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from argumentation_analysis.evaluation.corpus_instance_tokens import (  # noqa: E402
    instance_tokens_by_definition,
)


# --------------------------------------------------------------------------
# Normalisation — the ONE shape every side of every match goes through.
# --------------------------------------------------------------------------
def normalize(text: str) -> str:
    """Case-folded, accent-stripped, alnum+space form of ``text``.

    ``Ïlévanne-Pörtyge`` -> ``ilevanne portyge`` (synthetic example): the
    accentless form a label takes in code or in an ASCII-only export matches
    the accented form of the census (and vice versa). Whitespace collapses to
    single spaces so a re-wrapped quote still matches its window.
    """
    if not text.isascii():
        text = unicodedata.normalize("NFKD", text)
        text = "".join(c for c in text if not unicodedata.combining(c))
    return _NON_ALNUM.sub(" ", text.casefold()).strip()


# --------------------------------------------------------------------------
# Tokens — the derived vocabulary. A Token NEVER prints its text.
# --------------------------------------------------------------------------
@dataclass(frozen=True, repr=False)
class Token:
    """One derived label candidate. ``text`` is normalised and stays private."""

    source: str  # opaque census id: "src3" / "state0"
    kind: str  # "name" | "player" | "party" | "speaker"
    site: int  # position of the name within its site (players list, ...)
    word: int  # -1 = the whole name, >= 0 = that word of it
    text: str

    def __repr__(self) -> str:  # safety net: tracebacks must not leak labels
        return f"Token({self.opaque})"

    @property
    def opaque(self) -> str:
        base = f"{self.source}:{self.kind}{self.site}"
        return base if self.word < 0 else f"{base}:w{self.word}"


def _name_tokens(
    source: str,
    kind: str,
    site: int,
    name: str,
    min_word_len: int,
    seen: set[str],
    out: list[Token],
) -> bool:
    """The whole name plus its distinctive words, deduplicated by text.

    Returns whether anything was added: a duplicate name must not consume a
    site index (the ids of the names after it would shift).
    """
    norm = normalize(name)
    if not norm or norm in seen:
        return False
    seen.add(norm)
    out.append(Token(source, kind, site, -1, norm))
    words = [w for w in norm.split() if len(w) >= min_word_len]
    for j, word in enumerate(words):
        if word in seen:
            continue
        seen.add(word)
        out.append(Token(source, kind, site, j, word))
    return True


def derive_dataset_tokens(definitions: Iterable[Mapping[str, Any]]) -> list[Token]:
    """Instance vocabulary of the census — the #2187 derivation, ONE father.

    The tokens come from ``corpus_instance_tokens.instance_tokens_by_definition``
    (each whole ``source_name`` first, then its capitalised runs): the same
    rule the export scrubber redacts with, so the detector and the scrubber
    cannot drift apart. This probe owns no derivation rule of its own — it
    adds only the match-time shape (``normalize``, the accent fold) and its
    measured generic-word filter. The definitions are already decrypted IN
    MEMORY (rule 5).
    """
    tokens: list[Token] = []
    seen: set[str] = set()
    for k, entry in enumerate(instance_tokens_by_definition(definitions)):
        for j, text in enumerate(entry):
            norm = normalize(text)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            tokens.append(Token(f"src{k}", "name", 0, j - 1, norm))
    return tokens


def derive_state_tokens(
    state: Mapping[str, Any], source: str, min_word_len: int = DEFAULT_MIN_WORD_LEN
) -> list[Token]:
    """Persona-read vocabulary of ONE recorded state.

    Three whitelisted sites carry recorded names: the strategist's players
    (``strategic_read.players[*].name`` — the ``preferences`` dict is keyed by
    the same names, so its keys join the same channel), the stakeholders
    (``stakes_and_stakeholders.stakeholders[*].name``) and the speaker
    (``source_metadata.speaker``). Everything else in a state is either
    covered by the raw-text window channel or is not a name.
    """
    tokens: list[Token] = []
    seen: set[str] = set()

    def mapping(value: Any) -> Mapping[str, Any]:
        return value if isinstance(value, Mapping) else {}

    strategic = mapping(state.get("strategic_read"))
    site = 0
    for player in strategic.get("players") or []:
        if isinstance(player, Mapping) and player.get("name"):
            if _name_tokens(
                source, "player", site, str(player["name"]), min_word_len, seen, tokens
            ):
                site += 1
    for key in mapping(strategic.get("preferences")):
        if _name_tokens(source, "player", site, str(key), min_word_len, seen, tokens):
            site += 1
    stakes = mapping(state.get("stakes_and_stakeholders"))
    site = 0
    for holder in stakes.get("stakeholders") or []:
        if isinstance(holder, Mapping) and holder.get("name"):
            if _name_tokens(
                source, "party", site, str(holder["name"]), min_word_len, seen, tokens
            ):
                site += 1
    speaker = mapping(state.get("source_metadata")).get("speaker")
    if speaker:
        _name_tokens(source, "speaker", 0, str(speaker), min_word_len, seen, tokens)
    return tokens


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------
def _boundary_pattern(text: str) -> re.Pattern[str]:
    return re.compile(r"(?<![a-z0-9])" + re.escape(text) + r"(?![a-z0-9])")


def contains_phrase(content: str, phrase: str) -> bool:
    """Letter-bounded containment: ``esclave`` is not inside ``lesclaves``."""
    start = 0
    while True:
        i = content.find(phrase, start)
        if i < 0:
            return False
        end = i + len(phrase)
        before = content[i - 1] if i > 0 else " "
        after = content[end] if end < len(content) else " "
        if not before.isalnum() and not after.isalnum():
            return True
        start = i + 1


def match_counts(
    norm: str, matchers: Sequence[tuple[Token, re.Pattern[str]]]
) -> dict[str, int]:
    """Opaque id -> occurrence count of every token in normalised text."""
    counts: dict[str, int] = {}
    for token, pattern in matchers:
        n = len(pattern.findall(norm))
        if n:
            counts[token.opaque] = counts.get(token.opaque, 0) + n
    return counts


def window_runs(raw_norm: str, target_norm: str, window: int) -> list[tuple[int, int]]:
    """Maximal spans of ``raw_norm`` whose every ``window``-gram sits in the target.

    One contiguous quoted passage — however long — is ONE run: overlapping
    grams of the same quote must not count as many leaks.
    """
    if window <= 0 or len(raw_norm) < window or len(target_norm) < window:
        return []
    grams = {target_norm[i : i + window] for i in range(len(target_norm) - window + 1)}
    runs: list[tuple[int, int]] = []
    i, n = 0, len(raw_norm)
    while i <= n - window:
        if raw_norm[i : i + window] in grams:
            j = i
            while j <= n - window and raw_norm[j : j + window] in grams:
                j += 1
            runs.append((i, j - 1 + window))
            i = j
        i += 1
    return runs


# --------------------------------------------------------------------------
# File reading + document frequency (the measured noise floor)
# --------------------------------------------------------------------------
def read_normalised(path: Path) -> str | None:
    """Normalised text of a file, or None when binary/unreadable."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:_BINARY_SNIFF]:
        return None
    return normalize(data.decode("utf-8", errors="replace"))


def document_frequencies(
    token_texts: Iterable[str], baseline: Sequence[Path]
) -> dict[str, int]:
    """File count of each token text over the tracked tree — the noise floor."""
    df: dict[str, int] = {text: 0 for text in token_texts}
    phrases = [t for t in df if " " in t]
    words = {t for t in df if " " not in t}
    for path in baseline:
        norm = read_normalised(path)
        if norm is None:
            continue
        for text in phrases:
            if contains_phrase(norm, text):
                df[text] += 1
        if words:
            file_words = set(norm.split())
            for text in words:
                if text in file_words:
                    df[text] += 1
    return df


def tracked_files(root: Path) -> list[Path]:
    """``git ls-files`` of the checkout at ``root``, as absolute paths."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            f"git ls-files failed under {root}: {type(exc).__name__}"
        ) from exc
    return [root / p.decode("utf-8", errors="replace") for p in out.split(b"\x00") if p]


# --------------------------------------------------------------------------
# The probe itself
# --------------------------------------------------------------------------
@dataclass
class FileHit:
    path: Path
    labels: dict[str, int] = field(default_factory=dict)  # opaque id -> count
    windows: dict[str, tuple[int, int]] = field(
        default_factory=dict
    )  # id -> (runs, chars)


@dataclass
class ProbeResult:
    vocabulary_size: int = 0
    window_channels: int = 0
    baseline_files: int = 0
    skipped_binary: int = 0
    scanned: int = 0
    live_ids: list[str] = field(default_factory=list)
    generic_ids: list[str] = field(default_factory=list)
    hits: list[FileHit] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def label_matches(self) -> int:
        return sum(sum(h.labels.values()) for h in self.hits)

    @property
    def window_runs_total(self) -> int:
        return sum(runs for h in self.hits for runs, _ in h.windows.values())

    @property
    def has_hits(self) -> bool:
        return bool(self.hits)


def scan_content(
    norm: str,
    matchers: Sequence[tuple[Token, re.Pattern[str]]],
    raw_texts: Sequence[tuple[str, str]],  # (state id, normalised raw_text)
    window: int,
) -> tuple[dict[str, int], dict[str, tuple[int, int]]]:
    """Label counts + window runs of one normalised target text."""
    labels = match_counts(norm, matchers)
    windows: dict[str, tuple[int, int]] = {}
    for state_id, raw_norm in raw_texts:
        runs = window_runs(raw_norm, norm, window)
        if runs:
            chars = sum(end - start for start, end in runs)
            windows[f"{state_id}:window"] = (len(runs), chars)
    return labels, windows


def run_probe(
    *,
    baseline: Sequence[Path],
    targets: Sequence[Path],
    definitions: Sequence[Mapping[str, Any]] | None = None,
    states: Sequence[Mapping[str, Any]] | None = None,
    df_threshold: int = DEFAULT_DF_THRESHOLD,
    min_word_len: int = DEFAULT_MIN_WORD_LEN,
    window: int = DEFAULT_QUOTE_WINDOW,
    use_df_filter: bool = True,
) -> ProbeResult:
    """Scan ``targets`` for the derived vocabulary; ``baseline`` sets the df floor.

    Pure with respect to the census: the caller hands over already-decrypted
    definitions / already-loaded states, so a test feeds synthetic ones and
    the mechanism stays identical on both sides.
    """
    result = ProbeResult()
    tokens: list[Token] = []
    raw_texts: list[tuple[str, str]] = []
    if definitions is not None:
        tokens.extend(derive_dataset_tokens(definitions))
    for i, state in enumerate(states or []):
        sid = f"state{i}"
        tokens.extend(derive_state_tokens(state, sid, min_word_len))
        raw = state.get("raw_text")
        if isinstance(raw, str) and normalize(raw):
            raw_texts.append((sid, normalize(raw)))
    result.vocabulary_size = len(tokens)
    result.window_channels = len(raw_texts)
    if not tokens and not raw_texts:
        result.errors.append("no vocabulary derivable — refusing to run clean")
        return result

    if use_df_filter and tokens:
        df = document_frequencies({t.text for t in tokens}, baseline)
        live = [t for t in tokens if df.get(t.text, 0) < df_threshold]
        generic = [t for t in tokens if df.get(t.text, 0) >= df_threshold]
    else:
        live, generic = tokens, []
    result.live_ids = [t.opaque for t in live]
    result.generic_ids = [t.opaque for t in generic]
    matchers = [(t, _boundary_pattern(t.text)) for t in live]

    pending = {p.resolve(): p for p in targets}
    result.baseline_files = len(baseline)
    baseline_resolved = {p.resolve() for p in baseline}

    def scan_path(path: Path) -> None:
        if not path.exists():
            result.errors.append(f"target not found: {path}")
            return
        norm = read_normalised(path)
        if norm is None:
            result.skipped_binary += 1
            return
        result.scanned += 1
        labels, windows = scan_content(norm, matchers, raw_texts, window)
        if labels or windows:
            result.hits.append(FileHit(path, labels, windows))

    for path in baseline:  # one read serves the df floor and the scan
        resolved = path.resolve()
        if resolved in pending:
            scan_path(path)
            del pending[resolved]
    for path in pending.values():  # targets outside the tree (a PR body, a diff)
        scan_path(path)
    return result


# --------------------------------------------------------------------------
# CLI — the glue that owns the secrets, never prints them
# --------------------------------------------------------------------------
def load_definitions_from_env(
    root: Path, env_file: Path
) -> tuple[list[dict] | None, str]:
    """Decrypt the census in memory (rule 5); (None, reason) on any failure."""
    from dotenv import load_dotenv  # deferred: tests run without python-dotenv

    if env_file.exists():
        load_dotenv(env_file, override=False)
    passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
    if not passphrase:
        return (
            None,
            f"no TEXT_CONFIG_PASSPHRASE (looked at {env_file.name} and the environment)",
        )
    sys.path.insert(0, str(root))
    from argumentation_analysis.core.io_manager import load_extract_definitions
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key

    key = derive_encryption_key(passphrase)
    if not key:
        return None, "key derivation failed"
    config_file = (
        root / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"
    )
    if not config_file.exists():
        return None, f"encrypted dataset missing at {config_file.name}"
    try:
        definitions = load_extract_definitions(
            config_file=config_file,
            b64_derived_key=key.decode("utf-8"),
            raise_on_decrypt_error=True,
        )
    except Exception as exc:  # the message never carries decrypted content
        return None, f"dataset load failed ({type(exc).__name__})"
    if not definitions:
        return None, "dataset loaded but carried no definition"
    return definitions, ""


def load_states(states_dir: Path) -> tuple[list[dict] | None, str]:
    paths = sorted(states_dir.glob("*.json")) if states_dir.is_dir() else []
    if not paths:
        return None, f"no state file under {states_dir}"
    states: list[dict] = []
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, ValueError) as exc:
            return None, f"unreadable state {path.name} ({type(exc).__name__})"
        states.append(data if isinstance(data, dict) else {})
    return states, ""


def _print_result(result: ProbeResult, root: Path) -> None:
    print(
        f"[probe] baseline: {result.baseline_files} files "
        f"({result.skipped_binary} binary/unreadable skipped)"
    )
    if result.generic_ids:
        print(
            f"[probe] generic-word filter: {len(result.generic_ids)} token(s) at or above "
            f"the document-frequency threshold -> not searched"
        )
    print(
        f"[probe] live tokens: {len(result.live_ids)} "
        f"(vocabulary {result.vocabulary_size}, window channels {result.window_channels}); "
        f"scanned: {result.scanned}"
    )
    for hit in result.hits:
        parts = [f"{opaque} x{n}" for opaque, n in sorted(hit.labels.items())]
        for opaque, (runs, chars) in sorted(hit.windows.items()):
            parts.append(f"{opaque} x{runs} ({chars} chars)")
        shown = ", ".join(parts[:8]) + (", ..." if len(parts) > 8 else "")
        try:
            shown_path = hit.path.relative_to(root)
        except ValueError:
            shown_path = hit.path
        print(f"[HIT] {shown_path}: {len(parts)} token match(es) — {shown}")
    for error in result.errors:
        print(f"[probe] {error}")
    print(
        f"[probe] summary: {len(result.hits)} file(s) hit, "
        f"{result.label_matches} label match(es), "
        f"{result.window_runs_total} window run(s)"
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "files", nargs="*", help="targets (default: every tracked text file)"
    )
    parser.add_argument(
        "--from-states",
        type=Path,
        default=None,
        help="dir of recorded panel states (*.json) — adds the "
        "persona-read names and the raw-text windows; works "
        "without the passphrase",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help=".env holding TEXT_CONFIG_PASSPHRASE (default: <repo>/.env)",
    )
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument(
        "--df-threshold",
        type=int,
        default=DEFAULT_DF_THRESHOLD,
        help="a token in >= N tracked text files is generic (default: %(default)s)",
    )
    parser.add_argument(
        "--min-word-len",
        type=int,
        default=DEFAULT_MIN_WORD_LEN,
        help="state channel only: shortest word of a recorded name kept as a "
        "token (the dataset channel derives from #2187; default: %(default)s)",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=DEFAULT_QUOTE_WINDOW,
        help="normalised chars of document text that count as a quote "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--no-df-filter",
        action="store_true",
        help="search every token, generic ones included (measuring the floor)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root: Path = args.repo_root
    try:
        baseline = tracked_files(root)
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        return 2

    definitions, defs_note = load_definitions_from_env(
        root, args.env_file or (root / ".env")
    )
    states, states_note = (None, "")
    if args.from_states is not None:
        states, states_note = load_states(args.from_states)
    for note in (defs_note, states_note):
        if note:
            print(f"[probe] {note}")
    if definitions is None and states is None:
        print(
            "[FAIL] no vocabulary source: fix the errors above (#2187 — refusing to run clean)"
        )
        return 2
    if definitions is None:
        print("[probe] dataset tokens skipped — running on state tokens only")

    targets = [Path(f) for f in args.files] or baseline
    result = run_probe(
        baseline=baseline,
        targets=targets,
        definitions=definitions,
        states=states,
        df_threshold=args.df_threshold,
        min_word_len=args.min_word_len,
        window=args.window,
        use_df_filter=not args.no_df_filter,
    )
    _print_result(result, root)
    if result.errors:
        print("[FAIL] instrument error — the run does not certify a clean tree")
        return 2
    return 1 if result.has_hits else 0


if __name__ == "__main__":
    sys.exit(main())
