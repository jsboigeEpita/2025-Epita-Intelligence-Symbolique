# -*- coding: utf-8 -*-
"""#1912 — the single native-Dung decoder shared by Acts II and III.

Every formalism lives under the same ``state.dung_frameworks`` container:
native Dung verification entries (``verification_{semantics}``, written by
``_write_dung_extensions_to_state``) sit next to ABA / ADF / SetAF /
weighted / social / EAF / DeLP sidecars, each carrying its own extension
shape (``aba_extensions``, ``setaf_extensions``, ``social_ranking``, …).

Both act plugins used to decode that container with a generic resolver that
treated **any** entry as native Dung: a sidecar shape the resolver did not
understand collapsed to ``accepted = ∅`` and every sidecar argument was
reported rejected by Dung — 221 false rejections measured on the real
corpus (#1894 forensic), contaminating 35/35 documents and invalidating the
whole Dung axis of the verdict.

The boundary this module draws (predicted by the #1648 inventory): the
defect is at the READER, not the producer —

- only ``verification_*`` entries are native Dung evidence; sidecars keep
  their formalism-specific readers and are skipped here, whatever their
  shape, without being removed from the state;
- a native extension shape the decoder does not recognize is
  **non-concluable**: it contributes no rejection and says so. It never
  collapses to ``accepted = ∅`` (which would reject every argument) and
  never fabricates a guessed set;
- a *decodable* empty extension (``{"all_members": []}``) remains a genuine
  verdict — the solver accepted nothing, so the arguments are really
  rejected. Honesty about shape is not hesitation about verdicts.

All IDs opaque (arg_N) — privacy HARD.
"""

from __future__ import annotations

from typing import Any, Dict, List, NamedTuple, Optional, Set


class NativeDungDecoding(NamedTuple):
    """Result of decoding a state's native Dung frameworks.

    ``rejected_by_arg`` maps opaque arg_id → semantics label for arguments
    present in a native framework but absent from its accepted extension.
    ``non_concluable`` lists the semantics labels of native frameworks whose
    extension shape could not be decoded (honest unknown — no verdict).
    """

    rejected_by_arg: Dict[str, str]
    non_concluable: List[str]


def is_native_dung_framework(fw: Any) -> bool:
    """True only for native Dung verification entries.

    The writer folds the semantics into ``name=f"verification_{semantics}"``
    (``state_writers._write_dung_extensions_to_state``). Sidecar writers use
    their own prefixes (``aba_``, ``setaf_``, ``weighted_``, ``social_af``,
    …) — an entry carrying one of those names is a different formalism
    sharing the container, never native Dung evidence.
    """
    if not isinstance(fw, dict):
        return False
    name = str(fw.get("name", "") or "")
    return name.startswith("verification_")


def native_semantics_label(fw: Dict[str, Any]) -> str:
    """Recover the semantics label of a native framework.

    Finding D (#1151/#1153): ``add_dung_framework`` stores no ``semantics``
    key — the writer folds it into ``name``. An explicit key wins when
    present; else parse it back from the name; only default to ``grounded``
    when neither carries a signal.
    """
    sem = fw.get("semantics")
    if not sem:
        name = str(fw.get("name", "") or "")
        if name.startswith("verification_"):
            sem = name[len("verification_") :]
    return str(sem or "grounded")


def decode_accepted_members(ext: Any) -> Optional[Set[str]]:
    """Decode a native framework's extension into its accepted members.

    Returns ``None`` when the shape is unknown or malformed — the honest
    non-concluable signal. Returns a possibly-empty set for any decodable
    shape: ``set()`` means the solver genuinely accepted nothing.

    Decodable shapes: the canonical ``{"all_members": [...]}`` dict; a
    non-empty dict whose every value is a list of strings or lists of
    strings (multi-extension semantics, read as the union); a list of
    strings or lists of strings. Anything else — empty dict, non-list
    values, non-string items — is unknown.
    """
    if isinstance(ext, dict):
        if "all_members" in ext:
            members = ext.get("all_members")
            if not isinstance(members, list):
                return None
            return {m for m in members if isinstance(m, str)}
        if not ext:
            return None
        accepted: Set[str] = set()
        for val in ext.values():
            if not isinstance(val, list):
                return None
            for item in val:
                if isinstance(item, str):
                    accepted.add(item)
                elif isinstance(item, list):
                    accepted.update(x for x in item if isinstance(x, str))
                else:
                    return None
        return accepted
    if isinstance(ext, list):
        accepted = set()
        for item in ext:
            if isinstance(item, str):
                accepted.add(item)
            elif isinstance(item, list):
                accepted.update(x for x in item if isinstance(x, str))
            else:
                return None
        return accepted
    return None


def decode_native_dung(state: Any) -> NativeDungDecoding:
    """Decode ONLY the native verification_* Dung frameworks of a state.

    Sidecar entries (ABA/ADF/SetAF/weighted/social/EAF/DeLP) are skipped
    whatever their shape: reading their extension as native acceptance is
    the fabrication #1912 repairs. They stay in the state, untouched, for
    their formalism-specific readers.
    """
    rejected: Dict[str, str] = {}
    non_concluable: List[str] = []
    frameworks = getattr(state, "dung_frameworks", {}) or {}
    if not isinstance(frameworks, dict):
        return NativeDungDecoding(rejected, non_concluable)
    for _fid, fw in frameworks.items():
        if not is_native_dung_framework(fw):
            continue
        fw_args = fw.get("arguments", []) or []
        if not isinstance(fw_args, list):
            continue
        accepted = decode_accepted_members(fw.get("extensions"))
        if accepted is None:
            non_concluable.append(native_semantics_label(fw))
            continue
        label = native_semantics_label(fw)
        for arg in fw_args:
            if isinstance(arg, str) and arg not in accepted:
                rejected.setdefault(arg, label)
    return NativeDungDecoding(rejected, non_concluable)


def select_primary_native(frameworks: Any) -> Optional[Dict[str, Any]]:
    """Pick the primary native framework: preferred → grounded → first.

    The trace surfaces one extension to the reader; this mirrors the
    semantics the pipeline treats as primary. Returns ``None`` when no
    ``verification_*`` entry exists (honest absence — the caller reports
    the Dung axis unavailable rather than fabricating one).
    """
    if not isinstance(frameworks, dict):
        return None
    for pref in ("preferred", "grounded"):
        for _fid, fw in frameworks.items():
            if isinstance(fw, dict) and str(fw.get("name", "") or "") == (
                f"verification_{pref}"
            ):
                return fw
    for _fid, fw in frameworks.items():
        if is_native_dung_framework(fw):
            return fw
    return None
