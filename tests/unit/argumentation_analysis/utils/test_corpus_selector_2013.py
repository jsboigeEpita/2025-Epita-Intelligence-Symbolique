"""#2013: the three inline CLI parsers expose the opaque selector flag, and the
pre-2026 spelling still parses via the deprecated alias (production constant)
on the same dest with a DeprecationWarning.

Builders are imported from the modules — never re-typed. The modules create a
log file at import, so imports happen lazily inside the fixture under a chdir
to tmp_path. The scripts/ runner additionally pulls `ag2.agentchat` (the
distribution is declared in environment.yml, but that namespace is absent
from it — see #2018). The guard probes the submodule, not the aggregate:
`ag2` alone resolves in CI while `ag2.agentchat` does not, so probing the
aggregate skips locally and dies in CI on the part that is missing.
"""

import importlib

import pytest

from argumentation_analysis.core.utils.cli_utils import DEPRECATED_ORATOR_ALIAS

MODULES = [
    pytest.param(
        "argumentation_analysis.utils.run_verify_extracts",
        False,
        id="utils_verify",
    ),
    pytest.param(
        "argumentation_analysis.utils.run_verify_extracts_with_llm",
        False,
        id="utils_verify_llm",
    ),
    pytest.param(
        "argumentation_analysis.scripts.run_verify_extracts_llm",
        True,
        id="scripts_verify_llm",
    ),
]


@pytest.fixture
def parser_factory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def _factory(module_name, needs_ag2):
        if needs_ag2:
            pytest.importorskip("ag2.agentchat")
        module = importlib.import_module(module_name)
        return module.build_verify_parser()

    return _factory


@pytest.mark.parametrize("module_name,needs_ag2", MODULES)
def test_opaque_flag_selected(parser_factory, module_name, needs_ag2):
    parser = parser_factory(module_name, needs_ag2)
    args = parser.parse_args(["--single-orator-only"])
    assert args.single_orator_only is True


@pytest.mark.parametrize("module_name,needs_ag2", MODULES)
def test_deprecated_alias_still_parses(parser_factory, module_name, needs_ag2):
    parser = parser_factory(module_name, needs_ag2)
    with pytest.warns(DeprecationWarning):
        args = parser.parse_args([DEPRECATED_ORATOR_ALIAS])
    assert args.single_orator_only is True


@pytest.mark.parametrize("module_name,needs_ag2", MODULES)
def test_default_is_false(parser_factory, module_name, needs_ag2):
    parser = parser_factory(module_name, needs_ag2)
    args = parser.parse_args([])
    assert args.single_orator_only is False
