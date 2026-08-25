"""Diagnose upstream drift of a Maven-published Java library, across versions.

Motivation (#1874). Twice in one round the naive question gave the wrong answer:

* « la version 1.28 est-elle disponible ? » -> the aggregator POM resolves, so the
  answer looks like YES, while its 47 declared modules are simply not published at
  that version. The build fails anyway. A version is usable only if the *parts*
  we consume resolve, never because the umbrella coordinate does.
* « cette classe a disparu, où est-elle passée ? » -> a neighbouring module with a
  similar acronym (``arg.eaf``) looked like the new home. It was not: ``eaf`` means
  *Epistemic* AF, its inventory is byte-identical between the two versions, and the
  *Evidential* family was simply deleted. Reading a name collision as a migration
  invents a fact that nothing then re-measures.

So this module answers three questions that a `jar tf` or a single grep cannot, and
answers them *with the control that makes a negative meaningful*:

1. ``modules``   — which modules are actually published at each version, and which
                   ones the umbrella artifact does not aggregate.
2. ``classes``   — which classes were lost/gained, and for every lost one whether it
                   was **RELOCATED** (same simple name elsewhere in the new surface),
                   **DELETED** (nowhere), or **INDETERMINATE** (its module did not
                   resolve on the target side, so nothing was actually looked at).
                   The third verdict is the one that keeps the tool honest: without
                   it, an unpublished version reads as a mass deletion. A relocation
                   report is only trustworthy when the search surface is the whole new
                   version, aggregated modules *and* the ones the umbrella leaves out.
3. ``bytecode``  — the class-file major version histogram, which decides whether a
                   downstream bridge (IKVM, an older JRE, an Android toolchain) can
                   consume the jars at all. Downgrading the library does not help
                   when every release targets the same level.

The analysis functions are pure and operate on plain dicts, so they are unit-testable
without network or Maven. Only :func:`fetch_jar` and :func:`list_repo_children` do I/O.

Related single-jar inspectors, kept and not duplicated:
``scripts/validation/list_classes_in_jar.py`` (one package of one jar) and
``scripts/validation/check_jar_content.py`` (substring in one jar's entry names).
"""

from __future__ import annotations

import argparse
import collections
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

MAVEN_CENTRAL = "https://repo1.maven.org/maven2"
DEFAULT_TIMEOUT = 60
RETRY_BACKOFF_SECONDS = 2

# Java class-file major version -> human label. Anything above 52 is rejected by a
# toolchain that only accepts Java 8 bytecode, which is the IKVM 8.x situation.
MAJOR_NAMES = {
    45: "Java1.1",
    49: "Java5",
    50: "Java6",
    51: "Java7",
    52: "Java8",
    53: "Java9",
    54: "Java10",
    55: "Java11",
    56: "Java12",
    57: "Java13",
    58: "Java14",
    59: "Java15",
    60: "Java16",
    61: "Java17",
    62: "Java18",
    63: "Java19",
    64: "Java20",
    65: "Java21",
}

CLASS_MAGIC = b"\xca\xfe\xba\xbe"


# --------------------------------------------------------------------------- I/O


# A miss and an outage are not the same finding, and collapsing them is how a
# transport failure gets certified as "nothing was lost". ABSENT means the server
# answered and said no (404/410): the artifact is genuinely not published there,
# which is a *result*. UNREACHABLE means we never got an answer -- reset, timeout,
# DNS, 5xx: the instrument did not look, so every downstream negative drawn from it
# is an instrumental zero, not a semantic one. Measured on CI run 32776186323: a
# single `Connection reset` on one source-side jar turned `perdues=75` into
# `perdues=0` with the report certifying the zero.
FETCH_OK = "ok"
FETCH_ABSENT = "absent"
FETCH_UNREACHABLE = "unreachable"

# Retries cover the transport only. A 404 must keep failing on the first try:
# retrying it would spend three round-trips to re-learn a permanent answer, and --
# worse -- would blur the very distinction this function exists to draw.
FETCH_ATTEMPTS = 3


