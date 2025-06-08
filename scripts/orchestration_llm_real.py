<<<<<<< MAIN
#!/usr/bin/env python3
"""
Orchestration conversationnelle avec VRAIS agents LLM
====================================================

Script pour générer des traces d'analyse avec de véritables appels à GPT-4o-mini
au lieu de simulations. Utilise le composant réutilisable RealLLMOrchestrator.
"""

import asyncio
import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

# Ajout du chemin racine pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import du composant réutilisable
from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
from argumentation_analysis.core.llm_service import create_llm_service

# Configuration
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("OrchestrationLLMReal")


async def main():
    """Point d'entrée principal utilisant le composant réutilisable."""
    parser = argparse.ArgumentParser(description="Orchestration avec agents LLM réels")
    parser.add_argument("--text", required=True, help="Texte à analyser")
    parser.add_argument("--save", action="store_true", help="Sauvegarder le rapport")
    
    args = parser.parse_args()
    
    print("ORCHESTRATION AVEC AGENTS LLM REELS")
    print("=" * 60)
    
    try:
        # Créer le service LLM
        llm_service = create_llm_service()
        
        # Utiliser le composant réutilisable
        orchestrator = RealLLMOrchestrator(mode="real", llm_service=llm_service)
        
        # Exécuter l'orchestration
        report = await orchestrator.run_orchestration(args.text)
        
        print("\n" + "=" * 60)
        print("RAPPORT GÉNÉRÉ:")
        print("=" * 60)
        
        # Nettoyage complet des caractères Unicode problématiques
        clean_report = re.sub(r'[^\x00-\x7F]+', '[UNICODE]', report)
        print(clean_report)
        
        if args.save:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"orchestration_llm_real_{timestamp}.md"
            filepath = LOGS_DIR / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report)
                
            print(f"\n[SUCCESS] Rapport sauvegardé: {filepath}")
            
        print("\n[INFO] Orchestration LLM réelle terminée avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'orchestration: {e}", exc_info=True)
        return 1
        
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))

=======
#!/usr/bin/env python3
"""
Orchestration conversationnelle avec VRAIS agents LLM
====================================================

Script pour générer des traces d'analyse avec de véritables appels à GPT-4o-mini
au lieu de simulations. Utilise le composant réutilisable RealLLMOrchestrator.
"""

import asyncio
import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

# Ajout du chemin racine pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import du composant réutilisable
from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
from argumentation_analysis.core.llm_service import create_llm_service

# Configuration
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("OrchestrationLLMReal")


async def main():
    """Point d'entrée principal utilisant le composant réutilisable."""
    parser = argparse.ArgumentParser(description="Orchestration avec agents LLM réels")
    parser.add_argument("--text", required=True, help="Texte à analyser")
    parser.add_argument("--save", action="store_true", help="Sauvegarder le rapport")
    
    args = parser.parse_args()
    
    print("ORCHESTRATION AVEC AGENTS LLM REELS")
    print("=" * 60)
    
    try:
        # Créer le service LLM
        llm_service = create_llm_service()
        
        # Utiliser le composant réutilisable
        orchestrator = RealLLMOrchestrator(mode="real", llm_service=llm_service)
        
        # Exécuter l'orchestration
        report = await orchestrator.run_orchestration(args.text)
        
        print("\n" + "=" * 60)
        print("RAPPORT GÉNÉRÉ:")
        print("=" * 60)
        
        # Nettoyage complet des caractères Unicode problématiques
        clean_report = re.sub(r'[^\x00-\x7F]+', '[UNICODE]', report)
        print(clean_report)
        
        if args.save:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"orchestration_llm_real_{timestamp}.md"
            filepath = LOGS_DIR / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report)
                
            print(f"\n[SUCCESS] Rapport sauvegardé: {filepath}")
            
        print("\n[INFO] Orchestration LLM réelle terminée avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'orchestration: {e}", exc_info=True)
        return 1
        
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
>>>>>>> BACKUP
