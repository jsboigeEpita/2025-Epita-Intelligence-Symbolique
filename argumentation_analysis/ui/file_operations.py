# This file is a proxy to redirect imports to the core.io_manager
# to fix import errors without modifying all the files that use them.

from argumentation_analysis.core.io_manager import (
    load_extract_definitions,
    save_extract_definitions,
)

# You can also add a logger to warn about the redirection if you want.
import logging

file_ops_logger = logging.getLogger(__name__)
file_ops_logger.warning(
    "This module is deprecated. Please import from argumentation_analysis.core.io_manager directly."
)
