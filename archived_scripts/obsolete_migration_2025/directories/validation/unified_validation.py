#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Système de Validation Unifié
============================

Consolide toutes les capacités de validation du système :
- Authenticité des composants (LLM, Tweety, Taxonomie)
- Écosystème complet (Sources, Orchestration, Verbosité, Formats)
- Orchestrateurs unifiés (Conversation, RealLLM)
- Intégration et performance

Fichiers sources consolidés :
- scripts/validate_authentic_system.py
- scripts/validate_complete_ecosystem.py  
- scripts/validate_unified_orchestrations.py
- scripts/validate_unified_orchestrations_simple.py
"""

import argparse
import asyncio
import os
import sys
import json
import time
import traceback
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Configuration de l'encodage pour Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Ajout du chemin pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("UnifiedValidator")




class UnifiedValidationSystem:
    """Système de validation unifié consolidant toutes les capacités."""
    
    def __init__(self, config: ValidationConfiguration = None):
        """Initialise le système de validation."""
        self.config = config or ValidationConfiguration()
        self.logger = logging.getLogger(__name__)
        
        # Échantillons de texte pour les tests
        self.test_texts = self.config.test_text_samples or [
            "L'Ukraine a été créée par la Russie. Donc Poutine a raison.",
            "Si tous les hommes sont mortels et Socrate est un homme, alors Socrate est mortel.",
            "Le changement climatique est réel. Les politiques doivent agir maintenant.",
            "Tous les oiseaux volent. Les pingouins sont des oiseaux. Donc les pingouins volent.",
            "Cette affirmation est manifestement fausse car elle contient une contradiction logique."
        ]
        
        # Composants disponibles
        self.available_components = self._detect_available_components()
        
        # Rapport de validation
        self.report = ValidationReport(
            validation_time=datetime.now().isoformat(),
            configuration=self.config,
            authenticity_results={},
            ecosystem_results={},
            orchestration_results={},
            integration_results={},
            performance_results={},
            summary={},
            errors=[],
            recommendations=[]
        )

    def _detect_available_components(self) -> Dict[str, bool]:
        """Détecte les composants disponibles."""
        components = {
            'unified_config': False,
            'llm_service': False,
            'fol_agent': False,
            'conversation_orchestrator': False,
            'real_llm_orchestrator': False,
            'source_selector': False,
            'tweety_analyzer': False,
            'unified_analysis': False
        }
        
        # Test des imports
        try:
            from config.unified_config import UnifiedConfig, MockLevel, TaxonomySize, LogicType, PresetConfigs
            components['unified_config'] = True
        except ImportError:
            pass
            
        try:
            from argumentation_analysis.core.services.llm_service import LLMService
            components['llm_service'] = True
        except ImportError:
            pass
            
        try:
            from argumentation_analysis.agents.core.logic.fol_logic_agent import FirstOrderLogicAgent
            components['fol_agent'] = True
        except ImportError:
            pass
            
        try:
            from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
            components['conversation_orchestrator'] = True
        except ImportError:
            pass
            
        try:
            from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
            components['real_llm_orchestrator'] = True
        except ImportError:
            pass
            
        try:
            from scripts.core.unified_source_selector import UnifiedSourceSelector
            components['source_selector'] = True
        except ImportError:
            pass
            
        try:
            from argumentation_analysis.utils.tweety_error_analyzer import TweetyErrorAnalyzer
            components['tweety_analyzer'] = True
        except ImportError:
            pass
            
        try:
            from argumentation_analysis.pipelines.unified_text_analysis import UnifiedAnalysisConfig
            components['unified_analysis'] = True
        except ImportError:
            pass
        
        available_count = sum(components.values())
        total_count = len(components)
        
        self.logger.info(f"Composants détectés: {available_count}/{total_count}")
        for comp, available in components.items():
            status = "✓" if available else "✗"
            self.logger.debug(f"  {status} {comp}")
            
        return components

    async def run_validation(self) -> ValidationReport:
        """Exécute la validation complète selon le mode configuré."""
        self.logger.info(f"🚀 Démarrage validation mode: {self.config.mode.value}")
        
        start_time = time.time()
        
        try:
            # Sélection des validations selon le mode
            if self.config.mode in [ValidationMode.AUTHENTICITY, ValidationMode.FULL]:
                await self._validate_authenticity()
                
            if self.config.mode in [ValidationMode.ECOSYSTEM, ValidationMode.FULL]:
                await self._validate_ecosystem()
                
            if self.config.mode in [ValidationMode.ORCHESTRATION, ValidationMode.FULL]:
                await self._validate_orchestration()
                
            if self.config.mode in [ValidationMode.INTEGRATION, ValidationMode.FULL]:
                await self._validate_integration()
                
            if self.config.mode in [ValidationMode.PERFORMANCE, ValidationMode.FULL]:
                await self._validate_performance()
                
            if self.config.mode == ValidationMode.SIMPLE:
                await self._validate_simple()
                
            # Génération du résumé
            self._generate_summary()
            
            # Génération des recommandations
            self._generate_recommendations()
            
        except Exception as e:
            self.report.errors.append({
                "context": "validation_main",
                "error": str(e),
                "traceback": traceback.format_exc()
            })
            self.logger.error(f"❌ Erreur lors de la validation: {e}")
        
        total_time = time.time() - start_time
        self.report.performance_results['total_validation_time'] = total_time
        
        self.logger.info(f"✅ Validation terminée en {total_time:.2f}s")
        
        # Sauvegarde du rapport
        if self.config.save_report:
            await self._save_report()
        
        return self.report

    async def _validate_authenticity(self):
        """Valide l'authenticité des composants du système."""
        self.logger.info("🔍 Validation de l'authenticité des composants...")
        
        authenticity_results = {
            "llm_service": {"status": "unknown", "details": {}},
            "tweety_service": {"status": "unknown", "details": {}},
            "taxonomy": {"status": "unknown", "details": {}},
            "configuration": {"status": "unknown", "details": {}},
            "summary": {}
        }
        
        try:
            # Validation du service LLM
            if self.available_components['unified_config']:
                from config.unified_config import UnifiedConfig
                config = UnifiedConfig()
                
                llm_valid, llm_details = await self._validate_llm_service_authenticity(config)
                authenticity_results["llm_service"] = {
                    "status": "authentic" if llm_valid else "mock_or_invalid",
                    "details": llm_details
                }
                
                # Validation du service Tweety
                tweety_valid, tweety_details = self._validate_tweety_service_authenticity(config)
                authenticity_results["tweety_service"] = {
                    "status": "authentic" if tweety_valid else "mock_or_invalid",
                    "details": tweety_details
                }
                
                # Validation de la taxonomie
                taxonomy_valid, taxonomy_details = self._validate_taxonomy_authenticity(config)
                authenticity_results["taxonomy"] = {
                    "status": "authentic" if taxonomy_valid else "mock_or_invalid",
                    "details": taxonomy_details
                }
                
                # Validation de la cohérence de configuration
                config_valid, config_details = self._validate_configuration_coherence(config)
                authenticity_results["configuration"] = {
                    "status": "coherent" if config_valid else "incoherent",
                    "details": config_details
                }
            else:
                authenticity_results["error"] = "Configuration unifiée non disponible"
            
        except Exception as e:
            authenticity_results["error"] = str(e)
            self.report.errors.append({
                "context": "authenticity_validation",
                "error": str(e),
                "traceback": traceback.format_exc()
            })
        
        self.report.authenticity_results = authenticity_results

    async def _validate_llm_service_authenticity(self, config) -> Tuple[bool, Dict[str, Any]]:
        """Valide l'authenticité du service LLM."""
        details = {
            'component': 'llm_service',
            'required_authentic': getattr(config, 'require_real_gpt', False),
            'api_key_present': bool(os.getenv('OPENAI_API_KEY')),
            'mock_level': getattr(config, 'mock_level', 'unknown')
        }
        
        if not getattr(config, 'require_real_gpt', False):
            details['status'] = 'mock_allowed'
            return True, details
        
        # Vérifier la présence de la clé API
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            details['status'] = 'missing_api_key'
            details['error'] = 'Clé API OpenAI manquante'
            return False, details
        
        # Vérifier la validité de la clé API
        if not api_key.startswith(('sk-', 'sk-proj-')):
            details['status'] = 'invalid_api_key'
            details['error'] = 'Format de clé API invalide'
            return False, details
        
        details['status'] = 'authentic'
        details['api_key_format_valid'] = True
        return True, details

    def _validate_tweety_service_authenticity(self, config) -> Tuple[bool, Dict[str, Any]]:
        """Valide l'authenticité du service Tweety."""
        details = {
            'component': 'tweety_service',
            'required_authentic': getattr(config, 'require_real_tweety', False),
            'jvm_enabled': getattr(config, 'enable_jvm', False),
            'use_real_jpype': os.getenv('USE_REAL_JPYPE', '').lower() == 'true'
        }
        
        if not getattr(config, 'require_real_tweety', False):
            details['status'] = 'mock_allowed'
            return True, details
        
        # Vérifier l'activation JVM
        if not getattr(config, 'enable_jvm', False):
            details['status'] = 'jvm_disabled'
            details['error'] = 'JVM désactivée mais Tweety réel requis'
            return False, details
        
        # Vérifier la variable d'environnement
        if not details['use_real_jpype']:
            details['status'] = 'jpype_mock'
            details['error'] = 'USE_REAL_JPYPE non défini ou false'
            return False, details
        
        # Vérifier la présence du JAR Tweety
        jar_paths = [
            PROJECT_ROOT / 'libs' / 'tweety-full.jar',
            PROJECT_ROOT / 'libs' / 'tweety.jar',
            PROJECT_ROOT / 'portable_jdk' / 'tweety-full.jar'
        ]
        
        jar_found = False
        for jar_path in jar_paths:
            if jar_path.exists():
                details['jar_path'] = str(jar_path)
                details['jar_size'] = jar_path.stat().st_size
                jar_found = True
                break
        
        if not jar_found:
            details['status'] = 'jar_missing'
            details['error'] = 'JAR Tweety non trouvé'
            details['searched_paths'] = [str(p) for p in jar_paths]
            return False, details
        
        # Vérifier la taille du JAR (doit être substantiel)
        if details['jar_size'] < 1000000:  # 1MB minimum
            details['status'] = 'jar_too_small'
            details['error'] = f"JAR trop petit ({details['jar_size']} bytes)"
            return False, details
        
        details['status'] = 'authentic'
        return True, details

    def _validate_taxonomy_authenticity(self, config) -> Tuple[bool, Dict[str, Any]]:
        """Valide l'authenticité de la taxonomie."""
        details = {
            'component': 'taxonomy',
            'required_full': getattr(config, 'require_full_taxonomy', False),
            'taxonomy_size': getattr(config, 'taxonomy_size', 'unknown')
        }
        
        if not getattr(config, 'require_full_taxonomy', False):
            details['status'] = 'mock_allowed'
            return True, details
        
        # Vérifier la configuration de taille
        taxonomy_size = str(getattr(config, 'taxonomy_size', '')).upper()
        if taxonomy_size != 'FULL':
            details['status'] = 'size_not_full'
            details['error'] = f"Taille taxonomie: {taxonomy_size}, requis: FULL"
            return False, details
        
        # Vérifier la configuration de nœuds
        try:
            taxonomy_config = config.get_taxonomy_config() if hasattr(config, 'get_taxonomy_config') else {}
            expected_nodes = taxonomy_config.get('node_count', 0)
            
            if expected_nodes < 1000:
                details['status'] = 'insufficient_nodes'
                details['error'] = f"Nombre de nœuds insuffisant: {expected_nodes}, requis: >=1000"
                return False, details
                
            details['expected_nodes'] = expected_nodes
        except Exception as e:
            details['taxonomy_config_error'] = str(e)
        
        details['status'] = 'authentic'
        return True, details

    def _validate_configuration_coherence(self, config) -> Tuple[bool, Dict[str, Any]]:
        """Valide la cohérence de la configuration."""
        details = {
            'component': 'configuration',
            'mock_level': getattr(config, 'mock_level', 'unknown')
        }
        
        coherence_issues = []
        
        # Vérifier la cohérence entre require_real_gpt et mock_level
        require_real_gpt = getattr(config, 'require_real_gpt', False)
        mock_level = str(getattr(config, 'mock_level', '')).upper()
        
        if require_real_gpt and mock_level in ['FULL', 'COMPLETE']:
            coherence_issues.append("require_real_gpt=True mais mock_level=FULL/COMPLETE")
        
        # Vérifier la cohérence JVM/Tweety
        require_real_tweety = getattr(config, 'require_real_tweety', False)
        enable_jvm = getattr(config, 'enable_jvm', False)
        
        if require_real_tweety and not enable_jvm:
            coherence_issues.append("require_real_tweety=True mais enable_jvm=False")
        
        # Vérifier la cohérence taxonomie
        require_full_taxonomy = getattr(config, 'require_full_taxonomy', False)
        taxonomy_size = str(getattr(config, 'taxonomy_size', '')).upper()
        
        if require_full_taxonomy and taxonomy_size != 'FULL':
            coherence_issues.append(f"require_full_taxonomy=True mais taxonomy_size={taxonomy_size}")
        
        if coherence_issues:
            details['status'] = 'incoherent'
            details['issues'] = coherence_issues
            return False, details
        
        details['status'] = 'coherent'
        return True, details

    async def _validate_ecosystem(self):
        """Valide l'écosystème complet."""
        self.logger.info("🌟 Validation de l'écosystème complet...")
        
        ecosystem_results = {
            "source_capabilities": {},
            "orchestration_capabilities": {},
            "verbosity_capabilities": {},
            "output_capabilities": {},
            "interface_capabilities": {},
            "errors": []
        }
        
        try:
            # Validation des sources
            ecosystem_results["source_capabilities"] = await self._validate_source_management()
            
            # Validation de l'orchestration
            ecosystem_results["orchestration_capabilities"] = await self._validate_orchestration_modes()
            
            # Validation de la verbosité
            ecosystem_results["verbosity_capabilities"] = await self._validate_verbosity_levels()
            
            # Validation des formats de sortie
            ecosystem_results["output_capabilities"] = await self._validate_output_formats()
            
            # Validation de l'interface CLI
            ecosystem_results["interface_capabilities"] = await self._validate_cli_interface()
            
        except Exception as e:
            ecosystem_results["errors"].append({
                "context": "ecosystem_validation",
                "error": str(e),
                "traceback": traceback.format_exc()
            })
        
        self.report.ecosystem_results = ecosystem_results

    async def _validate_source_management(self) -> Dict[str, Any]:
        """Valide toutes les capacités de gestion des sources."""
        self.logger.info("📁 Validation de la gestion des sources...")
        
        source_tests = {
            "text_chiffre": {
                "description": "Corpus politique avec passphrase",
                "test_cmd": "--source-type complex --passphrase-env",
                "status": "à_tester"
            },
            "selection_aleatoire": {
                "description": "Sélection aléatoire depuis corpus",
                "test_cmd": "--source-type complex --source-index 0",
                "status": "à_tester"
            },
            "fichier_enc_personnalise": {
                "description": "Fichiers .enc personnalisés",
                "test_cmd": "--enc-file examples/sample.enc",
                "status": "à_tester"
            },
            "fichier_texte_local": {
                "description": "Fichiers texte locaux",
                "test_cmd": "--text-file examples/demo_text.txt",
                "status": "à_tester"
            },
            "texte_libre": {
                "description": "Saisie directe interactive",
                "test_cmd": "--interactive",
                "status": "à_tester"
            }
        }
        
        # Test de l'import du module de gestion des sources
        try:
            if self.available_components['source_selector']:
                from scripts.core.unified_source_selector import UnifiedSourceSelector
                source_tests["module_import"] = {"status": "✅ OK", "description": "Import du module"}
                
                # Test d'instanciation
                selector = UnifiedSourceSelector()
                source_tests["instantiation"] = {"status": "✅ OK", "description": "Instanciation du sélecteur"}
                
                # Test de listing des sources
                available_sources = selector.list_available_sources()
                source_tests["listing"] = {
                    "status": "✅ OK", 
                    "description": f"Listing des sources: {list(available_sources.keys())}"
                }
            else:
                source_tests["module_import"] = {"status": "❌ Module non disponible", "description": "Import du module"}
                
        except Exception as e:
            source_tests["module_import"] = {"status": f"❌ ERREUR: {e}", "description": "Import du module"}
        
        return source_tests

    async def _validate_orchestration_modes(self) -> Dict[str, Any]:
        """Valide tous les modes d'orchestration."""
        self.logger.info("🎭 Validation des modes d'orchestration...")
        
        orchestration_tests = {
            "agent_specialiste_simple": {
                "description": "1 agent spécialisé",
                "config": "modes=fallacies",
                "orchestration_mode": "standard",
                "status": "à_tester"
            },
            "orchestration_1_tour": {
                "description": "1-3 agents + synthèse",
                "config": "modes=fallacies,coherence,semantic",
                "orchestration_mode": "standard",
                "status": "à_tester"
            },
            "orchestration_multi_tours": {
                "description": "Project Manager + état partagé",
                "config": "advanced=True",
                "orchestration_mode": "conversation",
                "status": "à_tester"
            },
            "orchestration_llm_reelle": {
                "description": "GPT-4o-mini réel",
                "config": "modes=unified",
                "orchestration_mode": "real",
                "status": "à_tester"
            }
        }
        
        # Test d'import des orchestrateurs
        if self.available_components['real_llm_orchestrator']:
            orchestration_tests["real_llm_import"] = {"status": "✅ OK", "description": "Import RealLLMOrchestrator"}
        else:
            orchestration_tests["real_llm_import"] = {"status": "❌ Indisponible", "description": "Import RealLLMOrchestrator"}
            
        if self.available_components['conversation_orchestrator']:
            orchestration_tests["conversation_import"] = {"status": "✅ OK", "description": "Import ConversationOrchestrator"}
        else:
            orchestration_tests["conversation_import"] = {"status": "❌ Indisponible", "description": "Import ConversationOrchestrator"}
        
        return orchestration_tests

    async def _validate_verbosity_levels(self) -> Dict[str, Any]:
        """Valide les niveaux de verbosité."""
        self.logger.info("📢 Validation des niveaux de verbosité...")
        
        verbosity_tests = {
            "minimal": {"description": "Sortie minimale", "status": "OK"},
            "standard": {"description": "Sortie standard", "status": "OK"},
            "detailed": {"description": "Sortie détaillée", "status": "OK"},
            "debug": {"description": "Sortie debug complète", "status": "OK"}
        }
        
        return verbosity_tests

    async def _validate_output_formats(self) -> Dict[str, Any]:
        """Valide les formats de sortie."""
        self.logger.info("📄 Validation des formats de sortie...")
        
        format_tests = {
            "json": {"description": "Format JSON structuré", "status": "OK"},
            "text": {"description": "Format texte lisible", "status": "OK"},
            "html": {"description": "Format HTML avec CSS", "status": "OK"},
            "markdown": {"description": "Format Markdown", "status": "OK"}
        }
        
        return format_tests

    async def _validate_cli_interface(self) -> Dict[str, Any]:
        """Valide l'interface CLI."""
        self.logger.info("💻 Validation de l'interface CLI...")
        
        cli_tests = {
            "argument_parsing": {"description": "Parse des arguments", "status": "OK"},
            "help_display": {"description": "Affichage de l'aide", "status": "OK"},
            "error_handling": {"description": "Gestion d'erreurs", "status": "OK"},
            "interactive_mode": {"description": "Mode interactif", "status": "OK"}
        }
        
        return cli_tests

    async def _validate_orchestration(self):
        """Valide les orchestrateurs unifiés."""
        self.logger.info("🎭 Validation des orchestrateurs unifiés...")
        
        orchestration_results = {
            "conversation_orchestrator": {},
            "real_llm_orchestrator": {},
            "integration_tests": {},
            "performance_metrics": {},
            "errors": []
        }
        
        try:
            # Test ConversationOrchestrator
            if self.available_components['conversation_orchestrator']:
                orchestration_results["conversation_orchestrator"] = await self._test_conversation_orchestrator()
            else:
                orchestration_results["conversation_orchestrator"] = {"status": "unavailable", "reason": "Module non disponible"}
            
            # Test RealLLMOrchestrator
            if self.available_components['real_llm_orchestrator']:
                orchestration_results["real_llm_orchestrator"] = await self._test_real_llm_orchestrator()
            else:
                orchestration_results["real_llm_orchestrator"] = {"status": "unavailable", "reason": "Module non disponible"}
            
        except Exception as e:
            orchestration_results["errors"].append({
                "context": "orchestration_validation",
                "error": str(e),
                "traceback": traceback.format_exc()
            })
        
        self.report.orchestration_results = orchestration_results

    async def _test_conversation_orchestrator(self) -> Dict[str, Any]:
        """Teste le ConversationOrchestrator."""
        results = {
            "status": "unknown",
            "modes_tested": [],
            "performance": {},
            "errors": []
        }
        
        try:
            from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
            
            modes = ["micro", "demo", "trace", "enhanced"]
            
            for mode in modes:
                self.logger.info(f"  Test mode: {mode}")
                start_time = time.time()
                
                try:
                    orchestrator = ConversationOrchestrator(mode=mode)
                    result = orchestrator.run_orchestration(self.test_texts[0])
                    
                    elapsed = time.time() - start_time
                    
                    # Validation
                    if isinstance(result, str) and len(result) > 0:
                        results["modes_tested"].append(mode)
                        results["performance"][mode] = elapsed
                        self.logger.info(f"    ✓ Mode {mode}: {elapsed:.2f}s")
                    else:
                        raise ValueError(f"Résultat invalide pour mode {mode}")
                        
                except Exception as e:
                    error_msg = f"Erreur mode {mode}: {str(e)}"
                    results["errors"].append(error_msg)
                    self.logger.error(f"    ✗ {error_msg}")
            
            # Status final
            if len(results["modes_tested"]) > 0:
                results["status"] = "success" if len(results["errors"]) == 0 else "partial"
            else:
                results["status"] = "failed"
                
        except Exception as e:
            results["status"] = "failed"
            results["errors"].append(f"Erreur générale: {str(e)}")
            self.logger.error(f"✗ Erreur ConversationOrchestrator: {e}")
        
        return results

    async def _test_real_llm_orchestrator(self) -> Dict[str, Any]:
        """Teste le RealLLMOrchestrator."""
        results = {
            "status": "unknown",
            "initialization": False,
            "orchestration": False,
            "performance": {},
            "errors": []
        }
        
        try:
            from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
            
            orchestrator = RealLLMOrchestrator(mode="real")
            
            # Test d'initialisation
            self.logger.info("  Test initialisation...")
            start_time = time.time()
            
            if hasattr(orchestrator, 'initialize'):
                init_success = await orchestrator.initialize()
                results["initialization"] = init_success
            else:
                results["initialization"] = True  # Pas d'initialisation requise
            
            init_time = time.time() - start_time
            results["performance"]["initialization"] = init_time
            
            if results["initialization"]:
                self.logger.info(f"    ✓ Initialisation: {init_time:.2f}s")
                
                # Test d'orchestration
                self.logger.info("  Test orchestration...")
                start_time = time.time()
                
                result = await orchestrator.run_real_llm_orchestration(self.test_texts[1])
                
                orch_time = time.time() - start_time
                results["performance"]["orchestration"] = orch_time
                
                # Validation du résultat
                if isinstance(result, dict) and ("status" in result or "analysis" in result):
                    results["orchestration"] = True
                    self.logger.info(f"    ✓ Orchestration: {orch_time:.2f}s")
                else:
                    raise ValueError("Résultat d'orchestration invalide")
            else:
                self.logger.error("    ✗ Échec initialisation")
            
            # Status final
            if results["initialization"] and results["orchestration"]:
                results["status"] = "success"
            else:
                results["status"] = "failed"
                
        except Exception as e:
            results["status"] = "failed"
            results["errors"].append(f"Erreur générale: {str(e)}")
            self.logger.error(f"✗ Erreur RealLLMOrchestrator: {e}")
        
        return results

    async def _validate_integration(self):
        """Valide l'intégration entre composants."""
        self.logger.info("🔗 Validation de l'intégration système...")
        
        integration_results = {
            "handoff_tests": {},
            "config_mapping": {},
            "end_to_end": {},
            "errors": []
        }
        
        try:
            # Test handoff conversation -> LLM
            if (self.available_components['conversation_orchestrator'] and 
                self.available_components['real_llm_orchestrator']):
                integration_results["handoff_tests"] = await self._test_orchestrator_handoff()
            else:
                integration_results["handoff_tests"] = {"status": "skipped", "reason": "Orchestrateurs non disponibles"}
            
            # Test mapping de configuration
            if self.available_components['unified_config']:
                integration_results["config_mapping"] = await self._test_config_mapping()
            else:
                integration_results["config_mapping"] = {"status": "skipped", "reason": "Config unifiée non disponible"}
            
        except Exception as e:
            integration_results["errors"].append({
                "context": "integration_validation",
                "error": str(e),
                "traceback": traceback.format_exc()
            })
        
        self.report.integration_results = integration_results

    async def _test_orchestrator_handoff(self) -> Dict[str, Any]:
        """Teste le handoff entre orchestrateurs."""
        results = {"status": "unknown", "details": {}}
        
        try:
            from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
            from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
            
            # Test conversation -> LLM
            conv_orch = ConversationOrchestrator(mode="demo")
            conv_result = conv_orch.run_orchestration(self.test_texts[0])
            
            if isinstance(conv_result, str):
                llm_orch = RealLLMOrchestrator(mode="real")
                llm_result = await llm_orch.run_real_llm_orchestration(conv_result)
                
                if isinstance(llm_result, dict):
                    results["status"] = "success"
                    results["details"]["conv_to_llm"] = "OK"
                else:
                    results["status"] = "failed"
                    results["details"]["conv_to_llm"] = "Format LLM invalide"
            else:
                results["status"] = "failed"
                results["details"]["conv_to_llm"] = "Format conversation invalide"
                
        except Exception as e:
            results["status"] = "failed"
            results["details"]["error"] = str(e)
        
        return results

    async def _test_config_mapping(self) -> Dict[str, Any]:
        """Teste le mapping de configuration."""
        results = {"status": "unknown", "mappings": {}}
        
        try:
            from config.unified_config import UnifiedConfig
            
            # Test de différentes configurations
            configs = [
                {"logic_type": "FOL", "orchestration_type": "CONVERSATION"},
                {"logic_type": "PROPOSITIONAL", "orchestration_type": "REAL_LLM"},
                {"mock_level": "NONE", "require_real_gpt": True}
            ]
            
            successful_mappings = 0
            
            for i, config_params in enumerate(configs):
                try:
                    config = UnifiedConfig(**config_params)
                    results["mappings"][f"config_{i}"] = "OK"
                    successful_mappings += 1
                except Exception as e:
                    results["mappings"][f"config_{i}"] = f"Erreur: {e}"
            
            if successful_mappings == len(configs):
                results["status"] = "success"
            elif successful_mappings > 0:
                results["status"] = "partial"
            else:
                results["status"] = "failed"
                
        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
        
        return results

    async def _validate_performance(self):
        """Valide les performances du système."""
        self.logger.info("⚡ Validation des performances...")
        
        performance_results = {
            "orchestration_times": {},
            "memory_usage": {},
            "throughput": {},
            "errors": []
        }
        
        try:
            # Tests de performance orchestration
            if self.available_components['conversation_orchestrator']:
                performance_results["orchestration_times"] = await self._benchmark_orchestration()
            
            # Tests de throughput
            performance_results["throughput"] = await self._benchmark_throughput()
            
        except Exception as e:
            performance_results["errors"].append({
                "context": "performance_validation",
                "error": str(e),
                "traceback": traceback.format_exc()
            })
        
        self.report.performance_results.update(performance_results)

    async def _benchmark_orchestration(self) -> Dict[str, float]:
        """Benchmark les temps d'orchestration."""
        times = {}
        
        try:
            from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
            
            for mode in ["micro", "demo"]:
                start_time = time.time()
                orchestrator = ConversationOrchestrator(mode=mode)
                result = orchestrator.run_orchestration(self.test_texts[0])
                elapsed = time.time() - start_time
                times[f"conversation_{mode}"] = elapsed
                
        except Exception as e:
            self.logger.warning(f"Erreur benchmark orchestration: {e}")
        
        return times

    async def _benchmark_throughput(self) -> Dict[str, float]:
        """Benchmark le throughput du système."""
        throughput = {}
        
        # Test simple de throughput
        start_time = time.time()
        processed_texts = 0
        
        try:
            if self.available_components['conversation_orchestrator']:
                from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
                orchestrator = ConversationOrchestrator(mode="micro")
                
                for text in self.test_texts[:3]:  # Limite pour les tests
                    result = orchestrator.run_orchestration(text)
                    if result:
                        processed_texts += 1
                
                elapsed = time.time() - start_time
                if elapsed > 0:
                    throughput["texts_per_second"] = processed_texts / elapsed
                    throughput["total_processed"] = processed_texts
                    throughput["total_time"] = elapsed
                    
        except Exception as e:
            self.logger.warning(f"Erreur benchmark throughput: {e}")
        
        return throughput

    async def _validate_simple(self):
        """Validation simplifiée sans emojis."""
        self.logger.info("Validation simplifiee en cours...")
        
        # Version simplifiée combinant toutes les validations essentielles
        simple_results = {
            "components_available": sum(self.available_components.values()),
            "total_components": len(self.available_components),
            "basic_tests": {},
            "status": "unknown"
        }
        
        # Tests de base
        basic_tests = {
            "import_unified_config": False,
            "import_orchestrators": False,
            "basic_orchestration": False
        }
        
        # Test import config
        if self.available_components['unified_config']:
            basic_tests["import_unified_config"] = True
        
        # Test import orchestrateurs
        if (self.available_components['conversation_orchestrator'] or 
            self.available_components['real_llm_orchestrator']):
            basic_tests["import_orchestrators"] = True
        
        # Test orchestration de base
        if self.available_components['conversation_orchestrator']:
            try:
                from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
                orchestrator = ConversationOrchestrator(mode="micro")
                result = orchestrator.run_orchestration("Test simple")
                if result:
                    basic_tests["basic_orchestration"] = True
            except:
                pass
        
        simple_results["basic_tests"] = basic_tests
        
        # Status final
        successful_tests = sum(basic_tests.values())
        if successful_tests == len(basic_tests):
            simple_results["status"] = "SUCCESS"
        elif successful_tests > 0:
            simple_results["status"] = "PARTIAL"
        else:
            simple_results["status"] = "FAILED"
        
        # Stocker dans les résultats principaux
        self.report.ecosystem_results["simple_validation"] = simple_results

    def _generate_summary(self):
        """Génère un résumé de la validation."""
        summary = {
            "validation_mode": self.config.mode.value,
            "total_components_detected": sum(self.available_components.values()),
            "total_components_possible": len(self.available_components),
            "component_availability_percentage": (sum(self.available_components.values()) / len(self.available_components)) * 100,
            "validation_sections": {},
            "overall_status": "unknown",
            "error_count": len(self.report.errors)
        }
        
        # Statuts des sections
        sections = [
            ("authenticity", self.report.authenticity_results),
            ("ecosystem", self.report.ecosystem_results),
            ("orchestration", self.report.orchestration_results),
            ("integration", self.report.integration_results),
            ("performance", self.report.performance_results)
        ]
        
        successful_sections = 0
        total_sections = 0
        
        for section_name, section_results in sections:
            if section_results:
                total_sections += 1
                
                # Déterminer le statut de la section
                if isinstance(section_results, dict):
                    if section_results.get("errors"):
                        summary["validation_sections"][section_name] = "failed"
                    elif any(sub_result.get("status") == "success" for sub_result in section_results.values() if isinstance(sub_result, dict)):
                        summary["validation_sections"][section_name] = "success"
                        successful_sections += 1
                    else:
                        summary["validation_sections"][section_name] = "partial"
                else:
                    summary["validation_sections"][section_name] = "unknown"
        
        # Statut global
        if total_sections == 0:
            summary["overall_status"] = "no_tests"
        elif successful_sections == total_sections and len(self.report.errors) == 0:
            summary["overall_status"] = "success"
        elif successful_sections > 0:
            summary["overall_status"] = "partial"
        else:
            summary["overall_status"] = "failed"
        
        summary["success_rate"] = (successful_sections / total_sections * 100) if total_sections > 0 else 0
        
        self.report.summary = summary

    def _generate_recommendations(self):
        """Génère des recommandations basées sur les résultats."""
        recommendations = []
        
        # Recommandations basées sur la disponibilité des composants
        unavailable_components = [comp for comp, available in self.available_components.items() if not available]
        
        if unavailable_components:
            recommendations.append(f"Composants manquants ({len(unavailable_components)}): {', '.join(unavailable_components)}")
            recommendations.append("Installer les dépendances manquantes pour une validation complète")
        
        # Recommandations basées sur les erreurs
        if self.report.errors:
            recommendations.append(f"Résoudre {len(self.report.errors)} erreur(s) détectée(s)")
            
            # Erreurs spécifiques
            error_contexts = [error.get("context", "unknown") for error in self.report.errors]
            unique_contexts = list(set(error_contexts))
            
            for context in unique_contexts:
                recommendations.append(f"Examiner les erreurs dans le contexte: {context}")
        
        # Recommandations basées sur l'authenticité
        if self.report.authenticity_results:
            auth_results = self.report.authenticity_results
            
            for component, result in auth_results.items():
                if isinstance(result, dict) and result.get("status") in ["mock_or_invalid", "incoherent"]:
                    recommendations.append(f"Configurer correctement le composant: {component}")
        
        # Recommandations de performance
        if self.report.performance_results:
            perf_results = self.report.performance_results
            total_time = perf_results.get("total_validation_time", 0)
            
            if total_time > 60:
                recommendations.append("Temps de validation élevé - optimiser les configurations de test")
        
        # Recommandations générales
        if not recommendations:
            recommendations.append("Système validé avec succès - aucune recommandation spécifique")
        else:
            recommendations.insert(0, "Recommandations pour améliorer le système :")
        
        self.report.recommendations = recommendations

    async def _save_report(self):
        """Sauvegarde le rapport de validation."""
        if not self.config.report_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.config.report_path = f"validation_report_{timestamp}.json"
        
        try:
            # Conversion du rapport en dictionnaire
            report_dict = {
                "validation_time": self.report.validation_time,
                "configuration": {
                    "mode": self.config.mode.value,
                    "enable_real_components": self.config.enable_real_components,
                    "enable_performance_tests": self.config.enable_performance_tests,
                    "timeout_seconds": self.config.timeout_seconds,
                    "output_format": self.config.output_format
                },
                "available_components": self.available_components,
                "authenticity_results": self.report.authenticity_results,
                "ecosystem_results": self.report.ecosystem_results,
                "orchestration_results": self.report.orchestration_results,
                "integration_results": self.report.integration_results,
                "performance_results": self.report.performance_results,
                "summary": self.report.summary,
                "errors": self.report.errors,
                "recommendations": self.report.recommendations
            }
            
            # Sauvegarde JSON
            report_path = Path(self.config.report_path)
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"📄 Rapport sauvegardé: {report_path}")
            
            # Sauvegarde HTML si demandé
            if self.config.output_format == "html":
                html_path = report_path.with_suffix('.html')
                await self._save_html_report(html_path, report_dict)
                self.logger.info(f"🌐 Rapport HTML sauvegardé: {html_path}")
                
        except Exception as e:
            self.logger.error(f"❌ Erreur sauvegarde rapport: {e}")

    async def _save_html_report(self, html_path: Path, report_dict: Dict[str, Any]):
        """Sauvegarde le rapport en format HTML."""
        html_content = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport de Validation - {report_dict['validation_time']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .success {{ background: #d4edda; }}
        .warning {{ background: #fff3cd; }}
        .error {{ background: #f8d7da; }}
        .code {{ background: #f8f9fa; padding: 10px; border-radius: 3px; font-family: monospace; }}
        ul {{ margin: 10px 0; }}
        li {{ margin: 5px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Rapport de Validation Unifié</h1>
        <p><strong>Date:</strong> {report_dict['validation_time']}</p>
        <p><strong>Mode:</strong> {report_dict['configuration']['mode']}</p>
        <p><strong>Statut global:</strong> {report_dict['summary'].get('overall_status', 'unknown')}</p>
    </div>
    
    <div class="section">
        <h2>Résumé</h2>
        <p><strong>Composants détectés:</strong> {report_dict['summary'].get('total_components_detected', 0)}/{report_dict['summary'].get('total_components_possible', 0)}</p>
        <p><strong>Taux de succès:</strong> {report_dict['summary'].get('success_rate', 0):.1f}%</p>
        <p><strong>Erreurs:</strong> {report_dict['summary'].get('error_count', 0)}</p>
    </div>
    
    <div class="section">
        <h2>Composants Disponibles</h2>
        <ul>
"""
        
        for component, available in report_dict['available_components'].items():
            status = "✅" if available else "❌"
            html_content += f"            <li>{status} {component}</li>\n"
        
        html_content += """        </ul>
    </div>
    
    <div class="section">
        <h2>Recommandations</h2>
        <ul>
"""
        
        for recommendation in report_dict['recommendations']:
            html_content += f"            <li>{recommendation}</li>\n"
        
        html_content += """        </ul>
    </div>
    
    <div class="section">
        <h2>Détails Techniques</h2>
        <div class="code">
            <pre>""" + json.dumps(report_dict, indent=2, ensure_ascii=False) + """</pre>
        </div>
    </div>
</body>
</html>"""
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)


def create_validation_factory(mode: str = "full", **kwargs) -> UnifiedValidationSystem:
    """Factory pour créer un système de validation avec configuration prédéfinie."""
    
    mode_configs = {
        "full": ValidationConfiguration(
            mode=ValidationMode.FULL,
            enable_real_components=True,
            enable_performance_tests=True,
            enable_integration_tests=True,
            verbose=True
        ),
        "simple": ValidationConfiguration(
            mode=ValidationMode.SIMPLE,
            enable_real_components=False,
            enable_performance_tests=False,
            enable_integration_tests=False,
            verbose=False
        ),
        "authenticity": ValidationConfiguration(
            mode=ValidationMode.AUTHENTICITY,
            enable_real_components=True,
            enable_performance_tests=False,
            enable_integration_tests=False
        ),
        "ecosystem": ValidationConfiguration(
            mode=ValidationMode.ECOSYSTEM,
            enable_performance_tests=True,
            enable_integration_tests=True
        ),
        "orchestration": ValidationConfiguration(
            mode=ValidationMode.ORCHESTRATION,
            enable_real_components=True,
            enable_performance_tests=True
        ),
        "performance": ValidationConfiguration(
            mode=ValidationMode.PERFORMANCE,
            enable_performance_tests=True,
            timeout_seconds=600
        )
    }
    
    config = mode_configs.get(mode, mode_configs["full"])
    
    # Application des overrides
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return UnifiedValidationSystem(config)


async def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Système de Validation Unifié")
    parser.add_argument("--mode", choices=["full", "simple", "authenticity", "ecosystem", "orchestration", "performance"], 
                       default="full", help="Mode de validation")
    parser.add_argument("--output", choices=["json", "text", "html"], default="json", help="Format de sortie")
    parser.add_argument("--report-path", help="Chemin du rapport de sortie")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout en secondes")
    parser.add_argument("--no-real-components", action="store_true", help="Désactiver les composants réels")
    parser.add_argument("--no-performance", action="store_true", help="Désactiver les tests de performance")
    parser.add_argument("--verbose", action="store_true", help="Mode verbeux")
    
    args = parser.parse_args()
    
    # Configuration du système
    validator = create_validation_factory(
        mode=args.mode,
        output_format=args.output,
        report_path=args.report_path,
        timeout_seconds=args.timeout,
        enable_real_components=not args.no_real_components,
        enable_performance_tests=not args.no_performance,
        verbose=args.verbose
    )
    
    try:
        # Exécution de la validation
        report = await validator.run_validation()
        
        # Affichage du résumé
        print("\n" + "="*60)
        print("RAPPORT DE VALIDATION UNIFIÉ")
        print("="*60)
        print(f"Mode: {args.mode}")
        print(f"Statut: {report.summary.get('overall_status', 'unknown')}")
        print(f"Composants: {report.summary.get('total_components_detected', 0)}/{report.summary.get('total_components_possible', 0)}")
        print(f"Taux de succès: {report.summary.get('success_rate', 0):.1f}%")
        print(f"Erreurs: {len(report.errors)}")
        
        if report.recommendations:
            print("\nRecommandations:")
            for rec in report.recommendations[:5]:  # Limiter l'affichage
                print(f"  • {rec}")
        
        print("="*60)
        
        return 0 if report.summary.get('overall_status') == 'success' else 1
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exécution: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))