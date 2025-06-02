import pytest
from unittest import mock

# Import the function to test
from project_core.dev_utils.mock_utils import setup_jpype_mock

# Attempt to import jpype, but allow it to be None if not installed,
# as the function under test should mock it anyway.
try:
    import jpype
    import jpype.imports # if your setup_jpype_mock also mocks things in jpype.imports
except ImportError:
    jpype = None # Will be mocked by setup_jpype_mock or tests will mock it


def test_setup_jpype_mock_replaces_jpype_attributes():
    """
    Tests that setup_jpype_mock correctly replaces jpype's attributes
    with MagicMock objects.
    """
    # Define a mock JVM path to be returned by the mocked getDefaultJVMPath
    mock_jvm_path = "/mock/jvm/path"

    # Call the setup function
    # It's important that this function can run even if jpype is not installed,
    # as it's supposed to set up a mock *for* jpype.
    # The function itself should handle the case where 'jpype' module is not found
    # by creating a mock for it.
    
    # If jpype is truly unavailable, sys.modules['jpype'] might not exist.
    # setup_jpype_mock should ideally create it if it's not there.
    
    # Scenario 1: jpype is not installed (or we simulate it)
    # We want to ensure that after calling setup_jpype_mock, 'jpype' in sys.modules IS a mock.
    
    # To robustly test this, we might need to control sys.modules
    original_sys_modules_jpype = mock.sentinel.original_jpype
    if 'jpype' in mock.sys.modules:
        original_sys_modules_jpype = mock.sys.modules.get('jpype')
        del mock.sys.modules['jpype'] # Simulate jpype not being imported yet or not installed

    # Call the function that should set up the mock
    jpype_mock_instance = setup_jpype_mock(mock_jvm_path=mock_jvm_path)

    # Assert that the returned object is a MagicMock (or the type setup_jpype_mock creates)
    assert isinstance(jpype_mock_instance, mock.MagicMock), "setup_jpype_mock should return a MagicMock instance."

    # Verify that the attributes of the returned mock are also mocks and configured
    assert isinstance(jpype_mock_instance.startJVM, mock.MagicMock)
    assert isinstance(jpype_mock_instance.shutdownJVM, mock.MagicMock)
    assert isinstance(jpype_mock_instance.isJVMStarted, mock.MagicMock)
    assert isinstance(jpype_mock_instance.getDefaultJVMPath, mock.MagicMock)
    assert isinstance(jpype_mock_instance.JPackage, mock.MagicMock)
    assert isinstance(jpype_mock_instance.JClass, mock.MagicMock)
    # If jpype.imports is also mocked:
    if hasattr(jpype_mock_instance, 'imports'):
        assert isinstance(jpype_mock_instance.imports, mock.MagicMock)


    # Test the configured behavior of the mocked attributes
    jpype_mock_instance.isJVMStarted.return_value = True # Example configuration
    assert jpype_mock_instance.isJVMStarted() is True

    # getDefaultJVMPath should return the mock_jvm_path provided
    assert jpype_mock_instance.getDefaultJVMPath() == mock_jvm_path
    
    # JPackage should be callable and return another mock
    mock_pkg = jpype_mock_instance.JPackage("com.example")
    assert isinstance(mock_pkg, mock.MagicMock)
    
    # JClass should be callable and return another mock
    mock_class = jpype_mock_instance.JClass("com.example.MyClass")
    assert isinstance(mock_class, mock.MagicMock)

    # Restore original jpype in sys.modules if it was there
    if original_sys_modules_jpype is not mock.sentinel.original_jpype:
        mock.sys.modules['jpype'] = original_sys_modules_jpype
    elif 'jpype' in mock.sys.modules and mock.sys.modules['jpype'] is jpype_mock_instance:
        # If setup_jpype_mock added it, clean it up for other tests if necessary
        del mock.sys.modules['jpype']


def test_setup_jpype_mock_is_idempotent_or_consistent():
    """
    Tests that calling setup_jpype_mock multiple times behaves consistently.
    If it's idempotent, the same mock or an identically configured one is returned/set.
    """
    mock_jvm_path1 = "/path/one"
    mock_jvm_path2 = "/path/two"

    # Call 1
    jpype_mock1 = setup_jpype_mock(mock_jvm_path=mock_jvm_path1)
    assert jpype_mock1.getDefaultJVMPath() == mock_jvm_path1
    assert isinstance(jpype_mock1.isJVMStarted, mock.MagicMock)
    
    # Store the original isJVMStarted mock object from the first call
    original_isJVMStarted_mock_obj = jpype_mock1.isJVMStarted

    # Call 2 - with a different path
    # The behavior here depends on the implementation of setup_jpype_mock.
    # Does it overwrite the existing mock in sys.modules or return a new one?
    # The current implementation in the prompt seems to always create a new mock
    # and assign it to sys.modules['jpype'].
    jpype_mock2 = setup_jpype_mock(mock_jvm_path=mock_jvm_path2)
    
    assert jpype_mock2.getDefaultJVMPath() == mock_jvm_path2
    assert isinstance(jpype_mock2.isJVMStarted, mock.MagicMock)

    # Check if the mock instance in sys.modules is indeed the latest one
    # This requires setup_jpype_mock to actually place its mock into sys.modules['jpype']
    if 'jpype' in mock.sys.modules:
        assert mock.sys.modules['jpype'] is jpype_mock2, "sys.modules['jpype'] should be the latest mock."
        assert mock.sys.modules['jpype'].getDefaultJVMPath() == mock_jvm_path2

    # Verify that the mocks are distinct if new ones are created each time,
    # or the same if it's truly idempotent by object reference.
    # Given the typical MagicMock usage, they'd likely be different objects but
    # the one in sys.modules would be the latest.
    assert jpype_mock1 is not jpype_mock2, "Multiple calls should ideally update or return distinct mocks if re-patching."
    
    # However, the attributes like isJVMStarted might be new mock objects too.
    assert original_isJVMStarted_mock_obj is not jpype_mock2.isJVMStarted, \
        "Attribute mocks should also be new if the parent mock is new."

    # Clean up sys.modules for other tests
    if 'jpype' in mock.sys.modules:
        del mock.sys.modules['jpype']

# It might be useful to test with jpype actually installed vs not installed
# to see how setup_jpype_mock behaves, but that's harder to control in unit tests
# without more complex fixture setups for sys.modules.