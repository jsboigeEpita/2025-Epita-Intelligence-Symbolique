#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""#1651 — sonde de chargement DLL torch (STATUS_ORDINAL_NOT_FOUND 0xc0000138).

Le skip-storm CI naît d'un échec de chargement natif de torch pendant la
collection : ``Windows fatal exception: code 0xc0000138`` à
``torch/__init__.py`` (boucle ``LoadLibraryExW`` sur ``torch/lib/*.dll``).
Le crash est une exception SEH muette — ni nom de DLL ni ordinal dans le log,
et la VM runner est détruite après le run. Cette sonde capture, AVANT que
torch ne se charge, ce que le crash emporte :

- le PATH effectif de la session (une entrée par ligne, numérotée) ;
- le résultat de ``os.add_dll_directory`` sur ``torch/lib`` et
  ``<env>/Library/bin``, et le fichier runtime MSVC qui gagne le précharge
  par nom (résolution GetModuleFileNameW) ;
- le résultat de chargement de CHAQUE DLL de ``torch/lib`` en rejouant la
  boucle exacte de ``torch/__init__.py`` (``LoadLibraryExW`` flags 0x1100,
  fallback LoadLibraryW-paths-patchés sur erreur 126) — un échec d'ordinal y
  est attrapable et nomme la DLL fautive, là où la boucle de torch meurt
  silencieusement. Taille + sha1 par DLL (détection d'extraction partielle).

Le log est écrit ligne à ligne avec flush immédiat et l'entrée
``ATTEMPT <dll>`` précède chaque chargement : si la sonde elle-même est
tuée par le crash, la dernière DLL tentée est le coupable.

Isolation : la sonde est invoquée en SOUS-PROCESSUS par
``tests/conftest.py::pytest_sessionstart`` (et à la main sur tout host).
Charger les DLL ici ne masque donc pas le défaut dans le processus pytest —
un pre-flight dans le processus parent guérirait le storm en chargeant les
DLL le premier, ce qui détruirait la chose mesurée.

``--selftest`` valide le chemin d'échec de la sonde sur un arbre fabriqué :
une fausse DLL (octets de texte) doit être nommée en échec, une vraie DLL
système copiée doit charger. Exit 0 uniquement si les deux comportements
sont observés — c'est le contrôle négatif du né-rouge.
"""

import argparse
import ctypes
import hashlib
import importlib.util
import os
import shutil
import sys
import tempfile
from pathlib import Path

EXIT_OK = 0
EXIT_DLL_FAILURE = 3
EXIT_SELFTEST_FAILED = 4


class ProbeLog:
    def __init__(self, path):
        self._fh = open(path, "w", encoding="utf-8", buffering=1)
        self.path = path

    def write(self, line):
        self._fh.write(line + "\n")
        print(f"[torch-dll-probe] {line}")

    def close(self):
        self._fh.close()


def _find_torch_lib_dir():
    spec = importlib.util.find_spec("torch")
    if spec is None or spec.origin is None:
        return None
    return Path(spec.origin).resolve().parent / "lib"


def _module_file(kernel32, name):
    kernel32.GetModuleHandleW.restype = ctypes.c_void_p
    kernel32.GetModuleFileNameW.restype = ctypes.c_uint
    kernel32.GetModuleFileNameW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_uint,
    ]
    handle = kernel32.GetModuleHandleW(name)
    if not handle:
        return "<not loaded>"
    buf = ctypes.create_unicode_buffer(1024)
    if not kernel32.GetModuleFileNameW(handle, buf, 1024):
        return "<path unavailable>"
    return buf.value


def _walk_dlls(lib_dir, log):
    """Rejoue la séquence de chargement de torch/__init__.py (2.2.2) pas à pas.

    Miroir fidèle : (1) ``os.add_dll_directory`` sur torch/lib et
    ``<env>/Library/bin``, (2) précharge par NOM des runtimes MSVC — c'est le
    seul moment où la résolution dépend de l'ordre de PATH, et la version du
    fichier gagnant est journalisée via ``GetModuleFileNameW`` —, (3) boucle
    ``LoadLibraryExW`` flags 0x1100 (sans PATH) avec le fallback
    LoadLibraryW-paths-patchés de torch sur erreur 126.
    """
    failures = []
    kernel32 = ctypes.WinDLL("kernel32.dll", use_last_error=True)
    kernel32.LoadLibraryExW.restype = ctypes.c_void_p
    kernel32.LoadLibraryW.restype = ctypes.c_void_p

    dll_dirs = [lib_dir]
    py_bin = Path(sys.exec_prefix) / "Library" / "bin"
    if py_bin.is_dir():
        dll_dirs.append(py_bin)
    for d in dll_dirs:
        cookie = os.add_dll_directory(str(d))
        log.write(f"add_dll_directory({d}) -> {'ok' if cookie else 'FAIL'}")

    for runtime in ("vcruntime140.dll", "msvcp140.dll", "vcruntime140_1.dll"):
        try:
            ctypes.CDLL(runtime)
        except OSError as exc:
            log.write(
                f"MSVC-PRELOAD {runtime} FAIL winerror={getattr(exc, 'winerror', 'NA')} {exc}"
            )
            failures.append(runtime)
        else:
            log.write(
                f"MSVC-PRELOAD {runtime} resolved={_module_file(kernel32, runtime)}"
            )

    dlls = sorted(lib_dir.glob("*.dll"))
    ordered = []
    for prime in ("c10.dll", "torch_cpu.dll"):
        match = lib_dir / prime
        if match.exists():
            ordered.append(match)
    ordered.extend(d for d in dlls if d not in ordered)
    path_patched = False

    for dll in ordered:
        data = dll.read_bytes()
        log.write(
            f"FILE {dll.name} size={len(data)} sha1={hashlib.sha1(data).hexdigest()[:16]}"
        )
        log.write(f"ATTEMPT {dll.name}")
        res = kernel32.LoadLibraryExW(str(dll), None, 0x00001100)
        last_error = ctypes.get_last_error()
        if res is None and last_error != 126:
            err = ctypes.WinError(last_error)
            log.write(
                f"FAIL {dll.name} winerror={last_error} {err.strerror} (mode 0x1100, sans PATH)"
            )
            failures.append(dll.name)
            continue
        if res is None:
            if not path_patched:
                os.environ["PATH"] = ";".join(
                    [str(d) for d in dll_dirs] + [os.environ["PATH"]]
                )
                path_patched = True
            log.write(f"FALLBACK-PATH {dll.name} (126 au 0x1100, retry LoadLibraryW)")
            res = kernel32.LoadLibraryW(str(dll))
            last_error = ctypes.get_last_error()
            if res is None:
                err = ctypes.WinError(last_error)
                log.write(
                    f"FAIL {dll.name} winerror={last_error} {err.strerror} (fallback PATH)"
                )
                failures.append(dll.name)
                continue
        log.write(f"OK {dll.name}")
    return failures, len(ordered)


def _snapshot_env(log, lib_dir):
    log.write(f"python={sys.version.split()[0]} exe={sys.executable}")
    log.write(f"cwd={os.getcwd()}")
    for key in (
        "CONDA_PREFIX",
        "CONDA_DEFAULT_ENV",
        "PYTHONPATH",
        "JAVA_HOME",
        "TORCH_DLL_PROBE",
    ):
        log.write(f"env:{key}={os.environ.get(key, '<unset>')}")
    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    log.write(f"PATH entries={len(path_entries)}")
    for i, entry in enumerate(path_entries):
        log.write(f"PATH[{i:02d}] {entry}")
    log.write(f"torch_lib_dir={lib_dir}")


def run_probe(log_path, only_dir=None):
    log = ProbeLog(log_path)
    try:
        lib_dir = Path(only_dir) if only_dir else _find_torch_lib_dir()
        if lib_dir is None or not lib_dir.is_dir():
            log.write("NO_TORCH_LIB_DIR (torch absent ou non résolu) — rien à sonder")
            return EXIT_OK
        _snapshot_env(log, lib_dir)
        failures, total = _walk_dlls(lib_dir, log)
        if failures:
            log.write(
                f"VERDICT {len(failures)}/{total} DLL en échec: {', '.join(failures)}"
            )
            return EXIT_DLL_FAILURE
        log.write(f"VERDICT {total}/{total} DLL chargées")
        return EXIT_OK
    finally:
        log.close()


def run_selftest(log_path):
    tmp = Path(tempfile.mkdtemp(prefix="torch_dll_probe_selftest_"))
    try:
        bad = tmp / "bogus_ordinal_probe.dll"
        bad.write_bytes(b"this is not a PE image and exports nothing\x00")
        good_src = Path(os.environ["SystemRoot"]) / "System32" / "version.dll"
        good = tmp / "good_system_copy.dll"
        shutil.copyfile(good_src, good)

        log = ProbeLog(log_path)
        try:
            log.write("SELFTEST negative control: bogus DLL must FAIL, naming the file")
            failures, total = _walk_dlls(tmp, log)
            log.write(f"SELFTEST walked={total} failures={failures}")
            bad_named = "bogus_ordinal_probe.dll" in failures
            good_loaded = "good_system_copy.dll" not in failures
            if not (total == 2 and bad_named and good_loaded):
                log.write("SELFTEST FAILED: le chemin d'échec de la sonde est cassé")
                return EXIT_SELFTEST_FAILED
            log.write("SELFTEST PASSED")
            return EXIT_OK
        finally:
            log.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--log", default="torch_dll_probe.log")
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="valide le chemin d'échec sur un arbre fabriqué (contrôle négatif)",
    )
    parser.add_argument(
        "--probe-dir",
        default=None,
        help="sonder CE répertoire au lieu de torch/lib (usage diagnostic)",
    )
    args = parser.parse_args()

    log_path = Path(args.log).resolve()
    if args.selftest:
        sys.exit(run_selftest(log_path))
    sys.exit(run_probe(log_path, only_dir=args.probe_dir))


if __name__ == "__main__":
    main()
