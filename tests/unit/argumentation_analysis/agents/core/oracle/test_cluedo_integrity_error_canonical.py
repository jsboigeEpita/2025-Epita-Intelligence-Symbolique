"""Guards for the #2139 name-collision fixes.

Collision #1: ``CluedoIntegrityError`` used to be defined twice with
incompatible bases — ``permissions.py`` (plain ``Exception``, the class
actually raised) and ``error_handling.py`` (``OracleError``, the class the
``isinstance`` chain tests). The handler branch could never match the real
exception. The canonical class now lives in ``error_handling`` and
``permissions`` imports it.
"""

import pytest

from argumentation_analysis.agents.core.oracle import error_handling, permissions
from argumentation_analysis.agents.core.oracle.error_handling import OracleErrorHandler


def test_permissions_and_error_handling_share_one_class():
    assert (
        permissions.CluedoIntegrityError is error_handling.CluedoIntegrityError
    ), "CluedoIntegrityError must be a single class shared by both modules"


def test_handler_counts_the_exception_permissions_actually_raises():
    handler = OracleErrorHandler()

    with pytest.raises(permissions.CluedoIntegrityError):
        permissions.validate_cluedo_method_access("get_solution", "TestAgent")

    try:
        permissions.validate_cluedo_method_access("get_solution", "TestAgent")
    except Exception as caught:  # noqa: BLE001 - the handler takes any exception
        error = caught
        info = handler.handle_oracle_error(error, context="collision-2139")

    assert isinstance(error, error_handling.CluedoIntegrityError)
    assert handler.get_error_statistics()["integrity_errors"] == 1
    assert info["type"] == "CluedoIntegrityError"
