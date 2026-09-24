# -*- coding: utf-8 -*-
"""#2551: ``setup --env test`` does the work it reports.

On ``41ebd4aee`` the verb printed ``[SUCCESS] Environnement de test configuré``
after two steps that did nothing: ``download_test_jars`` logged "considérés à
jour (simulation)" and returned ``True``, and ``--with-mocks`` logged "Mocks
activés (simulation)". The jars now come from the one downloader CI uses,
``jvm_setup.download_tweety_jars``, and its verdict is the step's verdict.

The existing orchestration test patches ``download_test_jars`` itself, so it
could not see what the method does; these tests patch the downloader instead.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from project_core.core_from_scripts import project_setup
from project_core.core_from_scripts.common_utils import Logger

DOWNLOADER = "argumentation_analysis.core.jvm_setup.download_tweety_jars"


@pytest.fixture
def setup():
    logger = MagicMock(spec=Logger)
    with patch.object(project_setup, "EnvironmentManager") as manager, patch.object(
        project_setup, "ValidationEngine"
    ):
        manager.return_value.project_root = Path("/fake/dir")
        yield project_setup.ProjectSetup(logger=logger)


def test_a_failed_download_fails_the_test_setup(setup):
    with patch(DOWNLOADER, return_value=False) as downloader:
        assert setup.setup_environment("test") is False

    downloader.assert_called_once_with()
    setup.logger.success.assert_not_called()


def test_a_real_download_is_what_the_success_reports(setup):
    with patch(DOWNLOADER, return_value=True) as downloader:
        assert setup.setup_environment("test") is True

    downloader.assert_called_once_with()
    setup.logger.success.assert_called_once_with(
        "Environnement de test configuré avec succès."
    )


def test_no_step_logs_a_simulation(setup):
    with patch(DOWNLOADER, return_value=True):
        setup.setup_environment("test")

    logged = [str(call) for call in setup.logger.method_calls]
    assert not [line for line in logged if "simulation" in line], logged


def test_the_cli_no_longer_offers_mocks_it_never_applied():
    with patch("sys.argv", ["project_setup", "setup", "--env", "test", "--with-mocks"]):
        with pytest.raises(SystemExit) as exit_info:
            project_setup.main()

    assert exit_info.value.code == 2
