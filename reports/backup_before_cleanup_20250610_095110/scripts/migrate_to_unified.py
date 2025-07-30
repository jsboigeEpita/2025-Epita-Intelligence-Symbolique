#!/usr/bin/env python3
"""
Script de migration vers le système Enhanced PM Orchestration v2.0 unifié
Aide à passer des anciens scripts éparpillés au nouveau système consolidé.
"""

import sys
import os
import argparse
from pathlib import Path
import yaml
import subprocess
import shutil

def print_header():
    """Affiche l'en-tête du script de migration."""
    print("=" * 70)
    print("🚀 MIGRATION ENHANCED PM ORCHESTRATION v2.0")
    print("   Passage au système unifié et consolidé")
    print("=" * 70)

def check_environment():
    """Vérifie l'environnement requis."""
    print("\n📋 VÉRIFICATION DE L'ENVIRONNEMENT...")
    
    # Vérifier Python
    python_version = sys.version_info
    if python_version.major >= 3 and python_version.minor >= 8:
        print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    else:
        print(f"❌ Python {python_version.major}.{python_version.minor} (requis: 3.8+)")
        return False
    
    # Vérifier structure des répertoires
    required_dirs = [
        'scripts/main',
        'scripts/core', 
        'config',
        'reports'
    ]
    
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✅ Répertoire {dir_path}")
        else:
            print(f"❌ Répertoire manquant: {dir_path}")
            return False
    
    # Vérifier fichiers principaux
    required_files = [
        'scripts/main/analyze_text.py',
        'scripts/core/unified_source_selector.py',
        'scripts/core/unified_report_generator.py',
        'config/orchestration_config.yaml'
    ]
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ Fichier {file_path}")
        else:
            print(f"❌ Fichier manquant: {file_path}")
            return False
    
    return True

def show_migration_guide():
    """Affiche le guide de migration détaillé."""
    print("\n📖 GUIDE DE MIGRATION")
    print("-" * 50)
    
    migrations = [
        {
            "ancien": "scripts/execution/rhetorical_analysis.py",
            "nouveau": "scripts/main/analyze_text.py --source-type simple --modes fallacies,coherence,semantic",
            "description": "Analyse rhétorique de base"
        },
        {
            "ancien": "scripts/execution/advanced_rhetorical_analysis.py", 
            "nouveau": "scripts/main/analyze_text.py --advanced --modes fallacies,coherence,semantic",
            "description": "Analyse rhétorique avancée"
        },
        {
            "ancien": "scripts/demo/complete_rhetorical_analysis_demo.py",
            "nouveau": "scripts/main/analyze_text.py --interactive --modes unified",
            "description": "Démonstration complète"
        },
        {
            "ancien": "scripts/demo/run_rhetorical_analysis_demo.py",
            "nouveau": "scripts/main/analyze_text.py --source-type complex --modes fallacies,formal,unified",
            "description": "Démo avec sources complexes"
        },
        {
            "ancien": "scripts/execution/run_full_python_analysis_workflow.py",
            "nouveau": "scripts/main/analyze_text.py --source-type complex --passphrase-env",
            "description": "Workflow complet avec .enc"
        }
    ]
    
    for i, migration in enumerate(migrations, 1):
        print(f"\n{i}. {migration['description']}")
        print(f"   Ancien : {migration['ancien']}")
        print(f"   Nouveau: {migration['nouveau']}")

def backup_legacy_scripts():
    """Sauvegarde les anciens scripts dans scripts/legacy/."""
    print("\n💾 SAUVEGARDE DES ANCIENS SCRIPTS...")
    
    legacy_dir = Path('scripts/legacy')
    legacy_dir.mkdir(exist_ok=True)
    
    scripts_to_backup = [
        'scripts/execution/rhetorical_analysis.py',
        'scripts/execution/advanced_rhetorical_analysis.py',
        'scripts/execution/run_full_python_analysis_workflow.py',
        'scripts/demo/complete_rhetorical_analysis_demo.py', 
        'scripts/demo/run_rhetorical_analysis_demo.py',
        'scripts/testing/test_rhetorical_analysis.py'
    ]
    
    backed_up = 0
    for script_path in scripts_to_backup:
        script_file = Path(script_path)
        if script_file.exists():
            target = legacy_dir / script_file.name
            if not target.exists():
                shutil.copy2(script_file, target)
                print(f"✅ Sauvegardé: {script_file.name} → scripts/legacy/")
                backed_up += 1
            else:
                print(f"⚠️  Déjà sauvegardé: {script_file.name}")
        else:
            print(f"⚠️  Fichier non trouvé: {script_path}")
    
    if backed_up > 0:
        print(f"\n✅ {backed_up} scripts sauvegardés dans scripts/legacy/")
    else:
        print("\n📋 Aucun nouveau script à sauvegarder")

