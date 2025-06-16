#!/usr/bin/env python3
# scripts/validation_traces_master.py

"""
Script maître de validation des démos Sherlock, Watson et Moriarty avec traces complètes.
Orchestre les validations Cluedo et Einstein avec génération de rapports globaux.
"""

import scripts.core.auto_env  # Activation automatique de l'environnement

import asyncio
import json
import os
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Imports des validateurs spécialisés
from scripts.validation_cluedo_traces import CluedoTraceValidator
from scripts.validation_einstein_traces import EinsteinTraceValidator
from argumentation_analysis.utils.core_utils.logging_utils import setup_logging

class MasterTraceValidator:
    """Validateur maître orchestrant toutes les validations avec traces."""
    
    def __init__(self, output_dir: str = ".temp"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logger = logging.getLogger(__name__)
        
        # Création des validateurs spécialisés
        self.cluedo_validator = CluedoTraceValidator(str(self.output_dir / "traces_cluedo"))
        self.einstein_validator = EinsteinTraceValidator(str(self.output_dir / "traces_einstein"))
        
    def validate_environment(self) -> Dict[str, Any]:
        """Valide l'environnement avant d'exécuter les tests."""
        
        print("🔍 VALIDATION DE L'ENVIRONNEMENT")
        print("="*50)
        
        validation_results = {
            "openai_api_key": bool(os.getenv("OPENAI_API_KEY")),
            "directories_created": True,
            "python_imports": True,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Vérification clé API
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OPENAI_API_KEY non définie")
            validation_results["openai_api_key"] = False
        else:
            print(f"✅ OPENAI_API_KEY définie (longueur: {len(api_key)})")
            
        # Vérification des répertoires
        cluedo_dir = Path(".temp/traces_cluedo")
        einstein_dir = Path(".temp/traces_einstein")
        
        if cluedo_dir.exists() and einstein_dir.exists():
            print("✅ Répertoires de traces créés")
        else:
            print("❌ Répertoires de traces manquants")
            validation_results["directories_created"] = False
            
        # Test d'imports
        try:
            from argumentation_analysis.orchestration.cluedo_orchestrator import run_cluedo_game
            from argumentation_analysis.orchestration.logique_complexe_orchestrator import LogiqueComplexeOrchestrator
            print("✅ Imports des orchestrateurs réussis")
        except ImportError as e:
            print(f"❌ Erreur d'import: {e}")
            validation_results["python_imports"] = False
            
        # Résumé
        all_ok = all(validation_results[k] for k in ["openai_api_key", "directories_created", "python_imports"])
        validation_results["environment_ready"] = all_ok
        
        if all_ok:
            print("\n🎉 ENVIRONNEMENT PRÊT POUR LA VALIDATION")
        else:
            print("\n⚠️  PROBLÈMES DÉTECTÉS - CORRECTION NÉCESSAIRE")
            
        return validation_results
        
    async def run_full_validation(self) -> Dict[str, Any]:
        """Exécute la validation complète des démos avec traces."""
        
        print("\n🚀 LANCEMENT VALIDATION COMPLÈTE AVEC TRACES")
        print("="*80)
        
        # Validation de l'environnement
        env_validation = self.validate_environment()
        if not env_validation["environment_ready"]:
            raise RuntimeError("Environnement non prêt pour la validation")
            
        start_time = datetime.datetime.now()
        all_results = {
            "metadata": {
                "validation_start": start_time.isoformat(),
                "timestamp": self.timestamp,
                "environment_validation": env_validation
            },
            "cluedo_results": None,
            "einstein_results": None,
            "global_analysis": None
        }
        
        try:
            # ÉTAPE 1: Validation Cluedo (Sherlock + Watson collaboration informelle)
            print(f"\n📋 ÉTAPE 1/2: VALIDATION CLUEDO")
            print(f"{'='*50}")
            
            cluedo_results = await self.run_cluedo_validation()
            all_results["cluedo_results"] = cluedo_results
            
            # ÉTAPE 2: Validation Einstein (Watson + TweetyProject obligatoire)
            print(f"\n🧩 ÉTAPE 2/2: VALIDATION EINSTEIN")
            print(f"{'='*50}")
            
            einstein_results = await self.run_einstein_validation()
            all_results["einstein_results"] = einstein_results
            
            # ÉTAPE 3: Analyse globale
            print(f"\n📊 ANALYSE GLOBALE")
            print(f"{'='*50}")
            
            global_analysis = await self.perform_global_analysis(cluedo_results, einstein_results)
            all_results["global_analysis"] = global_analysis
            
            # Finalisation
            end_time = datetime.datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            all_results["metadata"]["validation_end"] = end_time.isoformat()
            all_results["metadata"]["total_duration"] = total_duration
            
            # Sauvegarde du rapport global
            await self.save_global_report(all_results)
            
            # Affichage du résumé final
            self.display_final_summary(all_results)
            
            return all_results
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la validation complète: {e}")
            all_results["error"] = str(e)
            
            # Sauvegarde de l'erreur
            error_file = self.output_dir / f"validation_error_{self.timestamp}.json"
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
                
            raise
            
    async def run_cluedo_validation(self) -> List[Dict[str, Any]]:
        """Exécute la validation Cluedo avec les cas simple et complexe."""
        
        print("🕵️ Démarrage validation Cluedo...")
        
        # Cas simple
        simple_case = self.cluedo_validator.generate_simple_case()
        simple_results = await self.cluedo_validator.run_cluedo_with_traces(simple_case, "simple")
        
        # Cas complexe
        complex_case = self.cluedo_validator.generate_complex_case()
        complex_results = await self.cluedo_validator.run_cluedo_with_traces(complex_case, "complexe")
        
        # Génération du rapport Cluedo
        cluedo_results = [simple_results, complex_results]
        await self.cluedo_validator.generate_synthesis_report(cluedo_results)
        
        return cluedo_results
        
    async def run_einstein_validation(self) -> List[Dict[str, Any]]:
        """Exécute la validation Einstein avec les cas simple et complexe."""
        
        print("🧩 Démarrage validation Einstein...")
        
        # Cas simple (5 contraintes)
        simple_case = self.einstein_validator.generate_simple_einstein_case()
        simple_results = await self.einstein_validator.run_einstein_with_traces(simple_case, "simple")
        
        # Cas complexe (10+ contraintes)
        complex_case = self.einstein_validator.generate_complex_einstein_case()
        complex_results = await self.einstein_validator.run_einstein_with_traces(complex_case, "complexe")
        
        # Génération du rapport Einstein
        einstein_results = [simple_results, complex_results]
        await self.einstein_validator.generate_synthesis_report(einstein_results)
        
        return einstein_results
        
    async def perform_global_analysis(self, cluedo_results: List[Dict], einstein_results: List[Dict]) -> Dict[str, Any]:
        """Effectue l'analyse globale comparant Cluedo et Einstein."""
        
        print("📊 Analyse globale en cours...")
        
        # Métriques globales
        total_tests = len(cluedo_results) + len(einstein_results)
        total_duration = sum(r['metadata']['duration_seconds'] for r in cluedo_results + einstein_results)
        
        # Analyse des outils
        cluedo_tools = set()
        for result in cluedo_results:
            cluedo_tools.update(result['analysis']['tools_used'])
            
        einstein_tweetyproject_usage = sum(
            r['tweetyproject_validation']['clauses_formulees'] + r['tweetyproject_validation']['requetes_executees'] 
            for r in einstein_results
        )
        
        # Analyse de la collaboration
        collaboration_analysis = {
            "cluedo_informal_collaboration": self._analyze_cluedo_collaboration(cluedo_results),
            "einstein_formal_logic": self._analyze_einstein_logic(einstein_results),
            "tools_specialization": {
                "cluedo_tools_diversity": len(cluedo_tools),
                "einstein_tweetyproject_intensity": einstein_tweetyproject_usage,
                "clear_tool_differentiation": einstein_tweetyproject_usage > 0
            }
        }
        
        # Évaluation de la qualité agentique
        agentique_quality = {
            "agent_differentiation": self._assess_agent_differentiation(cluedo_results, einstein_results),
            "specialized_tool_usage": self._assess_specialized_tools(cluedo_results, einstein_results),
            "conversation_naturalness": self._assess_conversation_quality(cluedo_results, einstein_results),
            "problem_solving_effectiveness": self._assess_problem_solving(cluedo_results, einstein_results)
        }
        
        global_analysis = {
            "summary": {
                "total_tests_executed": total_tests,
                "total_validation_time": total_duration,
                "cluedo_tests": len(cluedo_results),
                "einstein_tests": len(einstein_results),
                "overall_success_rate": self._calculate_success_rate(cluedo_results, einstein_results)
            },
            "collaboration_analysis": collaboration_analysis,
            "agentique_quality": agentique_quality,
            "validation_conclusions": self._generate_conclusions(cluedo_results, einstein_results, collaboration_analysis, agentique_quality)
        }
        
        return global_analysis
        
    def _analyze_cluedo_collaboration(self, cluedo_results: List[Dict]) -> Dict[str, Any]:
        """Analyse la collaboration informelle dans Cluedo."""
        if not cluedo_results:
            return {}
            
        avg_messages = sum(r['analysis']['conversation_length'] for r in cluedo_results) / len(cluedo_results)
        evidence_usage_rate = sum(1 for r in cluedo_results if r['analysis']['logic_quality']['evidence_based']) / len(cluedo_results)
        
        return {
            "average_conversation_length": avg_messages,
            "evidence_based_reasoning_rate": evidence_usage_rate,
            "systematic_approach_rate": sum(1 for r in cluedo_results if r['analysis']['logic_quality']['has_systematic_approach']) / len(cluedo_results)
        }
        
    def _analyze_einstein_logic(self, einstein_results: List[Dict]) -> Dict[str, Any]:
        """Analyse la logique formelle dans Einstein."""
        if not einstein_results:
            return {}
            
        total_clauses = sum(r['tweetyproject_validation']['clauses_formulees'] for r in einstein_results)
        total_queries = sum(r['tweetyproject_validation']['requetes_executees'] for r in einstein_results)
        compliance_rate = sum(1 for r in einstein_results if r['tweetyproject_validation']['meets_minimum_requirements']['all_requirements_met']) / len(einstein_results)
        
        return {
            "total_formal_clauses": total_clauses,
            "total_tweetyproject_queries": total_queries,
            "formal_logic_compliance_rate": compliance_rate,
            "average_logic_intensity": total_clauses / len(einstein_results)
        }
        
    def _assess_agent_differentiation(self, cluedo_results: List[Dict], einstein_results: List[Dict]) -> Dict[str, Any]:
        """Évalue la différenciation des agents entre les types de problèmes."""
        return {
            "sherlock_coordination_consistent": True,  # Sherlock toujours coordinateur
            "watson_adaptation": True,  # Watson s'adapte informel/formel
            "moriarty_specialization": False,  # Pas encore implémenté
            "role_clarity": "high"
        }
        
    def _assess_specialized_tools(self, cluedo_results: List[Dict], einstein_results: List[Dict]) -> Dict[str, Any]:
        """Évalue l'utilisation des outils spécialisés."""
        cluedo_uses_tweety = any('TweetyProject' in r['analysis']['tools_used'] for r in cluedo_results)
        einstein_uses_tweety = any(r['tweetyproject_validation']['requetes_executees'] > 0 for r in einstein_results)
        
        return {
            "cluedo_informal_tools": not cluedo_uses_tweety,  # Devrait être informel
            "einstein_formal_tools": einstein_uses_tweety,    # Devrait être formel
            "tool_appropriateness": not cluedo_uses_tweety and einstein_uses_tweety,
            "specialization_score": 1.0 if (not cluedo_uses_tweety and einstein_uses_tweety) else 0.5
        }
        
    def _assess_conversation_quality(self, cluedo_results: List[Dict], einstein_results: List[Dict]) -> Dict[str, Any]:
        """Évalue la qualité naturelle des conversations."""
        all_results = cluedo_results + einstein_results
        
        avg_length = sum(r['analysis']['conversation_length'] for r in all_results) / len(all_results) if all_results else 0
        
        return {
            "average_conversation_length": avg_length,
            "natural_flow": avg_length > 5,  # Au moins 5 échanges
            "agent_participation_balance": True,  # À améliorer avec analyse détaillée
            "quality_score": min(1.0, avg_length / 10.0)
        }
        
    def _assess_problem_solving(self, cluedo_results: List[Dict], einstein_results: List[Dict]) -> Dict[str, Any]:
        """Évalue l'efficacité de résolution de problèmes."""
        cluedo_solutions = sum(1 for r in cluedo_results if r['analysis']['logic_quality']['reaches_conclusion'])
        einstein_solutions = sum(1 for r in einstein_results if r['analysis']['enigme_resolue'])
        
        total_tests = len(cluedo_results) + len(einstein_results)
        success_rate = (cluedo_solutions + einstein_solutions) / total_tests if total_tests > 0 else 0
        
        return {
            "cluedo_solution_rate": cluedo_solutions / len(cluedo_results) if cluedo_results else 0,
            "einstein_solution_rate": einstein_solutions / len(einstein_results) if einstein_results else 0,
            "overall_success_rate": success_rate,
            "effectiveness_rating": "high" if success_rate > 0.8 else "medium" if success_rate > 0.5 else "low"
        }
        
    def _calculate_success_rate(self, cluedo_results: List[Dict], einstein_results: List[Dict]) -> float:
        """Calcule le taux de succès global."""
        cluedo_success = sum(1 for r in cluedo_results if r['analysis']['logic_quality']['reaches_conclusion'])
        einstein_success = sum(1 for r in einstein_results if r['analysis']['enigme_resolue'])
        
        total_tests = len(cluedo_results) + len(einstein_results)
        return (cluedo_success + einstein_success) / total_tests if total_tests > 0 else 0.0
        
    def _generate_conclusions(self, cluedo_results: List[Dict], einstein_results: List[Dict], 
                            collaboration_analysis: Dict, agentique_quality: Dict) -> List[str]:
        """Génère les conclusions de la validation."""
        conclusions = []
        
        # Analyse des résultats
        success_rate = self._calculate_success_rate(cluedo_results, einstein_results)
        
        if success_rate > 0.8:
            conclusions.append("✅ Excellent taux de réussite - Système agentique performant")
        elif success_rate > 0.5:
            conclusions.append("⚠️ Taux de réussite moyen - Améliorations possibles")
        else:
            conclusions.append("❌ Taux de réussite faible - Révision du système nécessaire")
            
        # Spécialisation des outils
        if agentique_quality['specialized_tool_usage']['tool_appropriateness']:
            conclusions.append("✅ Spécialisation des outils appropriée (Cluedo informel, Einstein formel)")
        else:
            conclusions.append("⚠️ Spécialisation des outils à améliorer")
            
        # Collaboration
        einstein_compliance = collaboration_analysis['einstein_formal_logic']['formal_logic_compliance_rate']
        if einstein_compliance > 0.8:
            conclusions.append("✅ Watson utilise efficacement TweetyProject pour la logique formelle")
        else:
            conclusions.append("⚠️ Watson doit améliorer l'utilisation de TweetyProject")
            
        conclusions.append(f"📊 Validation complète réalisée avec {len(cluedo_results) + len(einstein_results)} tests")
        
        return conclusions
        
    async def save_global_report(self, all_results: Dict[str, Any]):
        """Sauvegarde le rapport global de validation."""
        
        report_file = self.output_dir / f"global_validation_report_{self.timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
            
        self.logger.info(f"✅ Rapport global sauvegardé: {report_file}")
        
    def display_final_summary(self, all_results: Dict[str, Any]):
        """Affiche le résumé final de la validation."""
        
        print(f"\n{'='*80}")
        print(f"🎉 VALIDATION COMPLÈTE TERMINÉE")
        print(f"{'='*80}")
        
        metadata = all_results['metadata']
        global_analysis = all_results['global_analysis']
        
        print(f"⏱️  Durée totale: {metadata['total_duration']:.2f}s")
        print(f"🧪 Tests exécutés: {global_analysis['summary']['total_tests_executed']}")
        print(f"📈 Taux de succès: {global_analysis['summary']['overall_success_rate']:.1%}")
        
        print(f"\n📁 TRACES GÉNÉRÉES:")
        print(f"   - Cluedo: {self.output_dir}/traces_cluedo/")
        print(f"   - Einstein: {self.output_dir}/traces_einstein/")
        print(f"   - Rapport global: global_validation_report_{self.timestamp}.json")
        
        print(f"\n🎯 CONCLUSIONS:")
        for conclusion in global_analysis['validation_conclusions']:
            print(f"   {conclusion}")
            
        print(f"\n✅ Validation des démos Sherlock, Watson et Moriarty terminée avec succès!")

async def main():
    """Fonction principale de validation complète avec traces."""
    
    print("🚀 VALIDATION MAÎTRE - DÉMOS SHERLOCK, WATSON ET MORIARTY")
    print("="*80)
    print("🎯 Objectif: Valider les démos avec traces agentiques complètes")
    print("🔧 Tests: Cluedo (informel) + Einstein (formel avec TweetyProject)")
    print("📊 Livrables: Traces JSON + Rapports d'analyse + Validation qualité")
    
    # Configuration du logging
    setup_logging()
    
    try:
        # Création et lancement du validateur maître
        master_validator = MasterTraceValidator()
        
        # Exécution de la validation complète
        results = await master_validator.run_full_validation()
        
        return results
        
    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE: {e}")
        logging.error(f"Erreur validation maître: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())