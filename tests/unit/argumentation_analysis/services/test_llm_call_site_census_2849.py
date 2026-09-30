"""#2849 DoD 3 — coverage guard: no chat-completion call site bypasses the funnel.

Every live ``chat.completions.create`` in the production package must route
through the accounting point (``cached_raw_chat_completion`` / its sync twin /
``CachedChatCompletion``, all in ``services/llm_cache.py``). A site calling the
SDK directly spends tokens no counter sees — the exact hole measured on the
#2841 pass (usage logged for 44 client-direct calls, zero SK calls).

Precedent #1787: "0 clean" must be distinguishable from "0 unplugged". The
walker's own non-vacuity control asserts it SEES the funnel's create calls in
``llm_cache.py`` — a census that returns nothing anywhere is a broken walker,
not a clean tree.

#2853 review item 4 — the population comes from the git INDEX
(``iter_tracked_files``), never from the filesystem: a filesystem walk reads
seat-local untracked files CI never runs (#2821/#2833 doctrine), and a file
that cannot be parsed fails loudly — a census that silently drops what it
cannot read measures a smaller population without saying so.
"""

import ast
from pathlib import Path

from tests.support.tree_walk import iter_tracked_files

PRODUCTION_ROOT = Path(__file__).parents[4] / "argumentation_analysis"
FUNNEL_MODULE = "llm_cache.py"


def _parse_loud(py: Path) -> ast.Module:
    """Parse a tracked production file, FAILING the census on a SyntaxError.

    A census that cannot read a file it counts in its population must say so,
    not measure a smaller tree.
    """
    return ast.parse(py.read_text(encoding="utf-8-sig"), filename=str(py))


def _census_create_sites(root: Path) -> dict:
    """{relative_path: [line numbers]} of ``chat.completions.create`` calls."""
    sites: dict = {}
    for py in iter_tracked_files(root, "*.py"):
        if "__pycache__" in py.parts:
            continue
        tree = _parse_loud(py)
        lines = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            # shape: <anything>.chat.completions.create — walk the attribute chain
            chain = []
            while isinstance(func, ast.Attribute):
                chain.append(func.attr)
                func = func.value
            if isinstance(func, ast.Name):
                chain.append(func.id)
            if (
                len(chain) >= 4
                and chain[0] == "create"
                and chain[1] == "completions"
                and chain[2] == "chat"
            ):
                lines.append(node.lineno)
        if lines:
            sites[str(py.relative_to(root))] = sorted(lines)
    return sites


class TestNoBypassSite:
    def test_every_create_site_routes_through_the_funnel(self):
        """Any direct ``client.chat.completions.create`` outside llm_cache.py is
        a bypass of the accounting point — fail, naming the file and line."""
        sites = _census_create_sites(PRODUCTION_ROOT)
        bypasses = {
            path: lines
            for path, lines in sites.items()
            if not path.endswith(FUNNEL_MODULE)
        }
        assert not bypasses, (
            "Chat-completion call site(s) bypassing the accounting funnel "
            "(#2849 — route through cached_raw_chat_completion / _sync): "
            f"{bypasses}"
        )

    def test_walker_sees_the_funnel_its_own_calls(self):
        """Non-vacuity (#1787 precedent): a census finding nothing proves
        nothing. The funnel itself calls ``client.chat.completions.create`` —
        the walker must see those sites, or its 0 above is unwired."""
        sites = _census_create_sites(PRODUCTION_ROOT)
        funnel_sites = {
            path: lines for path, lines in sites.items() if path.endswith(FUNNEL_MODULE)
        }
        assert funnel_sites, (
            "The census walker found no chat.completions.create site at all, "
            "including inside the funnel (llm_cache.py) — the walker is broken "
            "and the guard above read a false 0."
        )
        # the funnel has exactly the async and sync live calls
        funnel_lines = sorted(set(sum(funnel_sites.values(), [])))
        assert (
            len(funnel_lines) >= 2
        ), f"Expected the funnel's own async + sync create calls, got lines {funnel_lines}"


