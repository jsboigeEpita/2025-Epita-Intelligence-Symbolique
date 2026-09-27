# -*- coding: utf-8 -*-
"""#2180 — `RESULTS_DIR` (un Path) ne sert plus de clé de contenu.

Même famille de défaut que #2177 (`DATA_DIR`) : `RESULTS_DIR` est un
``pathlib.Path`` utilisé comme clé de dictionnaire dans des charges utiles de
messages et de résultats. Écrivains et lecteurs étant orphelins de part et
d'autre (aucun consommateur du type ``objective_completion``, aucun écrivain
de la clé dans les retours de ``process_task``), rien ne cassait visiblement —
mais toute frontière JSON lève ``TypeError: keys must be str... not
WindowsPath``. Ces gardes fixent le contrat : la charge de résultats vit sous
la clé chaîne ``"results"`` (clé nommée : elle siège À CÔTÉ de clés nommées
dans le payload, pas au niveau où ``#2177`` a posé ``"data"``).

#2786 : l'écrivain côté coordinateur, le rapport ``objective_completion``, est
retiré (aucun lecteur, ``status`` à ``completed`` en dur même sur un échec).
Sa garde de sérialisation part avec lui ; restent les écrivains des gabarits.
"""

import json
from argumentation_analysis.orchestration.hierarchical.templates.analysis_tool_template import (
    BaseAnalysisTool,
)
from argumentation_analysis.orchestration.hierarchical.templates.analysis_type_template import (
    BaseAnalysisType,
)


class TestTemplateWriters:
    def test_analysis_tool_get_results_serializes(self):
        results = BaseAnalysisTool({"name": "my_tool"}).get_results()
        round_tripped = json.loads(json.dumps(results))
        assert round_tripped["tool"] == "my_tool"
        assert round_tripped["results"] == {}

    def test_analysis_type_expected_results_serializes(self):
        results = BaseAnalysisType({"name": "my_type"}).get_expected_results()
        round_tripped = json.loads(json.dumps(results))
        assert round_tripped["analysis_type"] == "my_type"
        assert round_tripped["results"] == {}
