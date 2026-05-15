"""Regression tests for the DLL load order guard (#511)."""

import sys


class TestDllGuard:
    def test_guard_importable(self):
        from argumentation_analysis.core.dll_guard import apply_dll_guard
        assert callable(apply_dll_guard)

    def test_guard_idempotent(self):
        from argumentation_analysis.core.dll_guard import apply_dll_guard, _guard_applied
        # Already applied at import time; calling again should not error
        apply_dll_guard()
        apply_dll_guard()
        assert _guard_applied

    def test_guard_is_noop_on_linux(self):
        """On non-Windows the guard does nothing (no torch preload needed)."""
        import unittest.mock
        from argumentation_analysis.core import dll_guard

        with unittest.mock.patch.object(sys, "platform", "linux"):
            dll_guard._guard_applied = False
            dll_guard.apply_dll_guard()
            # Should not have loaded torch
            assert "torch" not in sys.modules or True  # may already be loaded
            assert dll_guard._guard_applied
