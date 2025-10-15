import argumentation_analysis.core.environment
import sys

print(f"Python version: {sys.version}")
print(f"sys.path: {sys.path}")

try:
    print("Attempting to import jpype...")
    import jpype

    print(
        f"Successfully imported jpype. Version: {getattr(jpype, '__version__', 'N/A')}"
    )
    print(f"jpype module path: {getattr(jpype, '__file__', 'N/A')}")

    if hasattr(jpype, "_core"):
        print(f"jpype._core path: {getattr(jpype._core, '__file__', 'N/A')}")
    elif hasattr(jpype, "_jpype"):
        print(f"jpype._jpype path: {getattr(jpype._jpype, '__file__', 'N/A')}")
    else:
        print("jpype._core or jpype._jpype not found directly.")

    # Try to access something that might use _jinit implicitly
    try:
        print("Attempting to call jpype.isJVMStarted()...")
        print(f"jpype.isJVMStarted(): {jpype.isJVMStarted()}")
    except Exception as e_jvm_call:
        print(f"Error calling jpype.isJVMStarted(): {e_jvm_call}")

except ImportError as e_import:
    print(f"ImportError when importing jpype: {e_import}")
    import traceback

    traceback.print_exc()
except NameError as e_name:
    print(f"NameError during jpype import or usage: {e_name}")
    import traceback

    traceback.print_exc()
except Exception as e_general:
    print(f"An unexpected error occurred: {e_general}")
    import traceback

    traceback.print_exc()
