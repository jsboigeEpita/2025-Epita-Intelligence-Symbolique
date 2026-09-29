"""#2856: the env the gate installs must actually load torch.

Main's ``conda-lock.yml`` installs BOTH intel-openmp 2026.1.0 (the #1651 pin —
pytorch 2.2.2 imports ``libiomp5md.dll`` by ordinals only intel-openmp exports)
and llvm-openmp 22.1.2 (pulled by mkl 2025.3.1). Both ship ``Library/bin/
libiomp5md.dll``; with ``path_conflict: clobber`` the file that survives is
llvm-openmp's (684,872 B), and ``import torch`` dies with ``WinError 182`` on
``fbgemm.dll`` — measured on ai-01 and po-2025, in a fresh
``conda-lock install`` env and in CI (probe VERDICT 4/8). The #1651 verdict
"the runner image cannot load torch DLLs" was this defect, not an image
property.

Two witnesses:

- torch imports (and computes) in a FRESH SUBPROCESS — the session conftest
  swallows the ``OSError`` at import time, so an in-process import would
  never redden;
- when torch relies on the environment's ``Library/bin/libiomp5md.dll`` (the
  conda build; a pip torch bundles its own copy in ``torch/lib``), that DLL
  exports the ordinals pytorch 2.2.2 imports by number (#1651's measured
  list). intel-openmp 2026.1.0 exports them; llvm-openmp 22.1.2 does not.
"""

import ctypes
import subprocess
import sys
from pathlib import Path

import pytest

_TORCH_SMOKE = (
    "import torch; print(torch.__version__); print(float(torch.ones(2).sum()))"
)

# The ordinals pytorch 2.2.2 imports from libiomp5md.dll (environment.yml's
# #1651 note, verified on intel-openmp builds _246/_247/_248).
_TORCH_ORDINALS = (703, 706, 707, 900, 904, 958, 961)


def test_the_gate_env_imports_torch_in_a_fresh_subprocess():
    proc = subprocess.run(
        [sys.executable, "-c", _TORCH_SMOKE],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, (
        "torch does not load in this env (#2856):\n"
        f"stdout: {proc.stdout[-400:]}\nstderr: {proc.stderr[-800:]}"
    )
    # The compute ran, not just the import.
    assert proc.stdout.strip().splitlines()[-1] == "2.0", proc.stdout


def test_the_envs_libiomp5md_exports_the_ordinals_torch_imports():
    """One provider of libiomp5md.dll, and it is the one torch can call."""
    if sys.platform != "win32":
        pytest.skip("the libiomp5md ordinal contract is Windows-only")
    dll = Path(sys.prefix, "Library", "bin", "libiomp5md.dll")
    if not dll.is_file():
        pytest.skip(f"no conda Library/bin libiomp5md.dll in this env ({sys.prefix})")
    bundled = Path(sys.prefix, "lib", "site-packages", "torch", "lib", "libiomp5md.dll")
    if bundled.is_file():
        pytest.skip(
            "this env's torch bundles its own libiomp5md (pip wheel) — the "
            "environment DLL is not on torch's import path"
        )
    lib = ctypes.WinDLL(str(dll))
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    # restype must be c_void_p: the default c_int truncates the returned
    # procedure address on win64 and the probe reads every ordinal as absent.
    kernel32.GetProcAddress.restype = ctypes.c_void_p
    kernel32.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    missing = [
        ordinal
        for ordinal in _TORCH_ORDINALS
        if not kernel32.GetProcAddress(lib._handle, ctypes.c_void_p(ordinal))
    ]
    assert not missing, (
        f"{dll} does not export ordinals {missing} that pytorch 2.2.2 imports "
        "by number — this is llvm-openmp's runtime, the #2856 clobber "
        "(torch will fail with WinError 182)"
    )
