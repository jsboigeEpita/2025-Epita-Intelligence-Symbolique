#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de détection et élimination des mocks pour garantir l'authenticité 100%.

Ce script identifie tous les mocks présents dans le système et propose
des remplacements par des implémentations authentiques pour assurer
la traçabilité complète des analyses.

Objectifs :
- Détecter tous les mocks (classes, fonctions, services)
- Valider l'authenticité des services LLM
- Vérifier l'utilisation de Tweety JAR réel
- Contrôler la taxonomie complète (1000 nœuds)
- Générer un rapport d'authenticité
"""

import os
import re
import ast
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("MockElimination")

@dataclass
class MockDetection:
    """Résultat de détection d'un mock."""
    file_path: str
    line_number: int
    mock_type: str  # 'class', 'function', 'import', 'variable'
    mock_name: str
    context: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    replacement_suggestion: str = ""

@dataclass
class AuthenticityReport:
    """Rapport complet d'authenticité du système."""
    total_mocks_detected: int = 0
    critical_mocks: List[MockDetection] = field(default_factory=list)
    high_priority_mocks: List[MockDetection] = field(default_factory=list)
    medium_priority_mocks: List[MockDetection] = field(default_factory=list)
    low_priority_mocks: List[MockDetection] = field(default_factory=list)
    authenticity_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    validated_components: List[str] = field(default_factory=list)

