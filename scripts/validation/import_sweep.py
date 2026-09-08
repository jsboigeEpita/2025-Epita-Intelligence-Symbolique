"""Sweep: which modules under argumentation_analysis/ fail at plain import?
No fix, no judgement — just the instrument, run before anything is changed."""

import importlib, os, sys, traceback, warnings

warnings.simplefilter("ignore")
import logging

logging.disable(logging.CRITICAL)

ROOT = "argumentation_analysis"
mods = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "data", "libs")]
    for fn in filenames:
        if not fn.endswith(".py"):
            continue
        p = os.path.join(dirpath, fn).replace("\\", "/")
        m = p[:-3].replace("/", ".")
        if m.endswith(".__init__"):
            m = m[: -len(".__init__")]
        mods.append(m)
mods = sorted(set(mods))

ok, fail = [], []
buf = open(
    os.devnull, "w", encoding="utf-8"
)  # PAS StringIO : logging_utils appelle .reconfigure()
for m in mods:
    so, se = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = buf
    try:
        importlib.import_module(m)
        sys.stdout, sys.stderr = so, se
        ok.append(m)
    except BaseException as e:
        sys.stdout, sys.stderr = so, se
        tb = traceback.extract_tb(e.__traceback__)
        site = ""
        for fr in reversed(tb):
            if ROOT in fr.filename.replace("\\", "/"):
                site = "%s:%d" % (
                    fr.filename.replace("\\", "/").split(ROOT + "/")[-1],
                    fr.lineno,
                )
                break
        fail.append((m, type(e).__name__, str(e)[:150], site))
        # Un import raté laisse la chaîne ROOT.* dans un état partiel : le module
        # suivant lit alors `KeyError: '<parent>'` au lieu de la vraie cause.
        for k in [k for k in sys.modules if k == ROOT or k.startswith(ROOT + ".")]:
            del sys.modules[k]

print("TOTAL modules  :", len(mods))
print("import OK      :", len(ok))
print("import FAILED  :", len(fail))
print()
for m, k, msg, site in fail:
    print("%-62s %s: %s" % (m, k, msg))
    if site:
        print("%-62s   ^ at %s" % ("", site))
