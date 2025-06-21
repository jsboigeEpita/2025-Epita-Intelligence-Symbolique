#!/usr/bin/env python3
"""Script pour vérifier les dépendances de jvm.dll"""

import argumentation_analysis.core.environment
import subprocess
import sys
from pathlib import Path

def check_visual_cpp_redist():
    """Vérifier les redistribuables Visual C++ installés"""
    print("=== VISUAL C++ REDISTRIBUTABLES ===")
    
    try:
        # Utiliser PowerShell pour lister les programmes installés
        cmd = '''Get-WmiObject -Class Win32_Product | Where-Object {$_.Name -like "*Visual C++*"} | Select-Object Name, Version'''
        result = subprocess.run(['powershell', '-Command', cmd], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("Redistribuables Visual C++ trouvés :")
            print(result.stdout)
        else:
            print("Erreur lors de la recherche des redistribuables Visual C++")
            print(result.stderr)
            
    except Exception as e:
        print(f"Erreur lors de la vérification Visual C++: {e}")

def check_dll_dependencies():
    """Vérifier les dépendances de jvm.dll avec dumpbin si disponible"""
    print("\n=== DEPENDANCES DLL ===")
    
    project_root = Path(__file__).resolve().parent
    jvm_dll = project_root / "libs/portable_jdk/jdk-17.0.11+9/bin/server/jvm.dll"
    
    # Tenter d'utiliser dumpbin si Visual Studio est installé
    try:
        result = subprocess.run(['dumpbin', '/DEPENDENTS', str(jvm_dll)], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("Dépendances de jvm.dll (via dumpbin) :")
            print(result.stdout)
        else:
            print("dumpbin non disponible ou erreur")
    except FileNotFoundError:
        print("dumpbin non trouvé (Visual Studio non installé)")
    except Exception as e:
        print(f"Erreur avec dumpbin: {e}")

def check_required_dlls():
    """Vérifier si les DLLs couramment requises sont présentes"""
    print("\n=== VERIFICATION DLLS REQUISES ===")
    
    project_root = Path(__file__).resolve().parent
    jdk_bin = project_root / "libs/portable_jdk/jdk-17.0.11+9/bin"
    
    # DLLs typiquement requises par JVM
    required_dlls = [
        "msvcr120.dll",   # Visual C++ 2013
        "msvcp120.dll",   # Visual C++ 2013
        "msvcr140.dll",   # Visual C++ 2015+
        "msvcp140.dll",   # Visual C++ 2015+
        "vcruntime140.dll", # Present dans le listing
        "vcruntime140_1.dll",
        "ucrtbase.dll",   # Present dans le listing
    ]
    
    print("Vérification des DLLs dans le répertoire JDK bin :")
    for dll in required_dlls:
        dll_path = jdk_bin / dll
        exists = dll_path.exists()
        print(f"  {dll}: {'PRESENT' if exists else 'ABSENT'}")

def test_simple_java_execution():
    """Test d'exécution Java simple avec différentes options"""
    print("\n=== TEST EXECUTION JAVA ===")
    
    project_root = Path(__file__).resolve().parent
    java_exe = project_root / "libs/portable_jdk/jdk-17.0.11+9/bin/java.exe"
    
    # Test avec option minimal
    print("Test 1: java -help")
    try:
        result = subprocess.run([str(java_exe), "-help"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("SUCCESS: java -help fonctionne")
            print("Première ligne de sortie:", result.stdout.split('\n')[0])
        else:
            print("ECHEC: java -help")
            print("STDERR:", result.stderr)
    except Exception as e:
        print(f"ERREUR java -help: {e}")
    
    # Test sans JVM server
    print("\nTest 2: java -client -version (si client JVM disponible)")
    try:
        result = subprocess.run([str(java_exe), "-client", "-version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("SUCCESS: java -client -version fonctionne")
            print(result.stderr)  # -version output va sur stderr
        else:
            print("ECHEC: java -client -version")
            print("STDERR:", result.stderr)
    except Exception as e:
        print(f"ERREUR java -client: {e}")

def main():
    """Fonction principale"""
    check_visual_cpp_redist()
    check_dll_dependencies()
    check_required_dlls()
    test_simple_java_execution()

if __name__ == "__main__":
    main()