class MockDetector:
    """Détecteur de mocks dans le code source."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.mock_patterns = {
            'class_mocks': [
                r'class\s+(\w*Mock\w*)',
                r'class\s+(\w*Fake\w*)',
                r'class\s+(\w*Stub\w*)',
                r'class\s+(\w*Dummy\w*)',
                r'class\s+(\w*Simulated\w*)',
            ],
            'function_mocks': [
                r'def\s+(\w*mock\w*)',
                r'def\s+(\w*fake\w*)',
                r'def\s+(\w*stub\w*)',
                r'def\s+(\w*simulate\w*)',
            ],
            'import_mocks': [
                r'from\s+\w*\.?\w*\s+import\s+.*Mock',
                r'import\s+mock',
                r'from\s+unittest\s+import\s+mock',
                r'from\s+unittest\.mock\s+import',
            ],
            'variable_mocks': [
                r'(\w*mock\w*)\s*=',
                r'(\w*fake\w*)\s*=',
                r'(\w*stub\w*)\s*=',
            ]
        }
        
        # Patterns critiques pour services authentiques
        self.critical_patterns = {
            'llm_service_mocks': [
                r'MockLLMService',
                r'FakeLLMService',
                r'SimulatedLLMService',
                r'mock_llm',
                r'fake_llm',
            ],
            'tweety_mocks': [
                r'MockTweety',
                r'FakeTweety',
                r'SimulatedTweety',
                r'mock_tweety',
                r'fake_tweety',
            ],
            'taxonomy_mocks': [
                r'MockTaxonomy',
                r'FakeTaxonomy',
                r'mock_taxonomy',
                r'small_taxonomy',
                r'test_taxonomy',
            ]
        }

    def scan_project(self) -> AuthenticityReport:
        """
        Scanne tout le projet pour détecter les mocks.
        
        Returns:
            AuthenticityReport: Rapport complet d'authenticité
        """
        logger.info(f"🔍 Début du scan d'authenticité pour {self.project_root}")
        
        report = AuthenticityReport()
        python_files = self._find_python_files()
        
        logger.info(f"📁 {len(python_files)} fichiers Python à analyser")
        
        for file_path in python_files:
            file_mocks = self._scan_file(file_path)
            self._categorize_mocks(file_mocks, report)
        
        # Calcul du score d'authenticité
        report.authenticity_score = self._calculate_authenticity_score(report)
        
        # Génération des recommandations
        report.recommendations = self._generate_recommendations(report)
        
        logger.info(f"✅ Scan terminé - Score d'authenticité: {report.authenticity_score:.1%}")
        
        return report

    def _find_python_files(self) -> List[Path]:
        """Trouve tous les fichiers Python du projet."""
        python_files = []
        for pattern in ['**/*.py']:
            python_files.extend(self.project_root.glob(pattern))
        
        # Exclusion des fichiers de test et de cache
        excluded_patterns = [
            '**/__pycache__/**',
            '**/test_*',
            '**/tests/**',
            '**/.pytest_cache/**',
            '**/venv/**',
            '**/env/**',
        ]
        
        filtered_files = []
        for file_path in python_files:
            if not any(file_path.match(pattern) for pattern in excluded_patterns):
                filtered_files.append(file_path)
        
        return filtered_files

    def _scan_file(self, file_path: Path) -> List[MockDetection]:
        """
        Scanne un fichier pour détecter les mocks.
        
        Args:
            file_path: Chemin du fichier à scanner
            
        Returns:
            List[MockDetection]: Liste des mocks détectés
        """
        mocks = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Scan par patterns regex
            mocks.extend(self._scan_with_patterns(file_path, lines))
            
            # Scan AST pour une détection plus précise
            mocks.extend(self._scan_with_ast(file_path, content))
            
        except Exception as e:
            logger.warning(f"⚠️ Erreur lors du scan de {file_path}: {e}")
        
        return mocks

    def _scan_with_patterns(self, file_path: Path, lines: List[str]) -> List[MockDetection]:
        """Scan par patterns regex."""
        mocks = []
        
        for line_num, line in enumerate(lines, 1):
            # Scan des patterns généraux
            for category, patterns in self.mock_patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        mock_name = match.group(1) if match.groups() else match.group(0)
                        mocks.append(MockDetection(
                            file_path=str(file_path),
                            line_number=line_num,
                            mock_type=category,
                            mock_name=mock_name,
                            context=line.strip(),
                            severity='medium',
                            replacement_suggestion=self._suggest_replacement(mock_name, category)
                        ))
            
            # Scan des patterns critiques
            for category, patterns in self.critical_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        mocks.append(MockDetection(
                            file_path=str(file_path),
                            line_number=line_num,
                            mock_type=category,
                            mock_name=pattern,
                            context=line.strip(),
                            severity='critical',
                            replacement_suggestion=self._suggest_critical_replacement(pattern, category)
                        ))
        
        return mocks

    def _scan_with_ast(self, file_path: Path, content: str) -> List[MockDetection]:
        """Scan avec analyse AST pour détection avancée."""
        mocks = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if self._is_mock_class(node.name):
                        mocks.append(MockDetection(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            mock_type='class',
                            mock_name=node.name,
                            context=f"class {node.name}",
                            severity=self._determine_severity(node.name),
                            replacement_suggestion=self._suggest_replacement(node.name, 'class')
                        ))
                
                elif isinstance(node, ast.FunctionDef):
                    if self._is_mock_function(node.name):
                        mocks.append(MockDetection(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            mock_type='function',
                            mock_name=node.name,
                            context=f"def {node.name}",
                            severity=self._determine_severity(node.name),
                            replacement_suggestion=self._suggest_replacement(node.name, 'function')
                        ))
        
        except SyntaxError:
            logger.warning(f"⚠️ Erreur de syntaxe dans {file_path} - scan AST ignoré")
        
        return mocks

    def _is_mock_class(self, name: str) -> bool:
        """Détermine si un nom de classe est un mock."""
        mock_indicators = ['mock', 'fake', 'stub', 'dummy', 'simulated', 'test']
        return any(indicator in name.lower() for indicator in mock_indicators)

    def _is_mock_function(self, name: str) -> bool:
        """Détermine si un nom de fonction est un mock."""
        mock_indicators = ['mock', 'fake', 'stub', 'dummy', 'simulate', 'test']
        return any(indicator in name.lower() for indicator in mock_indicators)

    def _determine_severity(self, name: str) -> str:
        """Détermine la sévérité d'un mock basée sur son nom."""
        critical_keywords = ['llm', 'tweety', 'gpt', 'openai', 'taxonomy']
        high_keywords = ['agent', 'service', 'orchestrat']
        
        name_lower = name.lower()
        
        if any(keyword in name_lower for keyword in critical_keywords):
            return 'critical'
        elif any(keyword in name_lower for keyword in high_keywords):
            return 'high'
        else:
            return 'medium'

    def _suggest_replacement(self, mock_name: str, mock_type: str) -> str:
        """Suggère un remplacement pour un mock."""
        suggestions = {
            'MockLLMService': 'RealLLMService avec GPT-4o-mini',
            'FakeTweetyBridge': 'TweetyBridge avec JAR authentique',
            'MockTaxonomy': 'FullTaxonomy avec 1000 nœuds',
            'mock_agent': 'Agent authentique avec configuration réelle',
        }
        
        return suggestions.get(mock_name, f"Remplacer par implémentation réelle de {mock_name}")

    def _suggest_critical_replacement(self, pattern: str, category: str) -> str:
        """Suggère un remplacement pour un mock critique."""
        replacements = {
            'llm_service_mocks': 'Utiliser create_llm_service() avec API OpenAI réelle',
            'tweety_mocks': 'Utiliser TweetyBridge avec tweety-full.jar',
            'taxonomy_mocks': 'Charger la taxonomie complète 1000 nœuds',
        }
        
        return replacements.get(category, "Remplacer par service authentique")

    def _categorize_mocks(self, file_mocks: List[MockDetection], report: AuthenticityReport):
        """Catégorise les mocks détectés dans le rapport."""
        for mock in file_mocks:
            report.total_mocks_detected += 1
            
            if mock.severity == 'critical':
                report.critical_mocks.append(mock)
            elif mock.severity == 'high':
                report.high_priority_mocks.append(mock)
            elif mock.severity == 'medium':
                report.medium_priority_mocks.append(mock)
            else:
                report.low_priority_mocks.append(mock)

    def _calculate_authenticity_score(self, report: AuthenticityReport) -> float:
        """
        Calcule le score d'authenticité basé sur les mocks détectés.
        
        Args:
            report: Rapport d'authenticité
            
        Returns:
            float: Score entre 0.0 et 1.0
        """
        if report.total_mocks_detected == 0:
            return 1.0
        
        # Pondération des mocks par sévérité
        critical_weight = 10
        high_weight = 5
        medium_weight = 2
        low_weight = 1
        
        total_penalty = (
            len(report.critical_mocks) * critical_weight +
            len(report.high_priority_mocks) * high_weight +
            len(report.medium_priority_mocks) * medium_weight +
            len(report.low_priority_mocks) * low_weight
        )
        
        # Score basé sur la pénalité
        max_acceptable_penalty = 100  # Seuil arbitraire
        score = max(0.0, 1.0 - (total_penalty / max_acceptable_penalty))
        
        return score

    def _generate_recommendations(self, report: AuthenticityReport) -> List[str]:
        """Génère des recommandations basées sur le rapport."""
        recommendations = []
        
        if report.critical_mocks:
            recommendations.append("🚨 CRITIQUE: Éliminer immédiatement les mocks de services essentiels")
            recommendations.append("- Remplacer MockLLMService par service OpenAI réel")
            recommendations.append("- Utiliser TweetyBridge authentique avec JAR complet")
            recommendations.append("- Charger la taxonomie complète (1000 nœuds)")
        
        if report.high_priority_mocks:
            recommendations.append("⚠️ HAUTE PRIORITÉ: Remplacer les mocks d'agents")
            recommendations.append("- Utiliser des agents authentiques avec configuration réelle")
        
        if report.medium_priority_mocks:
            recommendations.append("📋 MOYENNE PRIORITÉ: Nettoyer les mocks utilitaires")
        
        if report.authenticity_score < 0.8:
            recommendations.append("🎯 OBJECTIF: Atteindre un score d'authenticité > 80%")
        
        recommendations.append("✅ VALIDATION: Tester chaque remplacement avec traces complètes")
        
        return recommendations


