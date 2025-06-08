<<<<<<< MAIN
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ORCHESTRATION CONVERSATIONNELLE UNIFIÉE
=======================================

Script d'interface CLI pour orchestration conversationnelle refactorisée.
Délègue la logique métier au composant réutilisable ConversationOrchestrator.

Modes disponibles :
- micro : Orchestration ultra-légère (<1000 lignes)
- demo : Démonstration complète avec tous les agents
- trace : Test du système de traçage conversationnel
- enhanced : Test des composants PM améliorés
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Ajout du chemin du projet pour les imports
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration de l'encodage pour éviter les problèmes Unicode
import io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("OrchestrationUnified")

# Import du composant refactorisé
try:
    from argumentation_analysis.orchestration.conversation_orchestrator import (
        run_mode_micro, 
        run_mode_demo, 
        run_mode_trace, 
        run_mode_enhanced
    )
except ImportError as e:
    logger.error(f"Erreur import du composant orchestrateur: {e}")
    logger.info("Utilisation du mode de fallback...")
    
    # Mode de fallback simple
    def run_mode_micro(text: str) -> str:
        return f"Mode micro (fallback): Analyse de '{text[:50]}...'"
    
    def run_mode_demo(text: str) -> str:
        return f"Mode demo (fallback): Analyse de '{text[:50]}...'"
    
    def run_mode_trace(text: str) -> str:
        return f"Mode trace (fallback): Analyse de '{text[:50]}...'"
    
    def run_mode_enhanced(text: str) -> str:
        return f"Mode enhanced (fallback): Analyse de '{text[:50]}...'"


