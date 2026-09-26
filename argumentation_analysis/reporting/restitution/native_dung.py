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

from typing import Any, Dict, List, NamedTuple, Optional, Set, Tuple


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
            if not all(isinstance(m, str) for m in members):
                return None
            return set(members)
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
                    for x in item:
                        if not isinstance(x, str):
                            return None
                        accepted.add(x)
                else:
                    return None
        return accepted
    if isinstance(ext, list):
        accepted = set()
        for item in ext:
            if isinstance(item, str):
                accepted.add(item)
            elif isinstance(item, list):
                for x in item:
                    if not isinstance(x, str):
                        return None
                    accepted.add(x)
            else:
                return None
        return accepted
    return None


def rejected_from_framework(
    fw: Dict[str, Any], accepted: Optional[Set[str]] = None
) -> Optional[Dict[str, str]]:
    """Rejections of ONE native framework: its own arguments absent from its
    own accepted extension, labeled with ITS semantics.

    Single home of the rejection rule: ``decode_native_dung`` aggregates it
    per ``verification_*`` entry, and the Act II primary trace applies it to
    the primary framework alone — a trace announcing one semantics must never
    carry another framework's rejections (R868 rework: the aggregate measured
    ``semantics=preferred, accepted=[arg_1, arg_2], rejected={arg_2:
    grounded}`` with zero sidecars). Returns ``None`` only when ``accepted``
    is not provided and the extension shape is undecodable (non-concluable).
    """
    if not is_native_dung_framework(fw):
        return {}
    if accepted is None:
        accepted = decode_accepted_members(fw.get("extensions"))
        if accepted is None:
            return None
    fw_args = fw.get("arguments", []) or []
    if not isinstance(fw_args, list):
        return {}
    label = native_semantics_label(fw)
    return {
        arg: label for arg in fw_args if isinstance(arg, str) and arg not in accepted
    }


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
        accepted = decode_accepted_members(fw.get("extensions"))
        if accepted is None:
            non_concluable.append(native_semantics_label(fw))
            continue
        for arg, label in (rejected_from_framework(fw, accepted) or {}).items():
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


# The semantics a dict keyed by semantics carries (conversational
# ``_build_dung_framework_from_state`` writes ``grounded``); the readers of
# #2672 display these three.
KEYED_SEMANTICS = ("grounded", "preferred", "stable")


def _as_extension_list(value: Any) -> Optional[List[List[str]]]:
    """``[[a, b], [c]]`` as is, a flat ``[a, b]`` as the one extension it is.

    ``[]`` is zero extensions. Anything else is unknown (``None``).
    """
    if not isinstance(value, list):
        return None
    if all(isinstance(x, str) for x in value):
        return [list(value)] if value else []
    if all(isinstance(x, list) and all(isinstance(y, str) for y in x) for x in value):
        return [list(x) for x in value]
    return None


def extension_lists(fw: Any) -> Optional[Dict[str, List[List[str]]]]:
    """The extensions ONE framework entry computed, per semantics (#2672).

    Two producers write Dung extensions, in two shapes:

    - the pipeline files one ``verification_{sem}`` entry per semantics, whose
      ``extensions`` is ``{"extensions": [[...], ...], "count", "sizes",
      "all_members"}`` (``_invoke_dung_extensions``, ``DungStudentProvider``);
    - conversational mode files ``conversational_dung`` with a dict keyed by
      semantics, ``{"grounded": [...]}``.

    Returns ``None`` when the entry carries neither: every formalism sidecar
    (its keys are formalism-specific: ``aba_extensions``, ``delp_query_results``,
    …), ``verification_multi`` (a copy of the primary under a label that is not
    a semantics), and a native entry whose extensions were never computed.
    ``all_members`` is the union of the extensions, not an extension, so it is
    never returned as one.
    """
    if not isinstance(fw, dict):
        return None
    ext = fw.get("extensions")
    if not isinstance(ext, dict):
        return None
    if is_native_dung_framework(fw) and "extensions" in ext:
        label = native_semantics_label(fw)
        lists = _as_extension_list(ext.get("extensions"))
        if label == "multi" or lists is None:
            return None
        return {label: lists}
    found: Dict[str, List[List[str]]] = {}
    for sem in KEYED_SEMANTICS:
        if sem in ext:
            lists = _as_extension_list(ext[sem])
            if lists is not None:
                found[sem] = lists
    return found or None


def dung_reading(
    frameworks: Any,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, List[List[str]]]]:
    """The framework to present as "the Dung framework", and its extensions
    per semantics (#2672).

    ``dung_frameworks`` holds every formalism, and its first entry is usually a
    sidecar (DeLP's, with no arguments, on every pipeline run). The native
    verification entries come first (``select_primary_native``), with the
    extensions of all ``verification_{sem}`` entries merged: one writer call
    files them over one argument set. Without a native entry, the first entry
    keyed by semantics is read (conversational mode), then the first entry with
    no extensions at all (a framework an agent declared through
    ``StateManagerPlugin.add_dung_framework`` without ``extensions_json``).
    Every formalism sidecar carries its own keys, so it matches neither: a
    state holding only sidecars has no Dung reading, ``(None, {})``.

    An empty mapping next to a framework means its extensions were never
    computed (``verification_unavailable``, compare mode): say so, never render
    it as an empty extension.
    """
    if not isinstance(frameworks, dict):
        return None, {}
    primary = select_primary_native(frameworks)
    if primary is not None:
        by_semantics: Dict[str, List[List[str]]] = {}
        for fw in frameworks.values():
            if is_native_dung_framework(fw):
                for sem, lists in (extension_lists(fw) or {}).items():
                    by_semantics.setdefault(sem, lists)
        return primary, by_semantics
    for fw in frameworks.values():
        lists = extension_lists(fw)
        if lists:
            return fw, lists
    for fw in frameworks.values():
        if isinstance(fw, dict) and not fw.get("extensions"):
            return fw, {}
    return None, {}