class MockEliminator:
    """Élimine automatiquement les mocks détectés."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "backups" / "mock_elimination"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def eliminate_mocks(self, report: AuthenticityReport) -> Dict[str, Any]:
        """
        Élimine automatiquement les mocks lorsque possible.
        
        Args:
            report: Rapport d'authenticité avec mocks détectés
            
        Returns:
            Dict[str, Any]: Résultats de l'élimination
        """
        logger.info("🧹 Début de l'élimination automatique des mocks")
        
        results = {
            'eliminated_mocks': 0,
            'manual_intervention_required': [],
            'errors': [],
            'backups_created': []
        }
        
        # Traiter les mocks par priorité
        all_mocks = (
            report.critical_mocks + 
            report.high_priority_mocks + 
            report.medium_priority_mocks + 
            report.low_priority_mocks
        )
        
        for mock in all_mocks:
            try:
                if self._can_auto_eliminate(mock):
                    self._backup_file(mock.file_path)
                    success = self._eliminate_mock(mock)
                    if success:
                        results['eliminated_mocks'] += 1
                    else:
                        results['manual_intervention_required'].append(mock)
                else:
                    results['manual_intervention_required'].append(mock)
                    
            except Exception as e:
                logger.error(f"❌ Erreur élimination {mock.mock_name}: {e}")
                results['errors'].append(f"{mock.mock_name}: {str(e)}")
        
        logger.info(f"✅ Élimination terminée - {results['eliminated_mocks']} mocks éliminés")
        
        return results

    def _can_auto_eliminate(self, mock: MockDetection) -> bool:
        """Détermine si un mock peut être éliminé automatiquement."""
        # Pour l'instant, élimination conservatrice
        safe_patterns = [
            'test_mock',
            'example_mock',
            'demo_mock'
        ]
        
        return any(pattern in mock.mock_name.lower() for pattern in safe_patterns)

    def _backup_file(self, file_path: str):
        """Crée une sauvegarde du fichier avant modification."""
        import shutil
        from datetime import datetime
        
        source = Path(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{source.name}.{timestamp}.backup"
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(source, backup_path)
        logger.info(f"💾 Sauvegarde créée: {backup_path}")

    def _eliminate_mock(self, mock: MockDetection) -> bool:
        """Élimine un mock spécifique."""
        # Implémentation conservatrice - juste commentaire pour l'instant
        try:
            with open(mock.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Commenter la ligne du mock
            line_index = mock.line_number - 1
            if line_index < len(lines):
                lines[line_index] = f"# MOCK ELIMINATED: {lines[line_index]}"
                
                with open(mock.file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
                logger.info(f"✅ Mock éliminé: {mock.mock_name} dans {mock.file_path}")
                return True
        
        except Exception as e:
            logger.error(f"❌ Erreur élimination {mock.mock_name}: {e}")
        
        return False


def generate_authenticity_report(report: AuthenticityReport, output_path: str):
    """Génère un rapport d'authenticité détaillé."""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Rapport d'Authenticité du Système\n\n")
        f.write(f"**Score d'authenticité: {report.authenticity_score:.1%}**\n\n")
        f.write(f"**Mocks détectés: {report.total_mocks_detected}**\n\n")
        
        f.write("## Résumé par Sévérité\n\n")
        f.write(f"- 🚨 Critiques: {len(report.critical_mocks)}\n")
        f.write(f"- ⚠️ Haute priorité: {len(report.high_priority_mocks)}\n")
        f.write(f"- 📋 Moyenne priorité: {len(report.medium_priority_mocks)}\n")
        f.write(f"- ℹ️ Basse priorité: {len(report.low_priority_mocks)}\n\n")
        
        # Détail des mocks critiques
        if report.critical_mocks:
            f.write("## 🚨 Mocks Critiques (Élimination Urgente)\n\n")
            for mock in report.critical_mocks:
                f.write(f"### {mock.mock_name}\n")
                f.write(f"- **Fichier**: `{mock.file_path}`\n")
                f.write(f"- **Ligne**: {mock.line_number}\n")
                f.write(f"- **Type**: {mock.mock_type}\n")
                f.write(f"- **Contexte**: `{mock.context}`\n")
                f.write(f"- **Remplacement suggéré**: {mock.replacement_suggestion}\n\n")
        
        # Recommandations
        f.write("## 📋 Recommandations\n\n")
        for i, rec in enumerate(report.recommendations, 1):
            f.write(f"{i}. {rec}\n")
        
        f.write("\n## 🎯 Objectif d'Authenticité 100%\n\n")
        f.write("Pour garantir l'authenticité complète :\n")
        f.write("1. Éliminer tous les mocks critiques\n")
        f.write("2. Utiliser GPT-4o-mini réel exclusivement\n")
        f.write("3. Charger TweetyProject JAR authentique\n")
        f.write("4. Utiliser taxonomie 1000 nœuds complète\n")
        f.write("5. Valider toutes les traces générées\n")


