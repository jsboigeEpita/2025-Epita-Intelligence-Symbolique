import sys
import pytest
import logging
from unittest import mock
from typing import Callable, Optional

# Import the function to test
from argumentation_analysis.utils.dev_tools.mock_utils import setup_jpype_mock

# Attempt to import jpype for type hinting and direct access if already patched.
# The tests will primarily rely on the dynamically imported 'jpype' after setup.
try:
    import jpype as jpype_module_for_typing
except ImportError:
    jpype_module_for_typing = None


class TestSetupJpypeMock:
    """
    Test suite for the setup_jpype_mock function.
    """
    teardown_jpype_mock_func: Optional[Callable[[], None]] = None
    original_jpype_in_sys_modules = None

    def setup_method(self):
        """
        Called before each test method.
        Ensures 'jpype' is not in sys.modules to simulate it not being imported,
        or stores the original to restore later.
        Initializes the JPype mock.
        """
        if 'jpype' in sys.modules:
            self.original_jpype_in_sys_modules = sys.modules['jpype']
            del sys.modules['jpype']
        else:
            self.original_jpype_in_sys_modules = None
        
        # Initialize the mock and store the teardown function
        # self.teardown_jpype_mock_func = setup_jpype_mock() # Will be called in each test

    def teardown_method(self):
        """
        Called after each test method.
        Calls the stored teardown function to clean up mocks and restores sys.modules.
        """
        if self.teardown_jpype_mock_func:
            try:
                self.teardown_jpype_mock_func()
            except Exception as e:
                logging.error(f"Erreur lors du teardown du mock JPype : {e}")
        
        # Ensure sys.modules is clean regarding jpype, even if teardown failed
        if 'jpype' in sys.modules:
            # If it's our mock, it should have been removed by teardown.
            # If it's something else, or teardown failed, remove it.
            if isinstance(sys.modules['jpype'], mock.MagicMock):
                 del sys.modules['jpype']
        
        if self.original_jpype_in_sys_modules:
            sys.modules['jpype'] = self.original_jpype_in_sys_modules
        elif 'jpype' in sys.modules and not isinstance(sys.modules['jpype'], mock.MagicMock):
            # If original was None, but now there's a non-mock jpype, something is odd.
            # This case should ideally not happen if setup/teardown is correct.
            pass # Or del sys.modules['jpype'] if strict cleanup is desired

        self.teardown_jpype_mock_func = None


    def test_jpype_attributes_are_mocked_after_setup(self, caplog):
        """
        Tests that after calling setup_jpype_mock, the attributes of the
        imported 'jpype' module are indeed mocks.
        """
        caplog.set_level(logging.INFO)
        mock_jvm_path = "/test/jvm/path"
        self.teardown_jpype_mock_func = setup_jpype_mock(mock_jvm_path=mock_jvm_path)
        
        import jpype # Import after mock is injected

        assert isinstance(jpype.startJVM, mock.Mock), "jpype.startJVM should be a mock."
        assert isinstance(jpype.shutdownJVM, mock.Mock), "jpype.shutdownJVM should be a mock."
        assert isinstance(jpype.isJVMStarted, mock.Mock), "jpype.isJVMStarted should be a mock."
        assert isinstance(jpype.getDefaultJVMPath, mock.Mock), "jpype.getDefaultJVMPath should be a mock."
        assert isinstance(jpype.JPackage, mock.MagicMock), "jpype.JPackage should be a MagicMock."
        
        # Verify getDefaultJVMPath behavior
        assert jpype.getDefaultJVMPath() == mock_jvm_path

        # Verify logging
        assert "Activation du mock JPype par injection dans sys.modules..." in caplog.text
        assert "Mock JPype injecté dans sys.modules." in caplog.text


    def test_jpype_mock_jvm_state_logic(self, caplog):
        """
        Tests the logic of the mocked JVM state (started/stopped).
        """
        caplog.set_level(logging.INFO)
        self.teardown_jpype_mock_func = setup_jpype_mock()
        import jpype

        assert not jpype.isJVMStarted(), "JVM should initially be not started."

        jpype.startJVM()
        assert "jpype.startJVM (mock) appelé." in caplog.text
        assert jpype.isJVMStarted(), "JVM should be started after mock startJVM call."

        jpype.shutdownJVM()
        assert "jpype.shutdownJVM (mock) appelé." in caplog.text
        assert not jpype.isJVMStarted(), "JVM should be stopped after mock shutdownJVM call."

    def test_jpype_mock_jpackage_structure(self):
        """
        Tests the mocked structure of jpype.JPackage.
        """
        self.teardown_jpype_mock_func = setup_jpype_mock()
        import jpype

        # Test the pre-configured java.lang.String path
        JavaLangString = jpype.JPackage("java").lang.String
        assert isinstance(JavaLangString, mock.MagicMock)
        
        string_instance_mock = JavaLangString("test")
        assert isinstance(string_instance_mock, mock.MagicMock)
        
        # Test dynamic package creation (MagicMock behavior)
        MyCustomPackage = jpype.JPackage("com").example.custom
        assert isinstance(MyCustomPackage, mock.MagicMock)
        MyClass = MyCustomPackage.MyClass
        assert isinstance(MyClass, mock.MagicMock)
        my_instance = MyClass()
        assert isinstance(my_instance, mock.MagicMock)

    def test_setup_jpype_mock_default_jvm_path(self):
        """
        Tests that getDefaultJVMPath returns the default mock path if none is provided.
        """
        self.teardown_jpype_mock_func = setup_jpype_mock(mock_jvm_path=None)
        import jpype
        assert jpype.getDefaultJVMPath() == "mock/jvm/path"

    def test_setup_jpype_mock_called_multiple_times_updates_path(self, caplog):
        """
        Tests that calling setup_jpype_mock multiple times correctly updates
        the behavior of the mock (e.g., getDefaultJVMPath).
        The state of the JVM (isJVMStarted) should also be reset.
        """
        caplog.set_level(logging.INFO)

        # Call 1
        path1 = "/path/num/one"
        teardown1 = setup_jpype_mock(mock_jvm_path=path1)
        import jpype as jpype1
        assert jpype1.getDefaultJVMPath() == path1
        jpype1.startJVM()
        assert jpype1.isJVMStarted()
        teardown1() # Stop first set of mocks

        # Ensure jpype is removed from sys.modules so the next import gets the new mock
        if 'jpype' in sys.modules: # Should have been removed by teardown1
            del sys.modules['jpype']

        # Call 2
        path2 = "/path/num/two"
        self.teardown_jpype_mock_func = setup_jpype_mock(mock_jvm_path=path2)
        import jpype # Re-import to get the newly injected mock
        
        assert jpype.getDefaultJVMPath() == path2
        assert not jpype.isJVMStarted(), "JVM state should be reset on re-mocking"
        
        # Verify logging from the second call
        log_records = [r.message for r in caplog.records if "mock_utils" in r.name] # Filter by logger name
        # Check for the new log messages
        assert "Activation du mock JPype par injection dans sys.modules..." in log_records
        assert "Mock JPype injecté dans sys.modules." in log_records
        
        jpype.startJVM() # This will log the path usage
        assert f"jpype.startJVM (mock) appelé. Chemin (simulé): {path2}" in caplog.text


    def test_setup_jpype_mock_handles_jpype_initially_not_imported(self, caplog):
        """
        Tests that setup_jpype_mock works even if 'jpype' was not in sys.modules.
        This is implicitly covered by setup_method, but an explicit test is good.
        """
        caplog.set_level(logging.INFO)
        # setup_method ensures 'jpype' is removed from sys.modules if it existed.
        assert 'jpype' not in sys.modules

        self.teardown_jpype_mock_func = setup_jpype_mock()
        import jpype # Should now be the mocked version
        
        assert isinstance(jpype.isJVMStarted, mock.Mock)
        assert "Mock JPype injecté dans sys.modules." in caplog.text

    def test_mock_start_jvm_logs_path_usage(self, caplog):
        """
        Tests that the mocked startJVM logs which JVM path it's (notionally) using.
        """
        caplog.set_level(logging.INFO)
        
        # Scenario 1: mock_jvm_path provided to setup_jpype_mock
        custom_path = "/my/custom/jvm"
        teardown1 = setup_jpype_mock(mock_jvm_path=custom_path)
        import jpype
        jpype.startJVM() # Call without jvmpath argument
        assert f"jpype.startJVM (mock) appelé. Chemin (simulé): {custom_path}" in caplog.text
        teardown1()
        if 'jpype' in sys.modules: del sys.modules['jpype'] # Ensure clean state
        caplog.clear()

        # Scenario 2: mock_jvm_path is None (default path used)
        teardown2 = setup_jpype_mock(mock_jvm_path=None)
        import jpype as jpype_default # Re-import to get new mock
        jpype_default.startJVM() # Call without jvmpath argument
        assert f"jpype.startJVM (mock) appelé. Chemin (simulé): mock/jvm/path" in caplog.text
        teardown2()
        if 'jpype' in sys.modules: del sys.modules['jpype'] # Ensure clean state
        caplog.clear()

        # Scenario 3: jvmpath explicitly passed to startJVM (should take precedence in call)
        explicit_path = "/explicit/startjvm/path"
        teardown3 = setup_jpype_mock(mock_jvm_path="/should/be/ignored/by/call")
        import jpype as jpype_explicit # Re-import to get new mock
        
        jpype_explicit.startJVM(jvmpath=explicit_path)
        # The log should reflect the path passed to startJVM, as per the updated mock_start_jvm_func
        assert f"jpype.startJVM (mock) appelé. Chemin (simulé): {explicit_path}" in caplog.text
        
        relevant_logs = [r.message for r in caplog.records if "jpype.startJVM (mock) appelé." in r.message]
        assert len(relevant_logs) > 0
        assert f"Chemin (simulé): {explicit_path}" in relevant_logs[-1]

        teardown3()
        if 'jpype' in sys.modules: del sys.modules['jpype'] # Ensure clean state
        caplog.clear()