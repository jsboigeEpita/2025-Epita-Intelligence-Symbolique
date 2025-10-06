import subprocess
import pytest

def get_all_tests():
    """Collects all tests using pytest."""
    # Capture output as bytes to handle potential encoding errors
    result = subprocess.run(
        ["pytest", "--collect-only", "-q", "tests/unit"],
        capture_output=True
    )
    tests = []
    # Decode stdout manually, ignoring errors
    stdout_str = result.stdout.decode('utf-8', errors='ignore')
    for line in stdout_str.splitlines():
        if '::' in line and '.py' in line and not line.startswith('===') and 'warning' not in line.lower():
            tests.append(line.strip())
    return tests

def filter_tests(tests, keywords):
    """Filters a list of tests based on keywords."""
    return [test for test in tests if not any(keyword in test for keyword in keywords)]

if __name__ == "__main__":
    all_tests = get_all_tests()
    
    # Keywords to identify JVM-related tests
    jvm_keywords = ["jvm", "fol", "tweety", "jpype", "conftest"]
    
    filtered_tests = filter_tests(all_tests, jvm_keywords)
    
    print(f"Running {len(filtered_tests)} tests out of {len(all_tests)} total.")
    
    # Execute the filtered tests
    exit_code = pytest.main(["-vv", "--capture=no"] + filtered_tests)
    
    # Forward the exit code
    exit(exit_code)