def main():
    """Point d'entrée principal - Interface CLI préservée."""
    parser = argparse.ArgumentParser(
        description="Orchestration conversationnelle unifiée - Version refactorisée"
    )
    parser.add_argument(
        "--mode",
        choices=["micro", "demo", "trace", "enhanced"],
        default="demo",
        help="Mode d'orchestration"
    )
    parser.add_argument(
        "--text",
        default="L'Ukraine a été créée par la Russie. Donc Poutine a raison. Tout le monde le sait.",
        help="Texte à analyser"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Sauvegarder le rapport"
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=1,
        help="Nombre de tours d'analyse (compatibilité)"
    )
    
    args = parser.parse_args()
    
    print(f"ORCHESTRATION CONVERSATIONNELLE UNIFIÉE - Mode {args.mode.upper()}")
    print("=" * 70)
    logger.info(f"Démarrage mode {args.mode} pour texte de {len(args.text)} caractères")
    
    # Sélection du mode via le composant refactorisé
    mode_functions = {
        "micro": run_mode_micro,
        "demo": run_mode_demo,
        "trace": run_mode_trace,
        "enhanced": run_mode_enhanced
    }
    
    try:
        # Exécution via le composant refactorisé
        print(f"=== MODE {args.mode.upper()} : {'Orchestration ultra-légère' if args.mode == 'micro' else 'Démonstration complète' if args.mode == 'demo' else 'Test du système de traçage' if args.mode == 'trace' else 'Test composants PM améliorés'} ===")
        
        report = mode_functions[args.mode](args.text)
        
        # Affichage du rapport
        print("\n" + "=" * 70)
        print("RAPPORT GÉNÉRE:")
        print("=" * 70)
        print(report)
        
        # Sauvegarde optionnelle
        if args.save:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"orchestration_conversationnelle_{args.mode}_{timestamp}.md"
            report_path = LOGS_DIR / filename
            
            try:
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"\n[SUCCESS] Rapport sauvegardé: {report_path}")
                logger.info(f"Rapport sauvegardé: {report_path}")
            except Exception as e:
                print(f"\n[ERROR] Erreur sauvegarde: {e}")
                logger.error(f"Erreur sauvegarde: {e}")
        
        print(f"\n[INFO] Mode {args.mode} exécuté avec succès")
        logger.info(f"Orchestration {args.mode} terminée avec succès")
        
        return report
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du mode {args.mode}: {e}")
        print(f"\n[ERROR] Erreur lors de l'exécution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

=======
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ORCHESTRATION CONVERSATIONNELLE UNIFIÉE
=======================================

Script d'interface CLI pour orchestration conversationnelle refactorisée.
Délègue la logique métier au composant réutilisable ConversationOrchestrator.

Modes disponibles :
- micro : Orchestration ultra-légère (<1000 lignes)
- demo : Démonstration complète avec tous les agents
- trace : Test du système de traçage conversationnel
- enhanced : Test des composants PM améliorés
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Ajout du chemin du projet pour les imports
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration de l'encodage pour éviter les problèmes Unicode
import io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("OrchestrationUnified")

# Import du composant refactorisé
try:
    from argumentation_analysis.orchestration.conversation_orchestrator import (
        run_mode_micro, 
        run_mode_demo, 
        run_mode_trace, 
        run_mode_enhanced
    )
except ImportError as e:
    logger.error(f"Erreur import du composant orchestrateur: {e}")
    logger.info("Utilisation du mode de fallback...")
    
    # Mode de fallback simple
    def run_mode_micro(text: str) -> str:
        return f"Mode micro (fallback): Analyse de '{text[:50]}...'"
    
    def run_mode_demo(text: str) -> str:
        return f"Mode demo (fallback): Analyse de '{text[:50]}...'"
    
    def run_mode_trace(text: str) -> str:
        return f"Mode trace (fallback): Analyse de '{text[:50]}...'"
    
    def run_mode_enhanced(text: str) -> str:
        return f"Mode enhanced (fallback): Analyse de '{text[:50]}...'"


def main():
    """Point d'entrée principal - Interface CLI préservée."""
    parser = argparse.ArgumentParser(
        description="Orchestration conversationnelle unifiée - Version refactorisée"
    )
    parser.add_argument(
        "--mode",
        choices=["micro", "demo", "trace", "enhanced"],
        default="demo",
        help="Mode d'orchestration"
    )
    parser.add_argument(
        "--text",
        default="L'Ukraine a été créée par la Russie. Donc Poutine a raison. Tout le monde le sait.",
        help="Texte à analyser"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Sauvegarder le rapport"
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=1,
        help="Nombre de tours d'analyse (compatibilité)"
    )
    
    args = parser.parse_args()
    
    print(f"ORCHESTRATION CONVERSATIONNELLE UNIFIÉE - Mode {args.mode.upper()}")
    print("=" * 70)
    logger.info(f"Démarrage mode {args.mode} pour texte de {len(args.text)} caractères")
    
    # Sélection du mode via le composant refactorisé
    mode_functions = {
        "micro": run_mode_micro,
        "demo": run_mode_demo,
        "trace": run_mode_trace,
        "enhanced": run_mode_enhanced
    }
    
    try:
        # Exécution via le composant refactorisé
        print(f"=== MODE {args.mode.upper()} : {'Orchestration ultra-légère' if args.mode == 'micro' else 'Démonstration complète' if args.mode == 'demo' else 'Test du système de traçage' if args.mode == 'trace' else 'Test composants PM améliorés'} ===")
        
        report = mode_functions[args.mode](args.text)
        
        # Affichage du rapport
        print("\n" + "=" * 70)
        print("RAPPORT GÉNÉRE:")
        print("=" * 70)
        print(report)
        
        # Sauvegarde optionnelle
        if args.save:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"orchestration_conversationnelle_{args.mode}_{timestamp}.md"
            report_path = LOGS_DIR / filename
            
            try:
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"\n[SUCCESS] Rapport sauvegardé: {report_path}")
                logger.info(f"Rapport sauvegardé: {report_path}")
            except Exception as e:
                print(f"\n[ERROR] Erreur sauvegarde: {e}")
                logger.error(f"Erreur sauvegarde: {e}")
        
        print(f"\n[INFO] Mode {args.mode} exécuté avec succès")
        logger.info(f"Orchestration {args.mode} terminée avec succès")
        
        return report
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du mode {args.mode}: {e}")
        print(f"\n[ERROR] Erreur lors de l'exécution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
>>>>>>> BACKUP
