# Rapport de la Campagne de Re-vérification du 22/06/2025
* [SUCCÈS] scripts/apps/webapp/launch_webapp_background.py
* [SUCCÈS] scripts/orchestration/orchestrate_complex_analysis.py
* [ÉCHEC] argumentation_analysis/scripts/simulate_balanced_participation.py
```
Traceback (most recent call last):
  File "C:\tools\miniconda3\envs\projet-is\lib\runpy.py", line 196, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "C:\tools\miniconda3\envs\projet-is\lib\runpy.py", line 86, in _run_code
    exec(code, run_globals)
  File "C:\dev\2025-Epita-Intelligence-Symbolique\argumentation_analysis\scripts\simulate_balanced_participation.py", line 35, in <module>
    from argumentation_analysis.core.strategies import BalancedParticipationStrategy
  File "C:\dev\2025-Epita-Intelligence-Symbolique\argumentation_analysis\core\strategies.py", line 9, in <module>
    from argumentation_analysis.orchestration.base import SelectionStrategy, TerminationStrategy
  File "C:\dev\2025-Epita-Intelligence-Symbolique\argumentation_analysis\orchestration\__init__.py", line 6, in <module>
    from .cluedo_extended_orchestrator import CluedoExtendedOrchestrator
  File "C:\dev\2025-Epita-Intelligence-Symbolique\argumentation_analysis\orchestration\cluedo_extended_orchestrator.py", line 54, in <module>
    from ..agents.core.logic.watson_logic_assistant import WatsonLogicAssistant
  File "C:\dev\2025-Epita-Intelligence-Symbolique\argumentation_analysis\agents\core\logic\__init__.py", line 14, in <module>
    from .propositional_logic_agent import PropositionalLogicAgent
  File "C:\dev\2025-Epita-Intelligence-Symbolique\argumentation_analysis\agents\core\logic\propositional_logic_agent.py", line 33, in <module>
    from .tweety_bridge import TweetyBridge
  File "C:\dev\2025-Epita-Intelligence-Symbolique\argumentation_analysis\agents\core\logic\tweety_bridge.py", line 21, in <module>
    from .tweety_initializer import TweetyInitializer
  File "C:\dev\2025-Epita-Intelligence-Symbolique\argumentation_analysis\agents\core\logic\tweety_initializer.py", line 10, in <module>
    from argumentation_analysis.core.utils.logging_utils import setup_logging
  File "C:\dev\2025-Epita-Intelligence-Symbolique\argumentation_analysis\core\utils\__init__.py", line 7, in <module>
    from . import file_utils
  File "C:\dev\2025-Epita-Intelligence-Symbolique\argumentation_analysis\core\utils\file_utils.py", line 30, in <module>
    from .markdown_utils import *
  File "C:\dev\2025-Epita-Intelligence-Symbolique\argumentation_analysis\core\utils\markdown_utils.py", line 8, in <module>
    import markdown # type: ignore
ModuleNotFoundError: No module named 'markdown'
```
* [ÉCHEC] argumentation_analysis/scripts/generate_and_analyze_arguments.py
```
C:\tools\miniconda3\envs\projet-is\python.exe: No module named argumentation_analysis.scripts.generate_and_analyze_arguments
```
* [ÉCHEC] argumentation_analysis/main_app.py
```
C:\tools\miniconda3\envs\projet-is\python.exe: No module named argumentation_analysis.main_app
```