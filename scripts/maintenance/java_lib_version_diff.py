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
import urllib.error
import urllib.request
import zipfile
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

MAVEN_CENTRAL = "https://repo1.maven.org/maven2"
DEFAULT_TIMEOUT = 60

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


def _get(url: str, timeout: int = DEFAULT_TIMEOUT) -> Optional[bytes]:
    """Return the body at ``url``, or None on any HTTP/network failure."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        return None


def list_repo_children(
    repo: str, path: str, timeout: int = DEFAULT_TIMEOUT
) -> List[str]:
    """List the immediate subdirectory names of a Maven repository path.

    Returns [] when the listing is unavailable. An empty listing is *not* proof of
    absence -- some mirrors disable directory browsing while still serving artifacts.
    """
    body = _get(f"{repo}/{path.strip('/')}/", timeout=timeout)
    if body is None:
        return []
    text = body.decode("utf-8", errors="replace")
    names = re.findall(r'href="([^"/?]+)/"', text)
    return sorted({n for n in names if n not in ("..",)})


def fetch_jar(
    repo: str, group: str, artifact: str, version: str, timeout: int = DEFAULT_TIMEOUT
) -> Optional[bytes]:
    """Download one module jar. None when the coordinate is not published."""
    gpath = group.replace(".", "/")
    url = f"{repo}/{gpath}/{artifact}/{version}/{artifact}-{version}.jar"
    body = _get(url, timeout=timeout)
    # A 404 page is served as HTML by some fronts; a real jar is a zip.
    if body is not None and not body.startswith(b"PK"):
        return None
    return body


def published_versions(
    repo: str, group: str, artifact: str, timeout: int = DEFAULT_TIMEOUT
) -> List[str]:
    """Versions listed in an artifact's maven-metadata.xml (may have holes)."""
    gpath = group.replace(".", "/")
    body = _get(f"{repo}/{gpath}/{artifact}/maven-metadata.xml", timeout=timeout)
    if body is None:
        return []
    text = body.decode("utf-8", errors="replace")
    return re.findall(r"<version>([^<]+)</version>", text)


# ------------------------------------------------------------------- pure analysis


def index_jar(blob: bytes, skip_inner: bool = True) -> Dict[str, int]:
    """Map fully-qualified class name -> class-file major version.

    ``skip_inner`` drops ``Foo$Bar`` entries, which inflate counts without naming a
    distinct API surface.
    """
    out: Dict[str, int] = {}
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        for name in zf.namelist():
            if not name.endswith(".class"):
                continue
            stem = name[: -len(".class")]
            if skip_inner and "$" in stem:
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
    blind: Set[str] = set(unresolved_new)

    relocated: List[Tuple[str, Optional[str]]] = []
    deleted: List[Tuple[str, Optional[str]]] = []
    indeterminate: List[Tuple[str, Optional[str]]] = []
    for fqcn in sorted(set(old_index) - set(new_index)):
        simple = fqcn.rsplit(".", 1)[-1]
        candidates = new_simple.get(simple, [])
        if candidates:
            relocated.append((fqcn, ", ".join(sorted(candidates))))
            continue
        owner = owners_old.get(fqcn)
        if owner in blind:
            indeterminate.append((fqcn, owner))
        else:
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
    if control["ok"]:
        lines.append(
            "  controle: index de depart non vide "
            f"({control['old_classes']} classes) et cible entierement resolue "
            "-> un zero est semantique"
        )
    elif not control["old_classes"]:
        lines.append(
            "  /!\\ CONTROLE ECHOUE: index de depart vide -- "
            "aucune conclusion negative n'est recevable"
        )
    else:
        lines.append(
            "  /!\\ CONTROLE ECHOUE: la version cible n'a pas entierement resolu ("
            + ", ".join(control["unresolved_target"][:6])
            + ") -- ces classes sont INDETERMINEES, pas supprimees"
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
) -> Tuple[Dict[str, int], Dict[str, str], List[str], List[str]]:
    """Download every module at ``version``.

    Returns (index, owners, resolved, unresolved). ``owners`` maps each class to the
    module it came from; without it a lost class cannot be attributed to a module
    that failed to resolve, and the diff would call it deleted.
    """
    index: Dict[str, int] = {}
    owners: Dict[str, str] = {}
    resolved: List[str] = []
    unresolved: List[str] = []
    for module in modules:
        artifact = module.rsplit(".", 1)[-1]
        sub_group = f"{group}.{module.rsplit('.', 1)[0]}" if "." in module else group
        blob = fetch_jar(repo, sub_group, artifact, version, timeout=timeout)
        if blob is None:
            unresolved.append(module)
            continue
        resolved.append(module)
        module_index = index_jar(blob)
        index.update(module_index)
        for fqcn in module_index:
            owners.setdefault(fqcn, module)
        if verbose:
            print(f"    + {module}-{version}", file=sys.stderr)
    return index, owners, resolved, unresolved


def diff_versions(
    old_index: Dict[str, int],
    new_index: Dict[str, int],
    *,
    group: str,
    from_version: str,
    to_version: str,
    per_version: dict,
    owners_old: Optional[Dict[str, str]] = None,
    limit: int = 25,
) -> dict:
    """Assemble the full comparison result from two already-built indexes."""
    unresolved_new = per_version.get(to_version, {}).get("unresolved", [])
    lost = classify_lost(
        old_index, new_index, owners_old=owners_old, unresolved_new=unresolved_new
    )
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
        # the instrument demonstrably saw something on the reference side, AND the
        # target side actually resolved. Either hole makes the diff uninterpretable.
        "control": {
            "ok": bool(old_index) and not unresolved_new,
            "old_classes": len(old_index),
            "unresolved_target": list(unresolved_new),
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
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--json", action="store_true", help="sortie JSON brute")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    modules = args.modules
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
        index, owners, resolved, unresolved = collect_version(
            args.repo,
            args.group,
            modules,
            version,
            timeout=args.timeout,
            verbose=args.verbose,
        )
        indexes[version] = index
        owners_by_version[version] = owners
        per_version[version] = {
            "module_count": len(resolved),
            "unresolved": unresolved,
            "class_count": len(index),
            "bytecode": bytecode_histogram(index),
        }

    result = diff_versions(
        indexes[args.from_version],
        indexes[args.to_version],
        group=args.group,
        from_version=args.from_version,
        to_version=args.to_version,
        per_version=per_version,
        owners_old=owners_by_version[args.from_version],
        limit=args.limit,
    )

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(render_report(result))

    # Exit 1 when the reference side is empty: the comparison is not interpretable.
    return 0 if result["control"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
