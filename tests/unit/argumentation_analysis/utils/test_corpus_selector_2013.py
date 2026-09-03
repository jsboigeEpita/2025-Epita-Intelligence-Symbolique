"""#2013: the three inline CLI parsers expose the opaque selector flag, and the
pre-2026 spelling still parses via the deprecated alias (production constant)
on the same dest with a DeprecationWarning.

Builders are imported from the modules — never re-typed. The modules create a
log file at import, so imports happen lazily inside the fixture under a chdir
to tmp_path. Since #2018 the scripts/ runner imports on the declared core
dependencies alone (the once-pulled namespace was a broken import, fixed
there), so these tests carry no dependency skip.
"""

import importlib

import pytest

from argumentation_analysis.core.utils.cli_utils import DEPRECATED_ORATOR_ALIAS

MODULE_NAMES = [
    "argumentation_analysis.utils.run_verify_extracts",
    "argumentation_analysis.utils.run_verify_extracts_with_llm",
    "argumentation_analysis.scripts.run_verify_extracts_llm",
]


@pytest.fixture
def parser_factory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def _factory(module_name):
        module = importlib.import_module(module_name)
        return module.build_verify_parser()

    return _factory


@pytest.mark.parametrize("module_name", MODULE_NAMES)
def test_opaque_flag_selected(parser_factory, module_name):
    parser = parser_factory(module_name)
    args = parser.parse_args(["--single-orator-only"])
    assert args.single_orator_only is True


@pytest.mark.parametrize("module_name", MODULE_NAMES)
def test_deprecated_alias_still_parses(parser_factory, module_name):
    parser = parser_factory(module_name)
    with pytest.warns(DeprecationWarning):
        args = parser.parse_args([DEPRECATED_ORATOR_ALIAS])
    assert args.single_orator_only is True


@pytest.mark.parametrize("module_name", MODULE_NAMES)
def test_default_is_false(parser_factory, module_name):
    parser = parser_factory(module_name)
    args = parser.parse_args([])
    assert args.single_orator_only is False