SK_SERVICE_NAMES = {"OpenAIChatCompletion", "AzureChatCompletion"}
FACTORY_MODULE = "llm_service.py"


def _census_sk_constructions(root: Path) -> dict:
    """{relative_path: [(line, wrapped)]} of SK chat-service constructions.

    ``wrapped`` is True when the constructor call is an argument (direct or
    nested) of a ``_wrap_with_llm_cache(...)`` call on the same tree — the
    shape every routed site uses. ``llm_service.py`` (the factory) constructs
    and wraps through a variable, so the file is allowlisted as a whole.
    """
    sites: dict = {}
    for py in iter_tracked_files(root, "*.py"):
        if "__pycache__" in py.parts:
            continue
        tree = _parse_loud(py)
        wrapped_ids: set = set()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_wrap_with_llm_cache"
            ):
                for arg in list(node.args) + [kw.value for kw in node.keywords]:
                    wrapped_ids.add(id(arg))
                    for sub in ast.walk(arg):
                        wrapped_ids.add(id(sub))
        found = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in SK_SERVICE_NAMES
            ):
                found.append((node.lineno, id(node) in wrapped_ids))
        if found:
            sites[str(py.relative_to(root))] = sorted(found)
    return sites


class TestNoUnaccountedSkService:
    def test_every_sk_service_construction_is_wrapped(self):
        """A raw ``OpenAIChatCompletion`` added to a kernel bypasses the
        accounting point — its SK calls spend tokens no counter sees (#2849).
        Outside the factory, every construction must be wrapped."""
        sites = _census_sk_constructions(PRODUCTION_ROOT)
        unwrapped = {
            path: [ln for ln, wrapped in lines if not wrapped]
            for path, lines in sites.items()
            if not path.endswith(FACTORY_MODULE)
            and any(not wrapped for _, wrapped in lines)
        }
        assert not unwrapped, (
            "SK chat-service construction(s) not wrapped by _wrap_with_llm_cache "
            "(#2849 — their calls bypass the accounting point): "
            f"{unwrapped}"
        )

    def test_walker_sees_the_factory_constructions(self):
        """Non-vacuity: the census must see the factory's own constructions,
        or the guard above read a false 0."""
        sites = _census_sk_constructions(PRODUCTION_ROOT)
        factory = {
            path: lines
            for path, lines in sites.items()
            if path.endswith(FACTORY_MODULE)
        }
        assert factory, (
            "The census walker found no SK service construction at all, "
            "including inside the factory (llm_service.py) — the walker is "
            "broken and the guard above read a false 0."
        )

    # #2853 review (minor) — llm_service.py is allowlisted as a whole: a raw
    # construction added to the factory later would be invisible to the guard
    # above. Pin the factory's own construction count instead, so the pin
    # reddens on any addition (then route it, and bump the constant).
    FACTORY_SK_CONSTRUCTIONS = 2  # Azure (:386) + OpenAI (:543), both wrapped

    def test_the_factory_builds_only_the_named_wrapped_services(self):
        """A raw SK construction inside the factory must not hide behind the
        whole-file allowlist — the count is pinned."""
        sites = _census_sk_constructions(PRODUCTION_ROOT)
        factory_lines = sorted(
            ln
            for path, lines in sites.items()
            if path.endswith(FACTORY_MODULE)
            for ln, _ in lines
        )
        assert len(factory_lines) == self.FACTORY_SK_CONSTRUCTIONS, (
            f"the factory (llm_service.py) now holds {len(factory_lines)} SK "
            f"service construction(s), expected {self.FACTORY_SK_CONSTRUCTIONS} "
            "(Azure + OpenAI) — a raw construction added under the whole-file "
            "allowlist is invisible to the bypass guard (#2853): route it "
            "through _wrap_with_llm_cache and bump the pin"
        )
