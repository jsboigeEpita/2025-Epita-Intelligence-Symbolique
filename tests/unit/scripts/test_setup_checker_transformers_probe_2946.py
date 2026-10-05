# -*- coding: utf-8 -*-
"""#2946 — la ligne ``transformers`` du vérificateur n'est plus une sonde aveugle.

``scripts/setup/test_all_dependencies.py`` testait import + version : dans un
env où transformers a désactivé torch (5.x servi avec un torch plus vieux —
l'exact contenu du lock de main avant ``7774ea283``), l'import réussit et la
ligne répondait ``transformers: OK`` alors que chaque classe modèle lève
``ImportError`` au premier usage. Le défaut passait du contrôle de
l'installation au premier appel en production.

La ligne rejoue maintenant la sonde du témoin de gate
(``tests/unit/test_gate_env_transformers_uses_torch_2946.py``) : importée,
pas recopiée — la preuve que les deux surfaces ne dérivent pas est qu'un
changement de la sonde redden les deux témoins ensemble.

Née rouge sur le lock d'avant ``7774ea283`` (transformers 5.17.0 / torch
2.2.2, ``conda-lock install`` du lock à ``6887b8d58``) : la ligne ÉCHOUE.
Verte sur le lock courant (transformers 4.57.6 / torch 2.2.2) : la ligne
est OK.
"""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
_CHECKER = REPO_ROOT / "scripts" / "setup" / "test_all_dependencies.py"
_GATE_WITNESS = "tests.unit.test_gate_env_transformers_uses_torch_2946"


def _load_checker():
    spec = importlib.util.spec_from_file_location("test_all_dependencies", _CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestTransformersRowAnswersTheRealQuestion:
    def test_the_row_runs_the_real_probe(self):
        """Import + version passent, puis la ligne doit construire un vrai
        modèle — pas s'arrêter à l'import. Échoue (False) dans un env où
        transformers a désactivé son backend torch."""
        checker = _load_checker()
        result = checker.test_dependency(
            {"name": "transformers", "min_version": "4.20.0"}
        )
        assert result is True, (
            "#2946: la ligne transformers du vérificateur échoue dans cet env "
            "— soit transformers y a désactivé torch (le vérificateur vient "
            "de le détecter : c'est son travail), soit la sonde est cassée"
        )

    def test_the_probe_is_shared_not_recopied(self):
        """La sonde vient du témoin de gate, importée — le corps du checker
        ne porte aucune copie locale (aucun ``BertConfig``, aucun
        ``is_torch_available``) : les deux surfaces ne peuvent pas dériver."""
        source = _CHECKER.read_text(encoding="utf-8-sig")
        assert _GATE_WITNESS in source, (
            "#2946: le checker n'importe plus la sonde du témoin de gate "
            f"({_GATE_WITNESS}) — recopie locale ou sonde perdue ?"
        )
        for probe_fragment in ("BertConfig", "is_torch_available"):
            assert probe_fragment not in source, (
                "#2946: le checker porte une copie locale de la sonde "
                f"({probe_fragment!r}) — elle doit rester importée depuis le "
                "témoin de gate pour que les deux surfaces ne dérivent pas"
            )
