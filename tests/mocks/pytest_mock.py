# -*- coding: utf-8 -*-
"""
Mock pour pytest - Compatibilité avec les tests existants
"""


class MockPytest:
    """Mock simple pour pytest"""

    @staticmethod
    def skip(reason=""):
        """Mock pour pytest.skip"""

        def decorator(func):
            def wrapper(*args, **kwargs):
                print(f"Test skipped: {reason}")
                return None

            return wrapper

        return decorator

    @staticmethod
    def mark():
        """Mock pour pytest.mark"""

        class Mark:
            @staticmethod
            def parametrize(*args, **kwargs):
                def decorator(func):
                    return func

                return decorator

        return Mark()


# Remplacer pytest par le mock
import sys

sys.modules["pytest"] = MockPytest()
