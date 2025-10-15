# ##############################################################################
# This module is deprecated and will be removed in a future version.
# Its functionality has been refactored into the 'argumentation_analysis.reporting' package.
# Please update imports to use the new 'ReportOrchestrator' class.
# ##############################################################################

# You can add a temporary import for backward compatibility if needed,
# but for now, we will mark it as deprecated.
import warnings

warnings.warn(
    "The 'report_generation' module is deprecated. Use the 'reporting' package instead.",
    DeprecationWarning,
    stacklevel=2,
)

# To avoid breaking existing code immediately, you could provide a facade here.
# For now, we will leave it mostly empty.
# from ..reporting.orchestrator import ReportOrchestrator
