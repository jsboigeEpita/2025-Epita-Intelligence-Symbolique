import pytest
import jpype
import logging
import os
import threading
import time
from argumentation_analysis.agents.core.logic.tweety_initializer import TweetyInitializer

logger = logging.getLogger(__name__)

@pytest.fixture(scope="session", autouse=True)
def jvm_session():
    """
    Manages the JPype JVM lifecycle for the entire test session.
    Starts the JVM before any tests run and shuts it down after all tests are complete.
    """
    logger.info("---------- Pytest session starting: Initializing JVM... ----------")
    try:
        if not jpype.isJVMStarted():
            TweetyInitializer.initialize_jvm()
            logger.info("JVM started successfully for the test session.")
        else:
            logger.info("JVM was already started.")
    except Exception as e:
        logger.error(f"Failed to start JVM: {e}", exc_info=True)
        pytest.exit(f"JVM initialization failed: {e}", 1)

    yield

    logger.info("---------- Pytest session finished: Shutting down JVM... ----------")
    try:
        if jpype.isJVMStarted():
            logger.info("Preparing to shut down JVM. Waiting 1 second...")
            time.sleep(1)
            jpype.shutdownJVM()
            logger.info("JVM shut down successfully.")
        else:
            logger.info("JVM was already shut down or never started.")
    except Exception as e:
        logger.error(f"Error shutting down JVM: {e}", exc_info=True)