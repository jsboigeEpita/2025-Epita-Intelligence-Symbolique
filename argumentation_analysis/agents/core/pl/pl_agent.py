# akerdomi/argumentation_analysis/agents/core/pl/pl_agent.py
#
# This file is a compatibility wrapper to maintain backward compatibility for student projects
# that still import from the old path.
#
# DO NOT ADD NEW Funarki. If not, the file will be removed in a future version.
#
# Original file location (legacy): argumentation_analysis/agents/core/pl/pl_agent.py
# New file location (current): argumentation_analysis/agents/logic/propositional_logic_agent.py

import warnings
import logging

# Configure a specific logger for deprecation warnings to allow fine-grained filtering if needed.
deprecation_logger = logging.getLogger('deprecation.student_compat')

# --- Compatibility Wrapper ---

try:
    # Attempt to import from the new, correct location.
    from argumentation_analysis.agents.logic.propositional_logic_agent import PropositionalLogicAgent

    # Define the legacy alias for backward compatibility.
    # This allows old code `from ...pl.pl_agent import PLAgent` to continue working.
    PLAgent = PropositionalLogicAgent

    # Formulate a detailed warning message for developers and students.
    DEPRECATION_MESSAGE = (
        "IMPORT REDIRECTION (Compatibility Mode): The module 'argumentation_analysis.agents.core.pl.pl_agent' "
        "is deprecated and will be removed in a future version. "
        f"Please update your imports to use the new location: "
        "'argumentation_analysis.agents.logic.propositional_logic_agent'. "
        f"The alias 'PLAgent' is also deprecated; please use 'PropositionalLogicAgent' directly."
    )

    # Issue a warning to alert the user that they are using an outdated import path.
    # Using DeprecationWarning is standard practice for this kind of issue.
    # warnings.warn(DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)

    # Also, log the warning. This helps in tracking usage of the legacy path in logs
    # without necessarily cluttering the console, depending on log configuration.
    # deprecation_logger.warning(DEPRECATION_MESSAGE)

except ImportError as e:
    # If the import from the new location fails, it signifies a deeper problem in the project structure,
    # and we should raise an error that clearly explains the situation.
    raise ImportError(
        "Failed to import 'PropositionalLogicAgent' from its new location "
        "'argumentation_analysis.agents.logic.propositional_logic_agent'. "
        "This indicates a potential issue with the project's structure or PYTHONPATH. "
        f"Original error: {e}"
    )

# --- Metadata for Static Analysis and Tooling ---

# __all__ controls what `from ... import *` imports. By defining it, we make the module's public API explicit.
__all__ = ['PLAgent', 'PropositionalLogicAgent']

# A tuple of deprecated names helps automated tools to identify and flag usage of legacy code.
__deprecated__ = {
    "PLAgent": {
        "new_name": "PropositionalLogicAgent",
        "since_version": "1.5.0",
        "removal_version": "2.0.0"
    }
}
