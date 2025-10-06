import sys
import pytest

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_tests_from_file.py <test_list_file>")
        sys.exit(1)

    test_list_file = sys.argv[1]
    with open(test_list_file, 'r') as f:
        test_items = [line.strip() for line in f if line.strip()]

    print(f"Running {len(test_items)} tests from {test_list_file}...")
    
    # On passe les tests comme arguments à pytest
    # j'ajoute --capture=no pour voir la sortie en temps réel et -vv pour verbosité
    exit_code = pytest.main(["-vv", "--capture=no"] + test_items)
    
    sys.exit(exit_code)