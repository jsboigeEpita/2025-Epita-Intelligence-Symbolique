#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de test pour le système de démonstration éducatif EPITA
============================================================

Tests de validation pour educational_showcase_system.py
- Test des différents modes d'apprentissage (L1 à M2)
- Validation de l'orchestration multi-agents
- Vérification de la capture de conversations
- Test des métriques pédagogiques
- Validation des rapports éducatifs générés

Author: Système de Consolidation Intelligent
Date: 2025-06-10
Version: 1.0.0
"""

import asyncio
import logging
import sys
import tempfile
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Configuration encodage Windows
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Ajouter la racine du projet au sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Imports du système éducatif
from scripts.consolidated.educational_showcase_system import (
    EducationalShowcaseSystem,
    EducationalConfiguration,
    EducationalMode,
    EducationalLanguage,
    EducationalProjectManager,
    EducationalConversationLogger,
    EducationalTextLibrary,
    EducationalMetrics
)

# Configuration du logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger("TestEducationalSystem")

class EducationalSystemTester:
    """Classe de test pour le système éducatif."""
    
    def __init__(self):
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log le résultat d'un test."""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            self.failed_tests += 1
            status = "❌ FAIL"
            
        result = {
            "test_name": test_name,
            "status": status,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        self.test_results.append(result)
        logger.info(f"{status} {test_name}: {details}")
    
    async def test_configuration_creation(self):
        """Test la création des configurations éducatives."""
        try:
            # Test configuration L1 débutant
            config_l1 = EducationalConfiguration(
                mode=EducationalMode.DEBUTANT,
                student_level="L1",
                language=EducationalLanguage.FRANCAIS
            )
            
            assert config_l1.mode == EducationalMode.DEBUTANT
            assert config_l1.student_level == "L1"
            assert config_l1.language == EducationalLanguage.FRANCAIS
            
            # Test configuration de difficulté
            difficulty = config_l1.get_difficulty_config()
            assert "complexity" in difficulty
            assert "concepts" in difficulty
            assert difficulty["complexity"] == 0.3  # L1 niveau
            
            self.log_test_result("Configuration L1 Creation", True, "Configuration L1 créée et validée")
            
            # Test configuration M2 expert
            config_m2 = EducationalConfiguration(
                mode=EducationalMode.EXPERT,
                student_level="M2",
                enable_advanced_metrics=True
            )
            
            assert config_m2.mode == EducationalMode.EXPERT
            assert config_m2.student_level == "M2"
            assert config_m2.enable_advanced_metrics == True
            
            difficulty_m2 = config_m2.get_difficulty_config()
            assert difficulty_m2["complexity"] == 1.0  # M2 niveau max
            
            self.log_test_result("Configuration M2 Creation", True, "Configuration M2 créée et validée")
            
        except Exception as e:
            self.log_test_result("Configuration Creation", False, f"Erreur: {e}")
    
    async def test_conversation_logger(self):
        """Test le logger conversationnel éducatif."""
        try:
            config = EducationalConfiguration(
                mode=EducationalMode.INTERMEDIAIRE,
                student_level="L3",
                max_conversation_length=5
            )
            
            logger_conv = EducationalConversationLogger(config)
            
            # Test d'ajout de messages
            logger_conv.log_agent_message(
                "TestAgent", 
                "Bonjour ! Je teste le système de conversation.",
                "test_phase"
            )
            
            assert len(logger_conv.conversations) == 1
            assert logger_conv.conversations[0].agent == "TestAgent"
            assert logger_conv.conversations[0].message_type == "conversation"
            
            # Test d'ajout d'interaction d'outil
            logger_conv.log_tool_interaction(
                "TestAgent", "test_tool", "param1,param2", "result_ok", 123.5
            )
            
            assert len(logger_conv.conversations) == 2
            assert logger_conv.conversations[1].message_type == "tool_call"
            assert logger_conv.conversations[1].duration_ms == 123.5
            
            # Test du checkpoint éducatif
            logger_conv.log_educational_checkpoint(
                "TestCheckpoint", "Point de test atteint avec succès"
            )
            
            assert len(logger_conv.conversations) == 3
            assert logger_conv.conversations[2].message_type == "checkpoint"
            assert logger_conv.conversations[2].agent == "SystemePedagogique"
            
            self.log_test_result("Conversation Logger", True, f"{len(logger_conv.conversations)} messages capturés")
            
        except Exception as e:
            self.log_test_result("Conversation Logger", False, f"Erreur: {e}")
    
    async def test_text_library(self):
        """Test la bibliothèque de textes éducatifs."""
        try:
            library = EducationalTextLibrary()
            sample_texts = library.get_sample_texts()
            
            # Vérifier la présence des textes pour chaque niveau
            expected_keys = [
                "L1_sophismes_basiques",
                "L2_logique_propositionnelle", 
                "L3_logique_modale",
                "M1_orchestration_complexe"
            ]
            
            for key in expected_keys:
                assert key in sample_texts, f"Texte manquant: {key}"
                
                text_data = sample_texts[key]
                assert "title" in text_data
                assert "content" in text_data
                assert "difficulty" in text_data
                assert len(text_data["content"]) > 50  # Contenu non vide
            
            # Test du contenu spécifique L1
            l1_text = sample_texts["L1_sophismes_basiques"]
            assert "expected_fallacies" in l1_text
            assert len(l1_text["expected_fallacies"]) > 0
            
            # Test du contenu spécifique M1
            m1_text = sample_texts["M1_orchestration_complexe"]
            assert "expected_analysis" in m1_text
            assert "Multi-agents requis" in m1_text["complexity"]
            
            self.log_test_result("Text Library", True, f"{len(sample_texts)} textes éducatifs disponibles")
            
        except Exception as e:
            self.log_test_result("Text Library", False, f"Erreur: {e}")
    
    async def test_educational_metrics(self):
        """Test le système de métriques pédagogiques."""
        try:
            metrics = EducationalMetrics()
            
            # Test des valeurs par défaut
            assert metrics.learning_level == ""
            assert metrics.complexity_score == 0.0
            assert metrics.interaction_count == 0
            assert metrics.cognitive_load == "low"
            assert isinstance(metrics.understanding_checkpoints, list)
            assert isinstance(metrics.time_per_concept, dict)
            
            # Test de mise à jour des métriques
            metrics.learning_level = "L3"
            metrics.complexity_score = 0.7
            metrics.interaction_count = 5
            metrics.cognitive_load = "medium"
            
            # Test d'ajout de checkpoints
            metrics.understanding_checkpoints.append("Sophismes compris")
            metrics.understanding_checkpoints.append("Logique propositionnelle assimilée")
            
            # Test d'ajout de temps par concept
            metrics.time_per_concept["sophismes"] = 45.2
            metrics.time_per_concept["logique_prop"] = 67.8
            
            assert len(metrics.understanding_checkpoints) == 2
            assert len(metrics.time_per_concept) == 2
            assert metrics.complexity_score == 0.7
            
            self.log_test_result("Educational Metrics", True, "Métriques mises à jour et validées")
            
        except Exception as e:
            self.log_test_result("Educational Metrics", False, f"Erreur: {e}")
    
    async def test_project_manager_initialization(self):
        """Test l'initialisation du Project Manager éducatif."""
        try:
            config = EducationalConfiguration(
                mode=EducationalMode.INTERMEDIAIRE,
                student_level="L2",
                enable_conversation_capture=True
            )
            
            pm = EducationalProjectManager(config)
            
            # Vérifier l'initialisation
            assert pm.config == config
            assert isinstance(pm.conversation_logger, EducationalConversationLogger)
            assert isinstance(pm.metrics, EducationalMetrics)
            assert pm.metrics.learning_level == "intermediaire"
            assert isinstance(pm.agents, dict)
            assert len(pm.agents) == 0  # Pas encore initialisés
            
            # Test des propriétés
            assert pm.current_phase == "initialisation"
            assert pm.start_time > 0
            
            self.log_test_result("Project Manager Init", True, "PM initialisé avec configuration L2")
            
        except Exception as e:
            self.log_test_result("Project Manager Init", False, f"Erreur: {e}")
    
    async def test_educational_system_initialization(self):
        """Test l'initialisation du système éducatif complet."""
        try:
            config = EducationalConfiguration(
                mode=EducationalMode.DEBUTANT,
                student_level="L1", 
                enable_real_llm=False,  # Pas de LLM pour les tests
                enable_conversation_capture=True
            )
            
            system = EducationalShowcaseSystem(config)
            
            # Vérifier l'initialisation
            assert system.config == config
            assert isinstance(system.project_manager, EducationalProjectManager)
            assert isinstance(system.text_library, EducationalTextLibrary)
            assert system.llm_service is None  # Pas encore initialisé
            assert system.jvm_initialized == False
            
            self.log_test_result("Educational System Init", True, "Système éducatif initialisé")
            
        except Exception as e:
            self.log_test_result("Educational System Init", False, f"Erreur: {e}")
    
    async def test_text_selection(self):
        """Test la sélection automatique de textes selon le niveau."""
        try:
            # Test pour différents niveaux
            test_configs = [
                ("L1", "L1_sophismes_basiques"),
                ("L2", "L2_logique_propositionnelle"),
                ("L3", "L3_logique_modale"),
                ("M1", "M1_orchestration_complexe"),
                ("M2", "M1_orchestration_complexe")  # M2 utilise le même que M1
            ]
            
            library = EducationalTextLibrary()
            sample_texts = library.get_sample_texts()
            
            for level, expected_key in test_configs:
                config = EducationalConfiguration(student_level=level)
                system = EducationalShowcaseSystem(config)
                
                selected_text = system._select_appropriate_text()
                expected_text = sample_texts[expected_key]["content"].strip()
                
                assert selected_text == expected_text, f"Texte incorrect pour {level}"
            
            self.log_test_result("Text Selection", True, f"{len(test_configs)} niveaux testés")
            
        except Exception as e:
            self.log_test_result("Text Selection", False, f"Erreur: {e}")
    
    async def test_report_generation(self):
        """Test la génération de rapports éducatifs."""
        try:
            config = EducationalConfiguration(
                mode=EducationalMode.INTERMEDIAIRE,
                student_level="L3"
            )
            
            system = EducationalShowcaseSystem(config)
            
            # Données de test pour le rapport
            test_text = "Test de génération de rapport éducatif avec analyse multi-agents."
            test_results = {
                "agents_results": {
                    "informal": {"status": "success", "fallacies": ["test_fallacy"]},
                    "propositional": {"status": "success", "consistency": True, "queries_count": 3}
                },
                "conversations": [
                    {
                        "agent": "TestAgent",
                        "message": "Message de test",
                        "timestamp": datetime.now().isoformat(),
                        "message_type": "conversation"
                    }
                ],
                "session_metrics": {
                    "total_duration_seconds": 45.2,
                    "agents_used": 2,
                    "conversations_captured": 5,
                    "educational_effectiveness": 0.85
                }
            }
            
            # Génération du rapport
            report = system._generate_educational_report(test_text, test_results)
            
            # Vérifications du contenu
            assert "# 🎓 RAPPORT D'ANALYSE ÉDUCATIF EPITA" in report
            assert f"**Niveau étudiant:** {config.student_level}" in report
            assert "## 📚 Texte Analysé" in report
            assert test_text in report
            assert "## 📊 Métriques Pédagogiques" in report
            assert "45.1 secondes" in report
            assert "## 🤖 Analyses des Agents Spécialisés" in report
            assert "## 💬 Conversations Entre Agents" in report
            assert "## 🎯 Recommandations Pédagogiques" in report
            assert "## 🚀 Prochaines Étapes" in report
            
            # Vérifier les recommandations selon l'efficacité
            assert "Excellente session" in report  # efficacité = 85%
            
            self.log_test_result("Report Generation", True, f"Rapport de {len(report)} caractères généré")
            
        except Exception as e:
            self.log_test_result("Report Generation", False, f"Erreur: {e}")
    
    async def test_mock_educational_session(self):
        """Test une session éducative simulée (sans LLM)."""
        try:
            config = EducationalConfiguration(
                mode=EducationalMode.DEBUTANT,
                student_level="L1",
                enable_real_llm=False,
                enable_conversation_capture=True,
                max_conversation_length=10
            )
            
            # Test avec le Project Manager seulement (pas tout le système)
            pm = EducationalProjectManager(config)
            
            # Simuler quelques métriques
            pm.metrics.interaction_count = 3
            pm.metrics.pedagogical_effectiveness = 0.75
            pm.metrics.complexity_score = 0.3  # Niveau L1
            
            # Simuler des conversations
            pm.conversation_logger.log_agent_message(
                "ProjectManager",
                "Début de la session éducative simulée",
                "test"
            )
            
            pm.conversation_logger.log_agent_message(
                "AgentTest",
                "Analyse de test en cours",
                "test"
            )
            
            pm.conversation_logger.log_educational_checkpoint(
                "TestCheckpoint",
                "Point de contrôle de test atteint"
            )
            
            # Vérifications
            assert pm.metrics.interaction_count == 3
            assert pm.metrics.pedagogical_effectiveness == 0.75
            assert len(pm.conversation_logger.conversations) == 3
            
            # Test des types de messages
            messages = pm.conversation_logger.conversations
            assert messages[0].message_type == "conversation"
            assert messages[1].message_type == "conversation" 
            assert messages[2].message_type == "checkpoint"
            
            self.log_test_result("Mock Educational Session", True, "Session simulée exécutée avec succès")
            
        except Exception as e:
            self.log_test_result("Mock Educational Session", False, f"Erreur: {e}")
    
    async def run_all_tests(self):
        """Exécute tous les tests du système éducatif."""
        print("🧪 DÉBUT DES TESTS DU SYSTÈME ÉDUCATIF EPITA")
        print("=" * 60)
        
        # Liste des tests à exécuter
        tests = [
            ("Configuration Creation", self.test_configuration_creation),
            ("Conversation Logger", self.test_conversation_logger),
            ("Text Library", self.test_text_library),
            ("Educational Metrics", self.test_educational_metrics),
            ("Project Manager Init", self.test_project_manager_initialization),
            ("Educational System Init", self.test_educational_system_initialization),
            ("Text Selection", self.test_text_selection),
            ("Report Generation", self.test_report_generation),
            ("Mock Educational Session", self.test_mock_educational_session)
        ]
        
        # Exécution des tests
        for test_name, test_func in tests:
            print(f"\n🔍 Exécution: {test_name}")
            try:
                await test_func()
            except Exception as e:
                self.log_test_result(test_name, False, f"Exception non gérée: {e}")
        
        # Résumé des résultats
        print("\n" + "=" * 60)
        print("📊 RÉSUMÉ DES TESTS")
        print("=" * 60)
        
        print(f"✅ Tests réussis: {self.passed_tests}")
        print(f"❌ Tests échoués: {self.failed_tests}")
        print(f"📈 Total tests: {self.total_tests}")
        
        if self.total_tests > 0:
            success_rate = (self.passed_tests / self.total_tests) * 100
            print(f"🎯 Taux de réussite: {success_rate:.1f}%")
            
            if success_rate >= 90:
                print("🌟 EXCELLENT - Système éducatif pleinement fonctionnel !")
            elif success_rate >= 75:
                print("👍 BON - Système éducatif fonctionnel avec quelques améliorations")
            elif success_rate >= 50:
                print("⚠️ MOYEN - Système partiellement fonctionnel, corrections nécessaires")
            else:
                print("❌ CRITIQUE - Système nécessite des corrections majeures")
        
        # Détails des échecs si présents
        if self.failed_tests > 0:
            print("\n❌ DÉTAILS DES ÉCHECS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test_name']}: {result['details']}")
        
        return self.passed_tests == self.total_tests

def create_test_report(test_results: List[Dict[str, Any]]) -> str:
    """Crée un rapport de test au format markdown."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report_lines = [
        "# 🧪 RAPPORT DE TESTS - Système Éducatif EPITA",
        "",
        f"**Date d'exécution:** {timestamp}",
        f"**Script testé:** educational_showcase_system.py",
        f"**Environnement:** Test automatisé",
        "",
        "---",
        ""
    ]
    
    # Résumé
    total_tests = len(test_results)
    passed_tests = len([r for r in test_results if r["success"]])
    failed_tests = total_tests - passed_tests
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    report_lines.extend([
        "## 📊 Résumé des Tests",
        "",
        f"- **Total des tests:** {total_tests}",
        f"- **Tests réussis:** {passed_tests} ✅",
        f"- **Tests échoués:** {failed_tests} ❌", 
        f"- **Taux de réussite:** {success_rate:.1f}%",
        ""
    ])
    
    # Statut global
    if success_rate >= 90:
        status = "🌟 EXCELLENT"
        message = "Système éducatif pleinement fonctionnel et prêt pour production"
    elif success_rate >= 75:
        status = "👍 BON"
        message = "Système fonctionnel avec quelques améliorations mineures"
    elif success_rate >= 50:
        status = "⚠️ MOYEN"
        message = "Système partiellement fonctionnel, corrections requises"
    else:
        status = "❌ CRITIQUE"
        message = "Système nécessite des corrections majeures avant utilisation"
    
    report_lines.extend([
        f"**Statut global:** {status}",
        f"**Évaluation:** {message}",
        "",
        "---",
        ""
    ])
    
    # Détails des tests
    report_lines.extend([
        "## 🔍 Détails des Tests",
        ""
    ])
    
    for result in test_results:
        status_icon = "✅" if result["success"] else "❌"
        report_lines.extend([
            f"### {status_icon} {result['test_name']}",
            "",
            f"- **Statut:** {result['status']}",
            f"- **Détails:** {result['details']}",
            f"- **Horodatage:** {result['timestamp']}",
            ""
        ])
    
    # Recommandations
    report_lines.extend([
        "---",
        "",
        "## 🎯 Recommandations",
        ""
    ])
    
    if failed_tests == 0:
        report_lines.extend([
            "✅ **Tous les tests sont passés avec succès !**",
            "",
            "Le système éducatif est prêt pour:",
            "- Déploiement en environnement de production",
            "- Utilisation par les étudiants EPITA",
            "- Démonstrations pédagogiques complètes",
            ""
        ])
    else:
        report_lines.extend([
            "⚠️ **Corrections nécessaires:**",
            ""
        ])
        
        for result in test_results:
            if not result["success"]:
                report_lines.extend([
                    f"- **{result['test_name']}:** {result['details']}",
                ])
        
        report_lines.extend([
            "",
            "🔧 **Actions recommandées:**",
            "- Corriger les tests en échec avant déploiement",
            "- Retester après corrections",
            "- Valider avec des données réelles",
            ""
        ])
    
    report_lines.extend([
        "---",
        "",
        f"*Rapport généré automatiquement le {timestamp}*"
    ])
    
    return "\n".join(report_lines)

async def main():
    """Point d'entrée principal des tests."""
    print("🚀 Lancement des tests du système éducatif EPITA")
    
    # Création du testeur
    tester = EducationalSystemTester()
    
    # Exécution de tous les tests
    all_passed = await tester.run_all_tests()
    
    # Génération du rapport de test
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_content = create_test_report(tester.test_results)
    
    # Sauvegarde du rapport
    reports_dir = project_root / "reports" / "educational"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = reports_dir / f"educational_system_tests_{timestamp}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    # Sauvegarde des données JSON
    json_file = reports_dir / f"educational_system_tests_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(tester.test_results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n📄 Rapport de test sauvegardé: {report_file}")
    print(f"📊 Données JSON sauvegardées: {json_file}")
    
    if all_passed:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS - Système prêt pour utilisation !")
        return 0
    else:
        print(f"\n⚠️ {tester.failed_tests} test(s) échoué(s) - Corrections nécessaires")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)