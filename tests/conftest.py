# This file is for shared pytest fixtures.
# a.k.a, conftest.py is a local per-directory plugin for pytest.
# Pytest will look for a conftest.py file in the directory of the test file and all parent directories.
# https://docs.pytest.org/en/latest/how-to/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files
#
# For example, you can define a fixture here that creates a temporary directory for tests.
#
# from pytest import fixture
#
# @fixture
# def my_fixture():
#     return 42
