import semantic_kernel
import sys

print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"semantic-kernel version: {semantic_kernel.__version__}")

try:
    from semantic_kernel.functions import kernel_function_context
    print("Successfully imported semantic_kernel.functions.kernel_function_context")
    if hasattr(kernel_function_context, 'KernelFunctionInvokingEventArgs'):
        print("KernelFunctionInvokingEventArgs found in kernel_function_context.")
    else:
        print("KernelFunctionInvokingEventArgs NOT found in kernel_function_context.")
    print("Dir of kernel_function_context:", dir(kernel_function_context))

except ImportError as e:
    print(f"Failed to import semantic_kernel.functions.kernel_function_context: {e}")

except Exception as e_gen:
    print(f"An unexpected error occurred: {e_gen}")

print("\nAttempting to import KernelFunctionInvokingEventArgs directly from kernel_function_context:")
try:
    from semantic_kernel.functions.kernel_function_context import KernelFunctionInvokingEventArgs
    print("Successfully imported KernelFunctionInvokingEventArgs from kernel_function_context.")
except ImportError as e2:
    print(f"Failed to import KernelFunctionInvokingEventArgs from kernel_function_context: {e2}")
except Exception as e_gen2:
    print(f"An unexpected error occurred during direct import: {e_gen2}")

print("\nChecking sys.path:")
for p in sys.path:
    print(p)