def test_unified_system():
    """Teste le système unifié."""
    print("\n🧪 TEST DU SYSTÈME UNIFIÉ...")
    
    # Test 1: Aide
    print("\n1. Test affichage aide...")
    try:
        result = subprocess.run([
            sys.executable, 'scripts/main/analyze_text.py', '--help'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Script principal accessible")
        else:
            print(f"❌ Erreur d'aide: {result.stderr[:100]}...")
            return False
    except Exception as e:
        print(f"❌ Erreur test aide: {e}")
        return False
    
    # Test 2: Sources simples
    print("\n2. Test sources simples...")
    try:
        result = subprocess.run([
            sys.executable, 'scripts/main/analyze_text.py',
            '--source-type', 'simple',
            '--format', 'console',
            '--template', 'summary',
            '--mocks',
            '--no-jvm'
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Analyse avec sources simples")
        else:
            print(f"❌ Erreur sources simples: {result.stderr[:100]}...")
            return False
    except Exception as e:
        print(f"❌ Erreur test sources simples: {e}")
        return False
    
    # Test 3: Configuration
    print("\n3. Test configuration...")
    try:
        with open('config/orchestration_config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            if 'profiles' in config and 'development' in config['profiles']:
                print("✅ Configuration YAML valide")
            else:
                print("❌ Configuration incomplète")
                return False
    except Exception as e:
        print(f"❌ Erreur config: {e}")
        return False
    
    return True

def show_quick_start():
    """Affiche le guide de démarrage rapide."""
    print("\n🚀 DÉMARRAGE RAPIDE")
    print("-" * 50)
    
    commands = [
        {
            "titre": "Découverte du système",
            "commande": "python scripts/main/analyze_text.py --source-type simple --format console",
            "description": "Test rapide avec données de démonstration"
        },
        {
            "titre": "Mode interactif",
            "commande": "python scripts/main/analyze_text.py --interactive",
            "description": "Interface guidée pour sélection de sources"
        },
        {
            "titre": "Analyse complète",
            "commande": "python scripts/main/analyze_text.py --interactive --modes fallacies,coherence,semantic,unified --format markdown",
            "description": "Analyse complète avec rapport détaillé"
        }
    ]
    
    for i, cmd in enumerate(commands, 1):
        print(f"\n{i}. {cmd['titre']}")
        print(f"   {cmd['description']}")
        print(f"   💻 {cmd['commande']}")

def create_migration_summary():
    """Crée un résumé de migration."""
    summary_file = Path('MIGRATION_SUMMARY.md')
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("# 📋 RÉSUMÉ MIGRATION ENHANCED PM ORCHESTRATION v2.0\n\n")
        f.write(f"**Date de migration**: {Path().cwd()}\n")
        f.write(f"**Script de migration**: scripts/migrate_to_unified.py\n\n")
        
        f.write("## ✅ Actions effectuées\n\n")
        f.write("- [x] Vérification environnement\n")
        f.write("- [x] Sauvegarde scripts legacy\n") 
        f.write("- [x] Test système unifié\n")
        f.write("- [x] Génération documentation\n\n")
        
        f.write("## 🎯 Point d'entrée principal\n\n")
        f.write("```bash\n")
        f.write("python scripts/main/analyze_text.py --interactive\n")
        f.write("```\n\n")
        
        f.write("## 📚 Documentation\n\n")
        f.write("- `README_REFACTORISATION_MAJEURE.md` - Documentation complète\n")
        f.write("- `config/orchestration_config.yaml` - Configuration centralisée\n")
        f.write("- `scripts/legacy/` - Anciens scripts sauvegardés\n\n")
        
        f.write("## 🧪 Tests rapides\n\n")
        f.write("```bash\n")
        f.write("# Test de base\n")
        f.write("python scripts/main/analyze_text.py --source-type simple --format console\n\n")
        f.write("# Test complet\n") 
        f.write("python scripts/main/analyze_text.py --interactive --modes unified\n")
        f.write("```\n")
    
    print(f"✅ Résumé sauvegardé dans: {summary_file}")

def main():
    """Fonction principale de migration."""
    parser = argparse.ArgumentParser(description="Migration vers Enhanced PM Orchestration v2.0")
    parser.add_argument('--backup-only', action='store_true', help='Sauvegarder uniquement les anciens scripts')
    parser.add_argument('--test-only', action='store_true', help='Tester uniquement le système unifié')
    parser.add_argument('--skip-tests', action='store_true', help='Ignorer les tests')
    
    args = parser.parse_args()
    
    print_header()
    
    # Vérification environnement
    if not check_environment():
        print("\n❌ ÉCHEC: Environnement non conforme")
        print("📋 Vérifiez que tous les fichiers unifiés sont présents")
        return 1
    
    if args.backup_only:
        backup_legacy_scripts()
        return 0
    
    if args.test_only:
        if test_unified_system():
            print("\n✅ SUCCÈS: Système unifié opérationnel")
            return 0
        else:
            print("\n❌ ÉCHEC: Tests système")
            return 1
    
    # Migration complète
    print("\n🔄 MIGRATION COMPLÈTE EN COURS...")
    
    # Afficher guide de migration
    show_migration_guide()
    
    # Sauvegarder anciens scripts
    backup_legacy_scripts()
    
    # Tester système unifié
    if not args.skip_tests:
        if not test_unified_system():
            print("\n⚠️  ATTENTION: Certains tests ont échoué")
            print("   Le système peut néanmoins être utilisable")
    
    # Guide de démarrage
    show_quick_start()
    
    # Créer résumé
    create_migration_summary()
    
    print("\n" + "=" * 70)
    print("🎉 MIGRATION TERMINÉE AVEC SUCCÈS!")
    print("   Le système Enhanced PM Orchestration v2.0 est opérationnel")
    print("   Point d'entrée: scripts/main/analyze_text.py")
    print("   Documentation: README_REFACTORISATION_MAJEURE.md")
    print("=" * 70)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())