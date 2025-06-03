import sys
import pytest
import logging
from unittest import mock

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
    active_patches: dict = {}
    original_jpype_in_sys_modules = None

    def setup_method(self):
        """
        Called before each test method.
        Ensures 'jpype' is not in sys.modules to simulate it not being imported,
        or stores the original to restore later.
        """
        if 'jpype' in sys.modules:
            self.original_jpype_in_sys_modules = sys.modules['jpype']
            del sys.modules['jpype']
        else:
            self.original_jpype_in_sys_modules = None
        
        # Clear any patches from previous tests, though teardown should handle this.
        self.active_patches = {}

    def teardown_method(self):
        """
        Called after each test method.
        Stops all active patches and restores sys.modules.
        """
        for patch_name, patch_obj in self.active_patches.items():
            try:
                patch_obj.stop()
            except RuntimeError: # Patch not started
                pass
        
        if 'jpype' in sys.modules:
            del sys.modules['jpype'] # Remove the potentially mocked version

        if self.original_jpype_in_sys_modules:
            sys.modules['jpype'] = self.original_jpype_in_sys_modules
        
        self.active_patches = {}


    def test_setup_jpype_mock_returns_patch_objects(self):
        """
        Tests that setup_jpype_mock returns a dictionary of active patch objects.
        """
        self.active_patches = setup_jpype_mock()
        assert isinstance(self.active_patches, dict)
        expected_keys = ["startJVM", "shutdownJVM", "isJVMStarted", "JPackage", "getDefaultJVMPath"]
        for key in expected_keys:
            assert key in self.active_patches
            assert isinstance(self.active_patches[key], mock.patch)

    def test_jpype_attributes_are_mocked_after_setup(self, caplog):
        """
        Tests that after calling setup_jpype_mock, the attributes of the
        imported 'jpype' module are indeed mocks.
        """
        caplog.set_level(logging.INFO)
        mock_jvm_path = "/test/jvm/path"
        self.active_patches = setup_jpype_mock(mock_jvm_path=mock_jvm_path)
        
        import jpype # Import after patches are active

        assert isinstance(jpype.startJVM, mock.Mock), "jpype.startJVM should be a mock."
        assert isinstance(jpype.shutdownJVM, mock.Mock), "jpype.shutdownJVM should be a mock."
        assert isinstance(jpype.isJVMStarted, mock.Mock), "jpype.isJVMStarted should be a mock."
        assert isinstance(jpype.getDefaultJVMPath, mock.Mock), "jpype.getDefaultJVMPath should be a mock."
        assert isinstance(jpype.JPackage, mock.MagicMock), "jpype.JPackage should be a MagicMock."
        
        # Verify getDefaultJVMPath behavior
        assert jpype.getDefaultJVMPath() == mock_jvm_path

        # Verify logging
        assert "Activation du mock pour JPype..." in caplog.text
        assert "Le mock JPype est correctement configuré et actif." in caplog.text


    def test_jpype_mock_jvm_state_logic(self, caplog):
        """
        Tests the logic of the mocked JVM state (started/stopped).
        """
        caplog.set_level(logging.INFO)
        self.active_patches = setup_jpype_mock()
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
        self.active_patches = setup_jpype_mock()
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
        self.active_patches = setup_jpype_mock(mock_jvm_path=None)
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
        patches1 = setup_jpype_mock(mock_jvm_path=path1)
        import jpype as jpype1
        assert jpype1.getDefaultJVMPath() == path1
        jpype1.startJVM()
        assert jpype1.isJVMStarted()
        for p in patches1.values(): p.stop() # Stop first set of patches

        # Ensure jpype is removed from sys.modules so the next import gets the new mock
        if 'jpype' in sys.modules:
            del sys.modules['jpype']

        # Call 2
        path2 = "/path/num/two"
        self.active_patches = setup_jpype_mock(mock_jvm_path=path2) # self.active_patches will be stopped by teardown
        import jpype # Re-import to get the newly patched version
        
        assert jpype.getDefaultJVMPath() == path2
        assert not jpype.isJVMStarted(), "JVM state should be reset on re-mocking"
        
        # Verify logging from the second call
        log_records = [r.message for r in caplog.records if "mock_utils" in r.name] # Filter by logger name
        assert "Activation du mock pour JPype..." in log_records[-2] # Second to last relevant log
        assert f"Utilisation du chemin JVM mocké fourni : {path2}" not in caplog.text # This log is inside startJVM
        
        jpype.startJVM() # This will log the path usage
        assert f"Utilisation du chemin JVM mocké fourni : {path2}" in caplog.text


    def test_setup_jpype_mock_handles_jpype_initially_not_imported(self, caplog):
        """
        Tests that setup_jpype_mock works even if 'jpype' was not in sys.modules.
        This is implicitly covered by setup_method, but an explicit test is good.
        """
        caplog.set_level(logging.INFO)
        # setup_method ensures 'jpype' is removed from sys.modules if it existed.
        assert 'jpype' not in sys.modules

        self.active_patches = setup_jpype_mock()
        import jpype # Should now be the mocked version
        
        assert isinstance(jpype.isJVMStarted, mock.Mock)
        assert "Le mock JPype est correctement configuré et actif." in caplog.text

    def test_mock_start_jvm_logs_path_usage(self, caplog):
        """
        Tests that the mocked startJVM logs which JVM path it's (notionally) using.
        """
        caplog.set_level(logging.INFO)
        
        # Scenario 1: mock_jvm_path provided to setup_jpype_mock
        custom_path = "/my/custom/jvm"
        self.active_patches = setup_jpype_mock(mock_jvm_path=custom_path)
        import jpype
        jpype.startJVM() # Call without jvmpath argument
        assert f"Utilisation du chemin JVM mocké fourni : {custom_path}" in caplog.text
        for p in self.active_patches.values(): p.stop()
        if 'jpype' in sys.modules: del sys.modules['jpype']
        caplog.clear()

        # Scenario 2: mock_jvm_path is None (default path used)
        self.active_patches = setup_jpype_mock(mock_jvm_path=None)
        import jpype as jpype_default
        jpype_default.startJVM() # Call without jvmpath argument
        assert f"Utilisation du chemin JVM mocké par défaut : mock/jvm/path" in caplog.text
        for p in self.active_patches.values(): p.stop()
        if 'jpype' in sys.modules: del sys.modules['jpype']
        caplog.clear()

        # Scenario 3: jvmpath explicitly passed to startJVM (should take precedence)
        explicit_path = "/explicit/startjvm/path"
        self.active_patches = setup_jpype_mock(mock_jvm_path="/should/be/ignored")
        import jpype as jpype_explicit
        # The mock_start_jvm in mock_utils.py doesn't actually use the passed jvmpath for logging if it's provided.
        # It logs based on what was passed to setup_jpype_mock or the default.
        # This test verifies the current behavior of mock_utils.py.
        # If mock_utils.py were changed to log the explicit path, this test would need an update.
        jpype_explicit.startJVM(jvmpath=explicit_path)
        # The log will reflect the path from setup_jpype_mock, not the one passed to startJVM directly.
        assert f"Utilisation du chemin JVM mocké fourni : /should/be/ignored" in caplog.text
        # However, the actual mock_start_jvm in mock_utils.py has a slight logic flaw:
        # it logs, then sets jvm_started_state, then *again* checks kwargs for jvmpath and logs.
        # This means the log for path usage appears twice if jvmpath is not in kwargs.
        # Let's check the last relevant log.
        relevant_logs = [r.message for r in caplog.records if "Utilisation du chemin JVM mocké" in r.message]
        assert len(relevant_logs) > 0
        # The provided mock_utils.py has duplicate logic in mock_start_jvm (lines 79-84 and 90-95 are identical)
        # This will result in the logging happening twice if jvmpath is not in kwargs.
        # For this test, we'll assume the provided code is what we're testing.
        # The log message related to path usage will be based on setup_jpype_mock's parameter.
        assert f"Utilisation du chemin JVM mocké fourni : /should/be/ignored" in relevant_logs[-1]

        for p in self.active_patches.values(): p.stop()
        if 'jpype' in sys.modules: del sys.modules['jpype']
        caplog.clear()