async def main():
    """Fonction principale de détection et élimination des mocks."""
    project_root = Path(__file__).parent.parent.parent
    
    logger.info("🚀 Démarrage de l'audit d'authenticité")
    
    # 1. Détection des mocks
    detector = MockDetector(str(project_root))
    report = detector.scan_project()
    
    # 2. Génération du rapport
    report_path = project_root / "reports" / "authenticity_report.md"
    report_path.parent.mkdir(exist_ok=True)
    generate_authenticity_report(report, str(report_path))
    
    logger.info(f"📄 Rapport généré: {report_path}")
    
    # 3. Élimination automatique (optionnelle)
    eliminator = MockEliminator(str(project_root))
    elimination_results = eliminator.eliminate_mocks(report)
    
    logger.info(f"✅ Audit terminé - Score: {report.authenticity_score:.1%}")
    
    # 4. Résumé console
    print(f"\n🎯 SCORE D'AUTHENTICITÉ: {report.authenticity_score:.1%}")
    print(f"📊 MOCKS DÉTECTÉS: {report.total_mocks_detected}")
    print(f"🚨 CRITIQUES: {len(report.critical_mocks)}")
    print(f"⚠️ HAUTE PRIORITÉ: {len(report.high_priority_mocks)}")
    print(f"📋 RAPPORT COMPLET: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())