def _get(
    url: str, timeout: int = DEFAULT_TIMEOUT, attempts: int = FETCH_ATTEMPTS
) -> Tuple[Optional[bytes], str]:
    """Return ``(body, status)`` where status is one of the ``FETCH_*`` constants."""
    last = FETCH_UNREACHABLE
    for attempt in range(max(1, attempts)):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.read(), FETCH_OK
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 410):
                return None, FETCH_ABSENT
            last = FETCH_UNREACHABLE
        except (urllib.error.URLError, OSError):
            last = FETCH_UNREACHABLE
        if attempt + 1 < max(1, attempts):
            time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    return None, last


def list_repo_children(
    repo: str, path: str, timeout: int = DEFAULT_TIMEOUT
) -> List[str]:
    """List the immediate subdirectory names of a Maven repository path.

    Returns [] when the listing is unavailable. An empty listing is *not* proof of
    absence -- some mirrors disable directory browsing while still serving artifacts.
    """
    body, _status = _get(f"{repo}/{path.strip('/')}/", timeout=timeout)
    if body is None:
        return []
    text = body.decode("utf-8", errors="replace")
    names = re.findall(r'href="([^"/?]+)/"', text)
    return sorted({n for n in names if n not in ("..",)})


def fetch_jar(
    repo: str, group: str, artifact: str, version: str, timeout: int = DEFAULT_TIMEOUT
) -> Tuple[Optional[bytes], str]:
    """Download one module jar, as ``(body, status)``.

    The status matters more than the body: ``FETCH_ABSENT`` is an answer about the
    repository ("this module is not published at this version"), while
    ``FETCH_UNREACHABLE`` is an answer about us ("we failed to ask"). Returning a
    bare None for both is what let a transport outage be read as a clean absence.
    """
    gpath = group.replace(".", "/")
    url = f"{repo}/{gpath}/{artifact}/{version}/{artifact}-{version}.jar"
    body, status = _get(url, timeout=timeout)
    # A 404 page is served as HTML by some fronts; a real jar is a zip. The server
    # answered, so this is an absence, not an outage.
    if body is not None and not body.startswith(b"PK"):
        return None, FETCH_ABSENT
    return body, status


def _module_group(root: str, module: str) -> str:
    """groupId of ``module`` under ``root`` (arg.bipolar -> <root>.arg)."""
    return f"{root}.{module.rsplit('.', 1)[0]}" if "." in module else root


def published_versions(
    repo: str, group: str, artifact: str, timeout: int = DEFAULT_TIMEOUT
) -> List[str]:
    """Versions listed in an artifact's maven-metadata.xml (may have holes)."""
    gpath = group.replace(".", "/")
    body, _status = _get(
        f"{repo}/{gpath}/{artifact}/maven-metadata.xml", timeout=timeout
    )
    if body is None:
        return []
    text = body.decode("utf-8", errors="replace")
    return re.findall(r"<version>([^<]+)</version>", text)


