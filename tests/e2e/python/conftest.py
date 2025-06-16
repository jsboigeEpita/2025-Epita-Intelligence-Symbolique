import pytest
import sys
import os
import importlib
import logging
from argumentation_analysis.core.jvm_setup import initialize_jvm, shutdown_jvm

# Configure logger
logger = logging.getLogger(__name__)

def deep_delete_from_sys_modules(module_name_prefix):
    """Helper to remove a module and its sub-modules from sys.modules."""
    keys_to_delete = [k for k in sys.modules if k == module_name_prefix or k.startswith(module_name_prefix + '.')]
    if keys_to_delete:
        logger.info(f"E2E_CONFTEST: Cleaning sys.modules for prefix '{module_name_prefix}': {keys_to_delete}")
    for key in keys_to_delete:
        try:
            del sys.modules[key]
        except KeyError:
            pass

@pytest.fixture(scope="session", autouse=True)
def e2e_environment_setup_session(request):
    """
    A session-scoped autouse fixture to set up the entire E2E test environment.
    This fixture ensures that for ALL tests run in this directory and subdirectories,
    the environment is correctly configured with REAL JPype and REAL NumPy.
    """
    logger.info("E2E_CONFTEST: STARTING E2E session setup.")

    # 1. Ensure tests/mocks is NOT in path to prevent mock imports
    mocks_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'mocks'))
    original_sys_path = list(sys.path)
    if mocks_path in sys.path:
        logger.info(f"E2E_CONFTEST: Temporarily removing mocks path from sys.path: {mocks_path}")
        sys.path.remove(mocks_path)

    # 3. Import and initialize REAL JPype and JVM
    try:
        logger.info("E2E_CONFTEST: Importing REAL jpype.")
        import jpype
        sys.modules['jpype'] = jpype
        
        logger.info("E2E_CONFTEST: Initializing JVM.")
        # We assume initialize_jvm handles starting if not started, and configuring classpath
        initialize_jvm()
        
        if not jpype.isJVMStarted():
            pytest.fail("E2E_CONFTEST: JVM failed to start!", pytrace=False)
        
        logger.info(f"E2E_CONFTEST: REAL JPype and JVM are active. Version: {jpype.getJVMVersion()}")

    except ImportError as e:
        pytest.fail(f"E2E_CONFTEST: Failed to import REAL jpype: {e}", pytrace=False)
    except Exception as e:
        pytest.fail(f"E2E_CONFTEST: An error occurred during JVM initialization: {e}", pytrace=False)


    # 4. Import REAL numpy, pandas, etc.
    try:
        logger.info("E2E_CONFTEST: Importing REAL numpy.")
        import numpy
        sys.modules['numpy'] = numpy
        logger.info(f"E2E_CONFTEST: REAL NumPy loaded. Version: {numpy.__version__}")
        
        logger.info("E2E_CONFTEST: Re-importing pandas to bind to real numpy.")
        deep_delete_from_sys_modules("pandas")
        import pandas
        sys.modules['pandas'] = pandas
        logger.info("E2E_CONFTEST: REAL Pandas re-loaded.")
        
    except ImportError as e:
        pytest.fail(f"E2E_CONFTEST: Failed to import REAL numpy or pandas: {e}", pytrace=False)
    finally:
        # Restore sys.path to its original state
        sys.path = original_sys_path
        logger.info("E2E_CONFTEST: Restored original sys.path.")

    yield
    
    logger.info("E2E_CONFTEST: E2E session teardown.")
    # The shutdown_jvm is already handled by argumentation_analysis.core.jvm_setup via atexit,
    # so we don't need to call it explicitly here.
    # If we needed to, it would be: shutdown_jvm()