import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("provision_tools")


def provision():
    """
    Provisions and sets up all required portable tools like JDK.
    """
    try:
        # Add project root to sys.path to allow for absolute imports
        project_root = Path(__file__).parent.parent.parent.resolve()
        sys.path.insert(0, str(project_root))
        logger.info(f"Project root added to sys.path: {project_root}")

        from argumentation_analysis.core.setup.manage_portable_tools import setup_tools

        tools_dir = project_root / "argumentation_analysis" / "libs"
        tools_dir.mkdir(exist_ok=True)

        logger.info(f"--- Starting Portable Tools Provisioning ---")
        logger.info(f"Target tools directory: {tools_dir}")

        setup_tools(
            tools_dir_base_path=tools_dir,
            force_reinstall=False,
            skip_octave=True,  # Skipping Octave as it's not critical for core tests
        )

        logger.info("--- Portable Tools Provisioning Finished Successfully ---")

    except ImportError as e:
        logger.error(f"Failed to import a required module: {e}", exc_info=True)
        logger.error(
            "Please ensure you are running this script from within the 'projet-is' conda environment."
        )
        sys.exit(1)
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during tool provisioning: {e}", exc_info=True
        )
        sys.exit(1)


if __name__ == "__main__":
    provision()
