import sys
import semantic_kernel

print(f"--- Semantic Kernel Diagnostic Script ---")
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")

try:
    print(f"semantic-kernel version: {semantic_kernel.__version__}")
    print(f"semantic-kernel path: {semantic_kernel.__path__}")

    # In modern semantic-kernel (>= 1.0), event args are in `semantic_kernel.events`.
    # Let's verify we can import them.
    from semantic_kernel.events import FunctionInvokingEventArgs
    print("\nSUCCESS: `semantic_kernel` basic import is working.")
    print("SUCCESS: `FunctionInvokingEventArgs` successfully imported from `semantic_kernel.events`.")
    print("Environment appears to be correctly configured for semantic-kernel v1.x.")

except AttributeError:
    print("\nERROR: Could not get `semantic_kernel.__version__`.")
    print("This often indicates a PYTHONPATH issue, where a local folder named 'semantic_kernel' is shadowing the installed package.")
    print("Please check your project structure and ensure no such local folder exists.")

except ImportError as e:
    print(f"\nERROR: An ImportError occurred: {e}")
    print("This might mean the `semantic-kernel` package is not correctly installed or there is a version mismatch.")
    print("Please ensure you have run 'pip install --upgrade semantic-kernel'.")

except Exception as e:
    print(f"\nERROR: An unexpected error occurred: {e}")

print("\n--- sys.path details ---")
for p in sys.path:
    print(p)
print("--------------------------")