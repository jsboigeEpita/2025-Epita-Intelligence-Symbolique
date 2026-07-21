"""Synthetic AF generators + ICCMA `.af` parser for backend comparison.

This module is consumed by :mod:`scripts.compare_dung_backends` and the
upstream ``_compare_dung_backends`` wiring. Everything is *synthetic* —
no encrypted dataset is touched here.

Components:

* :func:`parse_iccma_af` — strict parser for the ICCMA 2023 ``.af`` text
  format (``p af <n>\\nn N x\\n...\\na x y\\n...``). Pure stdlib.
* :func:`generate_sbm` — Stochastic Block Model using
  :mod:`networkx.stochastic_block_model`. Produces disjoint clusters of
  arguments with intra/inter-block attack densities. Scales past |V|=25
  where :func:`abs_arg_dung.framework_generator.generate_random_framework`
  is unusable.
* :func:`generate_er` — Erdős-Rényi flat model for a baseline.
* :func:`generate_classic_examples` — bundles the textbook frameworks
  (Nixon Diamond, odd cycle, mutual attack, chain, self-loop) so the
  backend comparison has a deterministic regression set.

Determinism: every generator takes a ``seed`` argument; outputs are
reproducible across runs. The ICCMA parser is purely functional and
deterministic by construction.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, Sequence, Set, Tuple

# Lazy import: keep module importable even if networkx is unavailable
# (the parser path does not need it).
try:  # pragma: no cover — import guard exercised at first use
    import networkx as nx
except ImportError:  # pragma: no cover
    nx = None


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

Attack = Tuple[str, str]
Framework = Tuple[List[str], List[Attack]]


# ---------------------------------------------------------------------------
# ICCMA .af parser
# ---------------------------------------------------------------------------

# Tokens recognized at the start of a non-comment line:
#   p af <int>          — problem header (mandatory)
#   n <ident>           — name an argument
#   a <src> <tgt>       — declare an attack src -> tgt
# Lines beginning with '#' or '%' (or empty) are comments.
_AF_HEADER_RE = re.compile(r"^p\s+af\s+(\d+)\s*$")
_AF_ARG_RE = re.compile(r"^n\s+([A-Za-z0-9_][\w\-]*)\s*$")
_AF_ATTACK_RE = re.compile(r"^a\s+([A-Za-z0-9_][\w\-]*)\s+([A-Za-z0-9_][\w\-]*)\s*$")


def parse_iccma_af(text: str) -> Framework:
    """Parse an ICCMA ``.af`` text payload.

    Returns ``(arguments, attacks)`` as sorted lists for determinism.
    Raises ``ValueError`` on malformed input with a line-number hint.

    Format reference: ICCMA 2023 — ``p af`` header, ``n X`` for arguments,
    ``a X Y`` for attacks. Comments start with ``#`` / ``%`` / blank lines.
    """
    arguments_set: Set[str] = set()
    attacks_set: Set[Attack] = set()
    header_seen = False
    expected_n: int | None = None

    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("%"):
            continue

        m_header = _AF_HEADER_RE.match(line)
        if m_header:
            if header_seen:
                raise ValueError(f"line {lineno}: duplicate `p af` header")
            expected_n = int(m_header.group(1))
            header_seen = True
            continue

        m_arg = _AF_ARG_RE.match(line)
        if m_arg:
            arguments_set.add(m_arg.group(1))
            continue

        m_attack = _AF_ATTACK_RE.match(line)
        if m_attack:
            src, tgt = m_attack.group(1), m_attack.group(2)
            # Defer ordering check on `src/tgt in arguments_set` until after
            # the full file is parsed (ICCMA allows `a` lines before `n`).
            attacks_set.add((src, tgt))
            continue

        raise ValueError(f"line {lineno}: unrecognized token {line!r}")

    if not header_seen:
        raise ValueError("missing mandatory `p af <n>` header")

    # Validate: every endpoint of an attack must be a declared argument.
    for src, tgt in attacks_set:
        if src not in arguments_set:
            raise ValueError(f"attack source {src!r} not declared with `n`")
        if tgt not in arguments_set:
            raise ValueError(f"attack target {tgt!r} not declared with `n`")

    if expected_n is not None and len(arguments_set) != expected_n:
        raise ValueError(
            f"`p af {expected_n}` declares {expected_n} args, "
            f"but `n` lines declared {len(arguments_set)}"
        )

    return (sorted(arguments_set), sorted(set(attacks_set)))


def parse_iccma_af_file(path: str | Path) -> Framework:
    """Convenience wrapper: read file and parse."""
    p = Path(path)
    return parse_iccma_af(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Synthetic generators (networkx-backed when available, stdlib fallback)
# ---------------------------------------------------------------------------

def _nx_sbm(
    block_sizes: Sequence[int],
    p_in: float,
    p_out: float,
    seed: int,
) -> Framework:
    if nx is None:
        raise RuntimeError("networkx required for SBM generation; `pip install networkx`")
    # Convention: an *edge u → v* in graph G means u attacks v.
    # Use DIRECTED stochastic_block_model with `directed=True` so each
    # ordered pair (u, v) is sampled independently. We split `p[i][j]` into
    # two directed channels: p_in for u→v when u, v are in the SAME block,
    # p_out for u→v when they are in DIFFERENT blocks. Both directions are
    # sampled, so within-block mutual attacks arise naturally and the
    # resulting AF has nontrivial structure (cycles within blocks, sparse
    # inter-block edges).
    rng = nx.stochastic_block_model(
        list(block_sizes),
        p=[[p_in if i == j else p_out for j in range(len(block_sizes))]
           for i in range(len(block_sizes))],
        seed=seed,
        directed=True,
    )
    # Type consistency: arguments and attack endpoints are all strings.
    # This matches the ICCMA parser contract and avoids type-mismatch
    # silent failures in downstream reasoners.
    arguments = sorted(str(n) for n in rng.nodes())
    attacks = sorted({(str(u), str(v)) for u, v in rng.edges()})
    return (arguments, attacks)


def _nx_er(num_args: int, p: float, seed: int) -> Framework:
    if nx is None:
        raise RuntimeError("networkx required for ER generation")
    g = nx.gnp_random_graph(num_args, p, seed=seed, directed=True)
    arguments = sorted(str(n) for n in g.nodes())
    attacks = sorted({(str(u), str(v)) for u, v in g.edges()})
    return (arguments, attacks)
    # NB: arguments are normalized to str to match the ICCMA parser and
    # the SBM generator contract.


def generate_sbm(
    block_sizes: Sequence[int],
    p_in: float = 0.3,
    p_out: float = 0.05,
    seed: int = 42,
) -> Framework:
    """Stochastic block model with both-direction attacks inside each block.

    Parameters mirror the validation setup from ICCMA benchmarks. With
    ``block_sizes = [10, 10]``, ``p_in=0.3``, ``p_out=0.05``, the framework
    has 20 arguments and a clear cluster structure useful for cross-backend
    comparison.
    """
    return _nx_sbm(block_sizes, p_in, p_out, seed)


def generate_er(num_args: int, p: float = 0.2, seed: int = 42) -> Framework:
    """Erdős-Rényi flat baseline (directed)."""
    return _nx_er(num_args, p, seed)


# ---------------------------------------------------------------------------
# Canonical examples (deterministic; useful as regression set)
# ---------------------------------------------------------------------------

def generate_classic_examples() -> Dict[str, Framework]:
    """Return a fixed dict of textbook Dung frameworks, all deterministic.

    Keys:

    * ``"nixon_diamond"`` — 4 args, mutual attacks, two stable extensions.
    * ``"odd_cycle_3"`` — 3-cycle, no stable extension.
    * ``"odd_cycle_5"`` — 5-cycle, no stable extension.
    * ``"self_loop"`` — 2 args, ``a`` attacks itself; ``a`` excluded from
      every conflict-free set.
    * ``"mutual_attack"`` — 2 args a↔b, both forms admissible.
    * ``"chain"`` — ``a -> b -> c``, only ``{a}`` survives.
    * ``"isolated"`` — 3 unattached args.
    * ``"asym_chain"`` — ``a -> b -> c`` (no a->c). Asymmetric, regression
      target for direction-inversion bugs (#1502 résidu).
    * ``"asym_diamond"`` — ``a -> b -> c`` + ``a -> d -> c`` (no cross).
      Asymmetric, exposes any direction inversion in `attack_range`.
    """
    a, b, c, d, e = "a", "b", "c", "d", "e"
    return {
        "nixon_diamond": (
            [a, b, c, d],
            [(a, b), (b, a), (c, d), (d, c), (a, c), (b, d)],
        ),
        "odd_cycle_3": (
            [a, b, c],
            [(a, b), (b, c), (c, a)],
        ),
        "odd_cycle_5": (
            [a, b, c, d, e],
            [(a, b), (b, c), (c, d), (d, e), (e, a)],
        ),
        "self_loop": (
            [a, b],
            [(a, a)],
        ),
        "mutual_attack": (
            [a, b],
            [(a, b), (b, a)],
        ),
        "chain": (
            [a, b, c],
            [(a, b), (a, c), (b, c)],
        ),
        "isolated": (
            [a, b, c],
            [],
        ),
        "asym_chain": (
            [a, b, c],
            [(a, b), (b, c)],
        ),
        "asym_diamond": (
            [a, b, c, d],
            [(a, b), (b, c), (a, d), (d, c)],
        ),
    }
