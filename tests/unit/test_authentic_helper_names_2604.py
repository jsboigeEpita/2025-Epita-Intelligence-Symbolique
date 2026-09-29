"""Un helper de test nommé ``authentic`` sert un LLM réel (#2604).

Sous pytest, ``UnifiedConfig.get_kernel_with_gpt4o_mini()`` et
``create_llm_service()`` rendent un ``MockChatCompletion`` tant que
``force_authentic=True`` n'est pas passé (``llm_service.py``). Un helper nommé
``authentic`` qui passe par l'un d'eux sans le forcer annonce donc un LLM réel
et sert un mock : c'est ce qui a fait lire ces tests comme des appels réels.

Mesure de référence (main ``1dd38e66c``) : 44 fonctions de ce type hors
``tests/_archived/`` — 39 ``_create_authentic_gpt4o_mini_instance``, puis une
de chacune : ``_make_authentic_llm_call``, ``_create_authentic_kernel_instance``,
``create_authentic_gpt4o_mini_instance``, ``setup_authentic_game`` et le test
``test_authentic_llm_call``.
"""

import ast
from pathlib import Path

from tests.support.tree_walk import PROBE_PREFIX, iter_tracked_files

TESTS_ROOT = Path(__file__).resolve().parents[1]

# Les deux fabriques qui rendent un mock sous pytest sans ``force_authentic=True``.
MOCK_UNLESS_FORCED = {"get_kernel_with_gpt4o_mini", "create_llm_service"}


def _callee(call):
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _forces(call):
    return any(
        kw.arg == "force_authentic"
        and isinstance(kw.value, ast.Constant)
        and kw.value.value is True
        for kw in call.keywords
    )


def misnamed_helpers(source, label):
    """``label:ligne nom`` de chaque fonction ``*authentic*`` qui atteint une
    fabrique de ``MOCK_UNLESS_FORCED`` sans forcer l'authenticité."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if "authentic" not in node.name.lower():
            continue
        if any(
            isinstance(call, ast.Call)
            and _callee(call) in MOCK_UNLESS_FORCED
            and not _forces(call)
            for call in ast.walk(node)
        ):
            found.append(f"{label}:{node.lineno} {node.name}")
    return found


def test_no_helper_named_authentic_serves_the_pytest_mock():
    found = []
    # ``_archived`` n'est pas collecté : il est hors de ce garde, comme du gate.
    for path in iter_tracked_files(
        TESTS_ROOT, skip_prefixes=(PROBE_PREFIX, "_archived")
    ):
        rel = path.relative_to(TESTS_ROOT).as_posix()
        found += misnamed_helpers(path.read_text(encoding="utf-8-sig"), rel)
    assert not found, (
        "Ces helpers s'appellent 'authentic' mais rendent le mock de pytest : "
        "renommer, ou passer force_authentic=True — "
        f"{found}"
    )


def test_the_detector_sees_both_factories_and_the_flag():
    source = """
class T:
    def _create_authentic_gpt4o_mini_instance(self):
        return UnifiedConfig().get_kernel_with_gpt4o_mini()

    async def authentic_service(self):
        return create_llm_service(service_id="s")

    def forced_authentic(self):
        return UnifiedConfig().get_kernel_with_gpt4o_mini(force_authentic=True)

    def _create_unified_config_kernel(self):
        return UnifiedConfig().get_kernel_with_gpt4o_mini()
"""
    assert misnamed_helpers(source, "x") == [
        "x:3 _create_authentic_gpt4o_mini_instance",
        "x:6 authentic_service",
    ]
