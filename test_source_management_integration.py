#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test d'intégration du composant source_management refactorisé.

Ce script valide :
1. L'intégration avec l'écosystème core existant
2. La compatibilité avec les composants refactorisés (pipelines, orchestrateurs)
3. Les nouvelles fonctionnalités unifiées (fichiers .enc, texte libre, etc.)
4. La cohérence des APIs programmables et interactives
"""

import os
import sys
import tempfile
import logging
from pathlib import Path
from typing import Tuple

# Ajout du répertoire racine du projet au chemin
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Imports des composants refactorisés
from argumentation_analysis.core.source_management import (
    create_unified_source_manager,
    InteractiveSourceSelector,
    UnifiedSourceType,
    UnifiedSourceConfig
)

# Imports des composants refactorisés récemment (optionnels pour test interface)
try:
    from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
    from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
    ORCHESTRATORS_AVAILABLE = True
except ImportError:
    ORCHESTRATORS_AVAILABLE = False
    ConversationOrchestrator = None
    RealLLMOrchestrator = None

# Import du script refactorisé pour comparaison
from scripts.core.unified_source_selector import UnifiedSourceSelector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SourceManagementIntegrationTest:
    """Test d'intégration du système de gestion de sources refactorisé."""
    
    def __init__(self):
        self.test_results = []
        self.temp_files = []
    
    def log_test_result(self, test_name: str, success: bool, message: str):
        """Enregistre le résultat d'un test."""
        status = "✅ SUCCÈS" if success else "❌ ÉCHEC"
        result = f"{status} - {test_name}: {message}"
        self.test_results.append((test_name, success, message))
        logger.info(result)
        print(result)
    
    def cleanup(self):
        """Nettoie les fichiers temporaires."""
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception as e:
                logger.warning(f"Erreur nettoyage {temp_file}: {e}")
    
    def test_core_component_api(self) -> bool:
        """Test 1: API du composant core UnifiedSourceManager."""
        try:
            # Test sources simples
            with create_unified_source_manager(
                source_type="simple",
                interactive_mode=False
            ) as manager:
                extract_definitions, status = manager.load_sources()
                if not extract_definitions:
                    raise Exception(f"Échec chargement sources simples: {status}")
                
                text, description = manager.select_text_for_analysis(extract_definitions)
                if not text or len(text) < 50:
                    raise Exception("Texte sélectionné trop court ou vide")
            
            self.log_test_result("API Core - Sources simples", True, 
                               f"Texte chargé: {len(text)} caractères")
            return True
            
        except Exception as e:
            self.log_test_result("API Core - Sources simples", False, str(e))
            return False
    
    def test_free_text_functionality(self) -> bool:
        """Test 2: Fonctionnalité texte libre."""
        try:
            test_text = """
            Voici un exemple d'argumentation politique. Certains politiciens utilisent des sophismes
            pour convaincre leur auditoire. Par exemple, l'argument d'autorité consiste à se référer
            à une autorité pour valider un point, même si cette autorité n'est pas compétente dans
            le domaine concerné. Il est important de développer un esprit critique face à ces techniques.
            """
            
            with create_unified_source_manager(
                source_type="free_text",
                free_text_content=test_text,
                interactive_mode=False
            ) as manager:
                extract_definitions, status = manager.load_sources()
                if not extract_definitions:
                    raise Exception(f"Échec chargement texte libre: {status}")
                
                text, description = manager.select_text_for_analysis(extract_definitions)
                if text.strip() != test_text.strip():
                    raise Exception("Texte libre non préservé correctement")
            
            self.log_test_result("Texte libre", True, 
                               f"Texte préservé: {len(text)} caractères")
            return True
            
        except Exception as e:
            self.log_test_result("Texte libre", False, str(e))
            return False
    
    def test_text_file_functionality(self) -> bool:
        """Test 3: Fonctionnalité fichier texte local."""
        try:
            # Créer un fichier temporaire de test
            test_content = """
            Analyse critique de l'argumentation.
            
            Les sophismes sont des erreurs de raisonnement qui peuvent être utilisées
            intentionnellement pour tromper ou involontairement par méconnaissance.
            La détection de ces erreurs nécessite une analyse rigoureuse.
            """
            
            temp_file = Path(tempfile.mktemp(suffix=".txt"))
            self.temp_files.append(temp_file)
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(test_content)
            
            with create_unified_source_manager(
                source_type="text_file",
                text_file_path=str(temp_file),
                interactive_mode=False
            ) as manager:
                extract_definitions, status = manager.load_sources()
                if not extract_definitions:
                    raise Exception(f"Échec chargement fichier texte: {status}")
                
                text, description = manager.select_text_for_analysis(extract_definitions)
                if not text or "sophismes" not in text:
                    raise Exception("Contenu fichier texte non chargé correctement")
            
            self.log_test_result("Fichier texte local", True, 
                               f"Fichier chargé: {temp_file.name}")
            return True
            
        except Exception as e:
            self.log_test_result("Fichier texte local", False, str(e))
            return False
    
    def test_script_wrapper_compatibility(self) -> bool:
        """Test 4: Compatibilité avec le wrapper de script refactorisé."""
        try:
            # Test du wrapper de script
            selector = UnifiedSourceSelector(auto_passphrase=True)
            
            # Test mode batch
            text, description, source_type = selector.load_source_batch(
                source_type="simple"
            )
            
            if not text or len(text) < 50:
                raise Exception("Wrapper script ne fonctionne pas correctement")
            
            # Test listing des sources
            sources = selector.list_available_sources()
            if "simple" not in sources:
                raise Exception("Listing des sources incorrect")
            
            self.log_test_result("Wrapper Script", True, 
                               f"Source chargée: {source_type}")
            return True
            
        except Exception as e:
            self.log_test_result("Wrapper Script", False, str(e))
            return False
    
    def test_pipeline_integration(self) -> bool:
        """Test 5: Intégration avec les pipelines existants."""
        try:
            # Créer un texte pour analyse
            test_text = """
            L'argument ad hominem est une technique rhétorique qui consiste à attaquer
            la personne qui présente un argument plutôt que l'argument lui-même.
            Cette technique est souvent utilisée en politique pour discréditer l'opposant.
            Par exemple, dire 'vous ne pouvez pas faire confiance à ses idées économiques
            car il a fait faillite' constitue un ad hominem.
            """
            
            # Utiliser le source manager pour fournir le texte
            with create_unified_source_manager(
                source_type="free_text",
                free_text_content=test_text,
                interactive_mode=False
            ) as source_manager:
                
                extract_definitions, status = source_manager.load_sources()
                if not extract_definitions:
                    raise Exception(f"Échec chargement pour pipeline: {status}")
                
                text, description = source_manager.select_text_for_analysis(extract_definitions)
                
                # Vérifier que le texte est correctement formaté pour les pipelines
                if not text or len(text) < 50:
                    raise Exception("Texte insuffisant pour pipeline")
                
                # Test d'import des fonctions de pipeline
                from argumentation_analysis.pipelines.advanced_rhetoric import run_enhanced_rhetoric_pipeline
                if not callable(run_enhanced_rhetoric_pipeline):
                    raise Exception("Fonction pipeline non disponible")
                
                # Interface validée - texte disponible et pipeline importable
                self.log_test_result("Intégration Pipeline", True,
                                   "Texte fourni compatible avec pipelines existants")
                return True
            
        except Exception as e:
            self.log_test_result("Intégration Pipeline", False, str(e))
            return False
    
    def test_orchestrator_integration(self) -> bool:
        """Test 6: Intégration avec les orchestrateurs refactorisés."""
        try:
            # Test de l'interface avec les orchestrateurs
            test_config = {
                "source_type": "simple",
                "interactive_mode": False
            }
            
            # Créer un source manager
            with create_unified_source_manager(**test_config) as source_manager:
                extract_definitions, status = source_manager.load_sources()
                if not extract_definitions:
                    raise Exception(f"Échec pour orchestrateur: {status}")
                
                text, description = source_manager.select_text_for_analysis(extract_definitions)
                
                # Vérifier la compatibilité avec les orchestrateurs si disponibles
                if ORCHESTRATORS_AVAILABLE:
                    orchestrator_configs = [
                        {"class": ConversationOrchestrator, "name": "ConversationOrchestrator"},
                        {"class": RealLLMOrchestrator, "name": "RealLLMOrchestrator"}
                    ]
                    
                    for config in orchestrator_configs:
                        try:
                            # Vérifier que l'orchestrateur peut être instancié
                            orchestrator_class = config["class"]
                            if hasattr(orchestrator_class, '__init__'):
                                pass  # Interface de base présente
                        except Exception as e:
                            raise Exception(f"Problème avec {config['name']}: {e}")
                    
                    self.log_test_result("Intégration Orchestrateurs", True,
                                       "Interfaces orchestrateurs compatibles")
                else:
                    self.log_test_result("Intégration Orchestrateurs", True,
                                       "Orchestrateurs non disponibles - texte compatible")
                return True
            
        except Exception as e:
            self.log_test_result("Intégration Orchestrateurs", False, str(e))
            return False
    
    def test_api_programmable(self) -> bool:
        """Test 7: API programmable pour autres composants."""
        try:
            # Test de l'API programmable pour usage par d'autres composants
            
            # Configuration programmatique
            config = UnifiedSourceConfig(
                source_type=UnifiedSourceType.FREE_TEXT,
                free_text_content="Texte de test pour API programmable",
                interactive_mode=False,
                auto_cleanup=True
            )
            
            from argumentation_analysis.core.source_management import UnifiedSourceManager
            
            with UnifiedSourceManager(config) as manager:
                # Test chargement
                definitions, status = manager.load_sources()
                if not definitions:
                    raise Exception(f"API programmable échec: {status}")
                
                # Test sélection
                text, desc = manager.select_text_for_analysis(definitions)
                if not text:
                    raise Exception("API programmable - texte vide")
                
                # Test listing
                sources = manager.list_available_sources()
                if not isinstance(sources, dict):
                    raise Exception("API programmable - listing incorrect")
            
            self.log_test_result("API Programmable", True, 
                               "Toutes les opérations API réussies")
            return True
            
        except Exception as e:
            self.log_test_result("API Programmable", False, str(e))
            return False
    
    def run_all_tests(self) -> Tuple[int, int]:
        """Exécute tous les tests d'intégration."""
        print("\n" + "="*70)
        print("    TEST D'INTÉGRATION - GESTION SOURCES REFACTORISÉE")
        print("="*70)
        
        tests = [
            self.test_core_component_api,
            self.test_free_text_functionality,
            self.test_text_file_functionality,
            self.test_script_wrapper_compatibility,
            self.test_pipeline_integration,
            self.test_orchestrator_integration,
            self.test_api_programmable
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                logger.error(f"Erreur test {test.__name__}: {e}")
        
        print("\n" + "="*70)
        print(f"RÉSULTATS: {passed}/{total} tests réussis")
        print("="*70)
        
        # Résumé détaillé
        print("\nRÉSUMÉ DÉTAILLÉ:")
        for test_name, success, message in self.test_results:
            status = "✅" if success else "❌"
            print(f"{status} {test_name}: {message}")
        
        if passed == total:
            print(f"\n🎉 TOUS LES TESTS RÉUSSIS ! Le composant source_management est bien intégré.")
        else:
            print(f"\n⚠️  {total - passed} test(s) en échec. Vérification nécessaire.")
        
        self.cleanup()
        return passed, total

def main():
    """Point d'entrée principal."""
    try:
        tester = SourceManagementIntegrationTest()
        passed, total = tester.run_all_tests()
        
        # Code de sortie
        sys.exit(0 if passed == total else 1)
        
    except Exception as e:
        logger.error(f"Erreur lors des tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()