def aggregator_modules(
    repo: str,
    group: str,
    artifact: str,
    version: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> Tuple[List[str], str]:
    """Module names an umbrella POM declares, as ``(modules, status)``.

    Measured on `tweety-full-1.29.pom`: 48 `<dependency>` blocks and zero
    `<module>` entries, so the declaration lives in the dependency list. Entries
    outside the root group are third-party closure, not modules of the library,
    and are dropped -- counting them would inflate every gap figure below.

    The status is propagated for the same reason it is everywhere else: an
    unreachable POM must not be read as "the aggregator declares nothing".
    """
    gpath = group.replace(".", "/")
    url = f"{repo}/{gpath}/{artifact}/{version}/{artifact}-{version}.pom"
    body, status = _get(url, timeout=timeout)
    if body is None:
        return [], status
    text = body.decode("utf-8", errors="replace")
    modules = []
    for dep in re.findall(r"<dependency>(.*?)</dependency>", text, re.S):
        gid = re.search(r"<groupId>([^<]+)</groupId>", dep)
        aid = re.search(r"<artifactId>([^<]+)</artifactId>", dep)
        if not gid or not aid:
            continue
        gid, aid = gid.group(1).strip(), aid.group(1).strip()
        if gid == group:
            modules.append(aid)
        elif gid.startswith(group + "."):
            modules.append(f"{gid[len(group) + 1:]}.{aid}")
    return sorted(set(modules)), status


# ------------------------------------------------------------------- pure analysis


def index_jar(blob: bytes, skip_inner: bool = True) -> Dict[str, int]:
    """Map fully-qualified class name -> class-file major version.

    ``skip_inner`` drops ``Foo$Bar`` entries, which inflate counts without naming a
    distinct API surface. The test is on the *simple name*, not on the whole path:
    a package directory containing a dollar sign is legal in a jar, and testing the
    full path would silently drop every class under it -- an exclusion that leaves
    no trace in the count it shrinks.
    """
    out: Dict[str, int] = {}
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        for name in zf.namelist():
            if not name.endswith(".class"):
                continue
            stem = name[: -len(".class")]
            if skip_inner and "$" in stem.rsplit("/", 1)[-1]:
                continue
            head = zf.open(name).read(8)
            if len(head) < 8 or head[:4] != CLASS_MAGIC:
                continue
            out[stem.replace("/", ".")] = (head[6] << 8) | head[7]
    return out


def bytecode_histogram(index: Dict[str, int]) -> List[Tuple[int, int]]:
    """(major, count) pairs, most frequent first."""
    hist = collections.Counter(index.values())
    return sorted(hist.items(), key=lambda kv: (-kv[1], kv[0]))


def max_major(index: Dict[str, int]) -> Optional[int]:
    return max(index.values()) if index else None


def classify_lost(
    old_index: Dict[str, int],
    new_index: Dict[str, int],
    owners_old: Optional[Dict[str, str]] = None,
    unresolved_new: Iterable[str] = (),
    owners_new: Optional[Dict[str, str]] = None,
) -> Dict[str, List[Tuple[str, Optional[str]]]]:
    """Split old-only classes into RELOCATED, DELETED and INDETERMINATE.

    A class counts as relocated when its *simple* name reappears anywhere in the new
    surface under a different package. That is a deliberately generous rule: it is
    meant to avoid declaring a deletion that is merely a move. The caller still has
    to look at the proposed new home -- a same-named class in an unrelated package is
    a name collision, not a migration (the ``arg.eaf`` trap that motivated this).

    ``unresolved_new`` is load-bearing, not decoration. A class whose owning module
    failed to resolve on the new side is **not** evidence of a deletion: the
    instrument simply did not look. Reporting it as DELETED would be a verdict read
    off an instrument that produced no positive for that module -- the very mistake
    this tool exists to prevent. Those classes go to ``indeterminate`` instead.
    """
    new_simple: Dict[str, List[str]] = collections.defaultdict(list)
    for fqcn in new_index:
        new_simple[fqcn.rsplit(".", 1)[-1]].append(fqcn)

    owners_old = owners_old or {}
    owners_new = owners_new or {}
    blind: Set[str] = set(unresolved_new)

    def annotate(fqcns: Iterable[str]) -> str:
        # Naming the module that HOSTS the candidate is what lets a reader reject
        # the move: `CompleteReasoner (arg.adf)` next to a class lost from
        # `arg.bipolar` reads as two unrelated formalisms reusing a generic name,
        # which the bare FQCN only implies.
        out = []
        for fqcn in sorted(fqcns):
            host = owners_new.get(fqcn)
            out.append(f"{fqcn} ({host})" if host else fqcn)
        return ", ".join(out)

    relocated: List[Tuple[str, Optional[str]]] = []
    deleted: List[Tuple[str, Optional[str]]] = []
    indeterminate: List[Tuple[str, Optional[str]]] = []
    for fqcn in sorted(set(old_index) - set(new_index)):
        simple = fqcn.rsplit(".", 1)[-1]
        candidates = new_simple.get(simple, [])
        owner = owners_old.get(fqcn)
        # Blindness is tested FIRST, before the simple-name match. When the owning
        # module never resolved on the new side, no observation about this class was
        # made at all -- and a same-simple-name hit elsewhere is exactly the kind of
        # coincidence that produced the original wrong answer (Evidential* in
        # `arg.bipolar` vs the unrelated `arg.eaf`). Letting `if candidates:` win
        # here would turn "we never looked" into a confident "it moved there",
        # which is the optimistic failure this tool exists to refuse. The candidate
        # is not discarded: it rides along as an annotation, clearly marked as a
        # lead to check rather than a conclusion.
        if owner in blind:
            hint = (
                "candidat non verifie: " + annotate(candidates) if candidates else None
            )
            indeterminate.append((fqcn, hint or owner))
            continue
        if candidates:
            relocated.append((fqcn, annotate(candidates)))
            continue
        deleted.append((fqcn, None))
    return {
        "relocated": relocated,
        "deleted": deleted,
        "indeterminate": indeterminate,
    }


def publication_gaps(aggregated: Sequence[str], resolvable: Iterable[str]) -> List[str]:
    """Modules an aggregator declares but that do not actually resolve.

    This is the #1874 trap: ``tweety-full:1.28`` resolves and declares 47 modules at
    1.28, none of which are published. The umbrella coordinate answering YES says
    nothing about buildability.
    """
    have: Set[str] = set(resolvable)
    return [m for m in aggregated if m not in have]


def not_aggregated(published: Iterable[str], aggregated: Iterable[str]) -> List[str]:
    """Modules published at a version that the umbrella artifact does not pull.

    These are exactly the blind spot of a relocation search performed on the
    aggregator's dependency closure alone.
    """
    return sorted(set(published) - set(aggregated))


# ------------------------------------------------------------------------ reporting


def _fmt_hist(hist: Sequence[Tuple[int, int]], total: int) -> str:
    bits = []
    for major, count in hist:
        pct = (100.0 * count / total) if total else 0.0
        bits.append(f"{MAJOR_NAMES.get(major, major)}={pct:.0f}%")
    return ", ".join(bits)


def render_report(result: dict) -> str:
    """Human-readable rendering of :func:`diff_versions` output."""
    lines: List[str] = []
    old, new = result["from_version"], result["to_version"]
    lines.append(f"=== {result['group']} : {old} -> {new}")

    for tag in (old, new):
        info = result["per_version"][tag]
        lines.append(
            f"  [{tag}] modules resolus={info['module_count']} "
            f"classes={info['class_count']} "
            f"bytecode: {_fmt_hist(info['bytecode'], info['class_count'])}"
        )
        if info["unresolved"]:
            lines.append(
                f"    /!\\ declares mais NON publies ({len(info['unresolved'])}): "
                + ", ".join(info["unresolved"][:12])
            )
        agg = info.get("aggregator")
        if agg:
            if agg["status"] != FETCH_OK:
                lines.append(
                    f"    agregat {agg['artifact']}: POM {agg['status'].upper()} -- "
                    "aucun chiffre de publication n'est disponible pour cette version"
                )
            else:
                lines.append(
                    f"    agregat {agg['artifact']}: declare={len(agg['declared'])} "
                    f"trous={len(agg['gaps'])} hors-agregat={len(agg['not_aggregated'])}"
                )
                shown = agg["gaps"][:12]
                if len(agg["gaps"]) > len(shown):
                    # A cut that leaves no trace reads as "that was all of them".
                    lines.append(
                        f"      ... {len(agg['gaps']) - len(shown)} autre(s) trou(s) "
                        "non listes (--limit ne s'applique qu'aux classes)"
                    )
                for module in shown:
                    seen = agg.get("gap_versions", {}).get(module) or []
                    where = (
                        "publie ailleurs en " + ", ".join(seen)
                        if seen
                        else "aucune version publiee"
                    )
                    lines.append(f"      TROU  {module} ({where})")
                if agg.get("metadata_only"):
                    lines.append(
                        "      METADATA-SEULE "
                        + ", ".join(agg["metadata_only"][:12])
                        + " -- maven-metadata annonce cette version, le jar ne "
                        "repond pas: l'ecart mesure ce qu'une lecture metadata "
                        "seule ne voit pas"
                    )
                if agg["not_aggregated"]:
                    lines.append(
                        "      HORS-AGREGAT "
                        + ", ".join(agg["not_aggregated"][:12])
                        + " -- invisible pour une recherche menee sur la seule "
                        "fermeture de l'agregat"
                    )

    lost = result["lost"]
    indet = lost.get("indeterminate", [])
    lines.append(
        f"  perdues={len(lost['relocated']) + len(lost['deleted']) + len(indet)} "
        f"(relocalisees={len(lost['relocated'])}, supprimees={len(lost['deleted'])}, "
        f"indeterminees={len(indet)}) gagnees={len(result['gained'])}"
    )
    for fqcn, where in lost["relocated"][: result["limit"]]:
        lines.append(f"    RELOCALISEE? {fqcn} -> {where}")
    for fqcn, _ in lost["deleted"][: result["limit"]]:
        lines.append(f"    SUPPRIMEE    {fqcn}")
    for fqcn, owner in indet[: result["limit"]]:
        lines.append(f"    INDETERMINEE {fqcn} (module {owner} non resolu en cible)")

    control = result["control"]
    unreachable = control.get("unreachable_source", []) + control.get(
        "unreachable_target", []
    )
    if control["ok"]:
        lines.append(
            "  controle: index de depart non vide "
            f"({control['old_classes']} classes), aucun module injoignable, cible "
            "entierement resolue -> un zero est semantique"
        )
    elif not control["old_classes"]:
        lines.append(
            "  /!\\ CONTROLE ECHOUE: index de depart vide -- "
            "aucune conclusion negative n'est recevable"
        )
    elif unreachable:
        # Named first and separately: this is the failure that used to be invisible.
        # It says nothing about the library and everything about the run -- a
        # transport outage on one source module is what turned `perdues=75` into
        # `perdues=0` under a report certifying the zero was semantic.
        side = []
        if control.get("unreachable_source"):
            side.append("source: " + ", ".join(control["unreachable_source"][:6]))
        if control.get("unreachable_target"):
            side.append("cible: " + ", ".join(control["unreachable_target"][:6]))
        lines.append(
            "  /!\\ CONTROLE ECHOUE: module(s) INJOIGNABLE(S) ("
            + " | ".join(side)
            + ") -- panne de transport, pas une absence: aucun chiffre de ce "
            "rapport n'est un resultat"
        )
    elif control.get("attribution_missing"):
        lines.append(
            "  /!\\ CONTROLE ECHOUE: attribution des classes indisponible "
            "(owners_old absent) alors que la cible n'a pas tout resolu -- "
            "les verdicts SUPPRIMEE de ce rapport ne sont pas recevables"
        )
    else:
        lines.append(
            "  /!\\ CONTROLE ECHOUE: la version cible n'a pas entierement resolu ("
            + ", ".join(control["unresolved_target"][:6])
            + ") -- ces classes sont INDETERMINEES, pas supprimees"
        )
    # Absence on the source side does not void the control (a module missing from the
    # older version contributes no class, so it cannot fake a zero), but staying
    # silent about it is how the source side came to be ignored in the first place.
    only_absent_source = [
        m
        for m in control.get("unresolved_source", [])
        if m not in control.get("unreachable_source", [])
    ]
    if only_absent_source:
        lines.append(
            f"  note: {len(only_absent_source)} module(s) absent(s) de la version "
            "source (" + ", ".join(only_absent_source[:6]) + ") -- normal si la "
            "liste de modules vient de la version cible"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------- orchestration


def collect_version(
    repo: str,
    group: str,
    modules: Sequence[str],
    version: str,
    timeout: int = DEFAULT_TIMEOUT,
    verbose: bool = False,
    skip_inner: bool = True,
) -> Tuple[Dict[str, int], Dict[str, str], List[str], List[str], List[str]]:
    """Download every module at ``version``.

    Returns (index, owners, resolved, unresolved, unreachable). ``owners`` maps each
    class to the module it came from; without it a lost class cannot be attributed to
    a module that failed to resolve, and the diff would call it deleted.

    ``unreachable`` is a strict subset of ``unresolved``: the modules for which no
    answer was obtained at all. Keeping it apart is what lets a caller tell "this
    module is not published here" from "this run never found out".
    """
    index: Dict[str, int] = {}
    owners: Dict[str, str] = {}
    resolved: List[str] = []
    unresolved: List[str] = []
    unreachable: List[str] = []
    for module in modules:
        artifact = module.rsplit(".", 1)[-1]
        sub_group = _module_group(group, module)
        blob, status = fetch_jar(repo, sub_group, artifact, version, timeout=timeout)
        if blob is None:
            unresolved.append(module)
            if status != FETCH_ABSENT:
                unreachable.append(module)
                if verbose:
                    print(f"    ! {module}-{version}: INJOIGNABLE", file=sys.stderr)
            continue
        resolved.append(module)
        module_index = index_jar(blob, skip_inner=skip_inner)
        index.update(module_index)
        for fqcn in module_index:
            owners.setdefault(fqcn, module)
        if verbose:
            print(f"    + {module}-{version}", file=sys.stderr)
    return index, owners, resolved, unresolved, unreachable


def diff_versions(
    old_index: Dict[str, int],
    new_index: Dict[str, int],
    *,
    group: str,
    from_version: str,
    to_version: str,
    per_version: dict,
    owners_old: Optional[Dict[str, str]] = None,
    owners_new: Optional[Dict[str, str]] = None,
    limit: Optional[int] = 25,
) -> dict:
    """Assemble the full comparison result from two already-built indexes."""
    unresolved_new = per_version.get(to_version, {}).get("unresolved", [])
    unresolved_old = per_version.get(from_version, {}).get("unresolved", [])
    unreachable_new = per_version.get(to_version, {}).get("unreachable", [])
    unreachable_old = per_version.get(from_version, {}).get("unreachable", [])
    lost = classify_lost(
        old_index,
        new_index,
        owners_old=owners_old,
        unresolved_new=unresolved_new,
        owners_new=owners_new,
    )
    # Without `owners_old`, a lost class cannot be attributed to its module, so the
    # INDETERMINATE verdict cannot be reached at all: every class would be reported
    # DELETED while the same report states the target side did not fully resolve.
    # A report that contradicts itself is worse than one that refuses to conclude.
    attribution_missing = bool(unresolved_new) and not owners_old
    gained = sorted(set(new_index) - set(old_index))
    return {
        "group": group,
        "from_version": from_version,
        "to_version": to_version,
        "per_version": per_version,
        "lost": lost,
        "gained": gained,
        "limit": limit,
        # A negative ("nothing was lost", "nothing relocated") is only meaningful if
        # the instrument demonstrably saw something on the reference side, AND both
        # sides were actually observed. The source side was rendered in the report
        # and never consulted here, which is how one failed GET on a source module
        # turned `perdues=75` into `perdues=0` -- with the report certifying that the
        # zero was semantic.
        #
        # The two holes are NOT symmetric, and collapsing them would build a guard
        # that cries wolf. A module *absent* from the source version is a normal
        # outcome of comparing two versions with one module list -- it contributes no
        # class to `old_index`, so it cannot manufacture a false zero. A module
        # *unreachable* on either side means the instrument did not look, and every
        # negative drawn from it is instrumental. So: absence on the source is
        # reported, unreachability anywhere voids the control.
        "control": {
            "ok": (
                bool(old_index)
                and not attribution_missing
                and not unreachable_old
                and not unreachable_new
                and not unresolved_new
            ),
            "old_classes": len(old_index),
            "attribution_missing": attribution_missing,
            "unresolved_source": list(unresolved_old),
            "unresolved_target": list(unresolved_new),
            "unreachable_source": list(unreachable_old),
            "unreachable_target": list(unreachable_new),
        },
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare deux versions d'une bibliotheque Java publiee sur un depot "
            "Maven: modules publies, classes perdues/gagnees, relocalisation vs "
            "suppression, niveau de bytecode."
        )
    )
    parser.add_argument("--from-version", required=True)
    parser.add_argument("--to-version", required=True)
    parser.add_argument("--repo", default=MAVEN_CENTRAL)
    parser.add_argument(
        "--group",
        default="org.tweetyproject",
        help="groupId racine (defaut: org.tweetyproject)",
    )
    parser.add_argument(
        "--modules",
        nargs="*",
        default=None,
        help=(
            "modules a comparer (ex: arg.bipolar logics.pl). Par defaut, decouverte "
            "par listing du depot."
        ),
    )
    parser.add_argument(
        "--aggregator",
        default=None,
        help=(
            "artifactId de l'agregat (ex: tweety-full). Active l'axe publication: "
            "modules declares mais non publies, et modules publies hors agregat."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="nombre de classes detaillees par verdict (0 = toutes)",
    )
    parser.add_argument(
        "--include-inner",
        action="store_true",
        help=(
            "compter aussi les classes internes (Foo$Bar). Par defaut elles sont "
            "ecartees: elles gonflent un total sans nommer une surface d'API "
            "distincte. Les deux comptages sont justes, ils ne mesurent pas le "
            "meme objet."
        ),
    )
    parser.add_argument("--json", action="store_true", help="sortie JSON brute")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    modules = args.modules
    # `--modules` with no value is a caller who meant to restrict the comparison and
    # got a full network discovery instead -- a silently different run, on a much
    # larger population, under a flag that says the opposite.
    if modules is not None and not modules:
        print(
            "--modules a ete passe sans valeur. Retirez le drapeau pour la "
            "decouverte automatique, ou nommez les modules a comparer.",
            file=sys.stderr,
        )
        return 2
    if not modules:
        gpath = args.group.replace(".", "/")
        top = list_repo_children(args.repo, gpath, timeout=args.timeout)
        modules = []
        for child in top:
            nested = list_repo_children(
                args.repo, f"{gpath}/{child}", timeout=args.timeout
            )
            # A directory holding version dirs is a leaf artifact; one holding more
            # names is a group segment (org.tweetyproject.arg -> dung, bipolar, ...).
            if any(re.match(r"^\d", n) for n in nested):
                modules.append(child)
            else:
                modules.extend(f"{child}.{n}" for n in nested)
        modules = sorted(set(modules))
        if args.verbose:
            print(f"  decouverte: {len(modules)} modules", file=sys.stderr)

    if not modules:
        print(
            "Aucun module decouvert: listing indisponible. Passez --modules "
            "explicitement -- un listing vide ne prouve pas une absence.",
            file=sys.stderr,
        )
        return 2

    per_version = {}
    indexes = {}
    owners_by_version = {}
    for version in (args.from_version, args.to_version):
        if args.verbose:
            print(f"  version {version}...", file=sys.stderr)
        index, owners, resolved, unresolved, unreachable = collect_version(
            args.repo,
            args.group,
            modules,
            version,
            timeout=args.timeout,
            verbose=args.verbose,
            skip_inner=not args.include_inner,
        )
        indexes[version] = index
        owners_by_version[version] = owners
        per_version[version] = {
            "module_count": len(resolved),
            "unresolved": unresolved,
            "unreachable": unreachable,
            "class_count": len(index),
            "bytecode": bytecode_histogram(index),
        }
        if args.aggregator:
            declared, agg_status = aggregator_modules(
                args.repo, args.group, args.aggregator, version, timeout=args.timeout
            )
            # The gap axis must be computed over the DECLARED set, never over the
            # compared set: with an explicit --modules list, every module the user
            # did not ask about would be counted as a publication gap. So each
            # declared module is probed on its own metadata.
            meta = {
                module: published_versions(
                    args.repo,
                    _module_group(args.group, module),
                    module.rsplit(".", 1)[-1],
                    timeout=args.timeout,
                )
                for module in declared
            }
            resolvable = [m for m, versions in meta.items() if version in versions]
            gaps = publication_gaps(declared, resolvable)
            # Two instruments on the same band: metadata says published, the jar
            # download says otherwise. The disagreement is not noise to arbitrate --
            # it measures what a metadata-only reading cannot see. Only computable
            # for modules that were actually compared.
            compared = set(resolved) | set(unresolved)
            metadata_only = sorted(
                m for m in resolvable if m in compared and m not in set(resolved)
            )
            per_version[version]["aggregator"] = {
                "artifact": args.aggregator,
                "status": agg_status,
                "declared": declared,
                "gaps": gaps,
                # For a gap, "never published anywhere" and "published, but not at
                # this version" call for different actions.
                "gap_versions": {m: meta[m][-6:] for m in gaps[:12]},
                "metadata_only": metadata_only,
                # Published here but not pulled by the umbrella: the blind spot of
                # any relocation search run on the aggregator's closure alone.
                "not_aggregated": not_aggregated(resolved, declared),
            }

    result = diff_versions(
        indexes[args.from_version],
        indexes[args.to_version],
        group=args.group,
        from_version=args.from_version,
        to_version=args.to_version,
        per_version=per_version,
        owners_old=owners_by_version[args.from_version],
        owners_new=owners_by_version[args.to_version],
        # 0 means "all": a silent truncation reads as "that was the whole list".
        limit=args.limit or None,
    )

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(render_report(result))

    # Exit 1 whenever the control refuses to certify: empty reference side, a module
    # left unreachable on either side, or an unresolved module on the target. A caller
    # scripting this tool must not be able to read a negative out of a run that
    # never looked.
    return 0 if result["control"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
