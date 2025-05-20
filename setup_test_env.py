#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour configurer un environnement de test propre pour le projet argumentation_analysis.
Ce script résout les problèmes d'environnement identifiés lors de l'exécution des tests.
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def print_step(message):
    """Affiche un message d'étape avec une mise en forme."""
    print("\n" + "=" * 80)
    print(f"  {message}")
    print("=" * 80)

def run_command(command, cwd=None):
    """Exécute une commande shell et affiche sa sortie."""
    print(f"> {command}")
    result = subprocess.run(command, shell=True, cwd=cwd, 
                           capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    
    if result.stderr:
        print(f"ERREUR: {result.stderr}")
    
    return result.returncode == 0

def main():
    """Fonction principale pour configurer l'environnement de test."""
    print_step("Vérification du système")
    
    # Déterminer le système d'exploitation
    system = platform.system()
    print(f"Système d'exploitation détecté: {system}")
    
    # Déterminer le chemin du projet
    project_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    print(f"Répertoire du projet: {project_dir}")
    
    # Vérifier si un environnement virtuel existe déjà
    venv_dir = project_dir / "venv_test"
    if venv_dir.exists():
        print_step("Suppression de l'ancien environnement virtuel")
        shutil.rmtree(venv_dir)
    
    # Créer un nouvel environnement virtuel
    print_step("Création d'un nouvel environnement virtuel")
    venv_command = "python -m venv venv_test"
    if not run_command(venv_command):
        print("Échec de la création de l'environnement virtuel.")
        return False
    
    # Déterminer la commande d'activation
    if system == "Windows":
        activate_cmd = str(venv_dir / "Scripts" / "activate")
        pip_cmd = str(venv_dir / "Scripts" / "pip")
    else:
        activate_cmd = f"source {venv_dir}/bin/activate"
        pip_cmd = str(venv_dir / "bin" / "pip")
    
    # Mettre à jour pip
    print_step("Mise à jour de pip")
    if system == "Windows":
        upgrade_pip_cmd = f"{pip_cmd} install --upgrade pip"
    else:
        upgrade_pip_cmd = f"{activate_cmd} && pip install --upgrade pip"
    
    if not run_command(upgrade_pip_cmd):
        print("Échec de la mise à jour de pip.")
        return False
    
    # Installer les dépendances de test
    print_step("Installation des dépendances de test")
    requirements_file = project_dir / "requirements-test.txt"
    
    if system == "Windows":
        install_cmd = f"{pip_cmd} install -r {requirements_file}"
    else:
        install_cmd = f"{activate_cmd} && pip install -r {requirements_file}"
    
    if not run_command(install_cmd):
        print("Échec de l'installation des dépendances de test.")
        return False
    
    # Installer le package en mode développement
    print_step("Installation du package en mode développement")
    if system == "Windows":
        dev_install_cmd = f"{pip_cmd} install -e ."
    else:
        dev_install_cmd = f"{activate_cmd} && pip install -e ."
    
    if not run_command(dev_install_cmd):
        print("Échec de l'installation du package en mode développement.")
        return False
    
    # Vérifier les importations problématiques
    print_step("Vérification des importations problématiques")
    
    # Vérifier numpy
    if system == "Windows":
        check_numpy_cmd = f"{venv_dir}\\Scripts\\python -c \"import numpy; print('Numpy importé avec succès:', numpy.__version__)\""
    else:
        check_numpy_cmd = f"{activate_cmd} && python -c \"import numpy; print('Numpy importé avec succès:', numpy.__version__)\""
    
    run_command(check_numpy_cmd)
    
    # Vérifier jpype
    if system == "Windows":
        check_jpype_cmd = f"{venv_dir}\\Scripts\\python -c \"import jpype; print('JPype importé avec succès:', jpype.__version__)\""
    else:
        check_jpype_cmd = f"{activate_cmd} && python -c \"import jpype; print('JPype importé avec succès:', jpype.__version__)\""
    
    run_command(check_jpype_cmd)
    
    # Vérifier cffi
    if system == "Windows":
        check_cffi_cmd = f"{venv_dir}\\Scripts\\python -c \"import cffi; print('CFFI importé avec succès:', cffi.__version__)\""
    else:
        check_cffi_cmd = f"{activate_cmd} && python -c \"import cffi; print('CFFI importé avec succès:', cffi.__version__)\""
    
    run_command(check_cffi_cmd)
    
    # Vérifier cryptography
    if system == "Windows":
        check_crypto_cmd = f"{venv_dir}\\Scripts\\python -c \"import cryptography; print('Cryptography importé avec succès:', cryptography.__version__)\""
    else:
        check_crypto_cmd = f"{activate_cmd} && python -c \"import cryptography; print('Cryptography importé avec succès:', cryptography.__version__)\""
    
    run_command(check_crypto_cmd)
    
    # Exécuter un test simple pour vérifier l'environnement
    print_step("Exécution d'un test simple pour vérifier l'environnement")
    test_file = "argumentation_analysis/tests/test_async_communication_fixed.py"
    
    if system == "Windows":
        test_cmd = f"{venv_dir}\\Scripts\\python -m unittest {test_file}"
    else:
        test_cmd = f"{activate_cmd} && python -m unittest {test_file}"
    
    success = run_command(test_cmd)
    
    if success:
        print_step("Configuration de l'environnement de test terminée avec succès")
        print("\nPour activer l'environnement de test:")
        if system == "Windows":
            print(f"    {venv_dir}\\Scripts\\activate")
        else:
            print(f"    source {venv_dir}/bin/activate")
        
        print("\nPour exécuter les tests:")
        if system == "Windows":
            print(f"    {venv_dir}\\Scripts\\python -m unittest discover -s argumentation_analysis/tests -p \"test_*.py\" -v")
        else:
            print(f"    python -m unittest discover -s argumentation_analysis/tests -p \"test_*.py\" -v")
    else:
        print_step("Des problèmes subsistent dans l'environnement de test")
    
    return success

if __name__ == "__main__":
    main()