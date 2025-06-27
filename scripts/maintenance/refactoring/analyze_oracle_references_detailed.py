#!/usr/bin/env python3
"""
Script d'analyse détaillée des fichiers avec références Oracle.

Ce script analyse en profondeur les 208 fichiers identifiés avec des références
Oracle pour les catégoriser précisément selon leur utilité et leur statut.

Categories:
- Code actif (utilisé dans le système)
- Tests orphelins (anciens tests non intégrés)  
- Scripts temporaires (scripts de développement)
- Documentation obsolète (guides/rapports anciens)
- Fichiers de configuration (cache, environnement)
- Code précieux récupérable (extensions, modules utiles)
"""

import argumentation_analysis.core.environment
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from dataclasses import dataclass
from enum import Enum

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FileCategory(Enum):
    """Catégories de classification des fichiers Oracle"""
    CODE_ACTIF = "code_actif"
    TESTS_ORPHELINS = "tests_orphelins"
    SCRIPTS_TEMPORAIRES = "scripts_temporaires"
    DOCUMENTATION_OBSOLETE = "documentation_obsolete"
    FICHIERS_CONFIGURATION = "fichiers_configuration"
    CODE_PRECIEUX_RECUPERABLE = "code_precieux_recuperable"

@dataclass
class FileAnalysis:
    """Analyse détaillée d'un fichier"""
    file_path: str
    file_size: int
    file_type: str
    category: FileCategory
    confidence_score: float
    oracle_references: Dict[str, Any]
    code_quality_metrics: Dict[str, Any]
    integration_potential: str
    recommendation: str
    risk_assessment: str
    recovery_priority: int

class OracleFileAnalyzer:
    """Analyseur de fichiers avec références Oracle"""
    
    def __init__(self, data_file: str):
        self.data_file = Path(data_file)
        self.project_root = Path(".")
        self.analysis_results = {}
        self.categorization_stats = {}
        
        # Patterns pour la classification
        self.category_patterns = {
            FileCategory.CODE_ACTIF: {
                'paths': [
                    r'argumentation_analysis/agents/core/oracle/',
                    r'argumentation_analysis/core/',
                    r'argumentation_analysis/orchestration/'
                ],
                'integration_status': ['integrated', 'work_in_progress'],
                'keywords': ['class ', 'def ', 'import ', 'from '],
                'min_quality': 'moderate'
            },
            FileCategory.TESTS_ORPHELINS: {
                'paths': [
                    r'tests/.*test_.*\.py$',
                    r'.*test.*\.py$'
                ],
                'integration_status': ['test_file'],
                'keywords': ['test_', 'pytest', 'unittest', 'assert'],
                'min_quality': 'basic'
            },
            FileCategory.SCRIPTS_TEMPORAIRES: {
                'paths': [
                    r'scripts/temp/',
                    r'scripts/.*temp.*',
                    r'.*_fixes\.py$',
                    r'.*_corrections\.py$'
                ],
                'keywords': ['fix', 'temp', 'debug', 'quick'],
                'min_quality': 'basic'
            },
            FileCategory.DOCUMENTATION_OBSOLETE: {
                'paths': [
                    r'.*\.md$',
                    r'.*\.txt$',
                    r'.*\.rst$'
                ],
                'keywords': ['documentation', 'guide', 'readme'],
                'min_quality': 'minimal'
            },
            FileCategory.FICHIERS_CONFIGURATION: {
                'paths': [
                    r'venv_test/',
                    r'.*\.json$',
                    r'.*\.yaml$',
                    r'.*\.yml$',
                    r'.*config.*'
                ],
                'keywords': ['config', 'setup', 'install'],
                'min_quality': 'minimal'
            },
            FileCategory.CODE_PRECIEUX_RECUPERABLE: {
                'keywords': ['phase_d', 'enhanced', 'oracle', 'extension'],
                'min_quality': 'substantial',
                'special_markers': ['Phase D', 'Enhanced', 'Extensions']
            }
        }

    def load_data(self) -> Dict[str, Any]:
        """Charge les données d'analyse existantes"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Données chargées depuis {self.data_file}")
            return data
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données: {e}")
            raise

    def analyze_code_quality(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyse la qualité du code d'un fichier"""
        quality_metrics = {
            'complexity_score': 0,
            'maintainability': 'unknown',
            'documentation_level': 'none',
            'test_coverage_potential': 'low',
            'reusability': 'low'
        }
        
        content_preview = file_data.get('content_preview', '')
        file_size = file_data.get('file_size', 0)
        
        # Analyse de la complexité basée sur la taille et le contenu
        if file_size > 20000:
            quality_metrics['complexity_score'] = 8
        elif file_size > 10000:
            quality_metrics['complexity_score'] = 6
        elif file_size > 5000:
            quality_metrics['complexity_score'] = 4
        else:
            quality_metrics['complexity_score'] = 2
            
        # Analyse de la documentation
        if '"""' in content_preview or "'''" in content_preview:
            quality_metrics['documentation_level'] = 'good'
        elif '#' in content_preview:
            quality_metrics['documentation_level'] = 'basic'
            
        # Analyse de la maintenabilité
        code_quality = file_data.get('code_quality', 'basic')
        if code_quality == 'substantial':
            quality_metrics['maintainability'] = 'high'
        elif code_quality == 'moderate':
            quality_metrics['maintainability'] = 'medium'
        else:
            quality_metrics['maintainability'] = 'low'
            
        # Potentiel de réutilisation
        keywords = file_data.get('keyword_matches', [])
        oracle_keywords = len([k for k in keywords if k in ['oracle', 'moriarty', 'sherlock', 'watson']])
        if oracle_keywords >= 3:
            quality_metrics['reusability'] = 'high'
        elif oracle_keywords >= 2:
            quality_metrics['reusability'] = 'medium'
            
        return quality_metrics

    def categorize_file(self, file_data: Dict[str, Any]) -> Tuple[FileCategory, float]:
        """Catégorise un fichier et retourne le niveau de confiance"""
        file_path = file_data.get('file_path', '')
        integration_status = file_data.get('integration_status', '')
        code_quality = file_data.get('code_quality', 'basic')
        keywords = file_data.get('keyword_matches', [])
        content_preview = file_data.get('content_preview', '')
        
        scores = {}
        
        for category, patterns in self.category_patterns.items():
            score = 0
            
            # Vérification des chemins
            if 'paths' in patterns:
                for path_pattern in patterns['paths']:
                    if re.search(path_pattern, file_path, re.IGNORECASE):
                        score += 30
                        
            # Vérification du statut d'intégration
            if 'integration_status' in patterns:
                if integration_status in patterns['integration_status']:
                    score += 25
                    
            # Vérification des mots-clés
            if 'keywords' in patterns:
                keyword_matches = sum(1 for kw in patterns['keywords'] 
                                    if any(kw in k.lower() for k in keywords) or 
                                       kw.lower() in content_preview.lower())
                score += keyword_matches * 10
                
            # Vérification de la qualité minimale
            if 'min_quality' in patterns:
                quality_levels = {'minimal': 1, 'basic': 2, 'moderate': 3, 'substantial': 4}
                min_level = quality_levels.get(patterns['min_quality'], 1)
                current_level = quality_levels.get(code_quality, 1)
                if current_level >= min_level:
                    score += 15
                    
            # Marqueurs spéciaux pour le code précieux
            if 'special_markers' in patterns:
                for marker in patterns['special_markers']:
                    if marker.lower() in content_preview.lower():
                        score += 20
                        
            scores[category] = score
            
        # Règles spéciales pour la catégorisation
        if 'phase_d_extensions.py' in file_path:
            scores[FileCategory.CODE_PRECIEUX_RECUPERABLE] += 50
            
        if 'venv_test' in file_path:
            scores[FileCategory.FICHIERS_CONFIGURATION] += 40
            
        if file_path.startswith('tests/validation_sherlock_watson/'):
            scores[FileCategory.TESTS_ORPHELINS] += 30
            
        # Sélection de la catégorie avec le score le plus élevé
        best_category = max(scores, key=scores.get)
        confidence = min(scores[best_category] / 100.0, 1.0)
        
        return best_category, confidence

    def assess_recovery_potential(self, file_data: Dict[str, Any], category: FileCategory) -> Tuple[str, int]:
        """Évalue le potentiel de récupération d'un fichier"""
        code_quality = file_data.get('code_quality', 'basic')
        reference_count = file_data.get('reference_count', 0)
        file_size = file_data.get('file_size', 0)
        
        # Matrice de priorité de récupération
        priority_matrix = {
            FileCategory.CODE_PRECIEUX_RECUPERABLE: {
                'substantial': 9,
                'moderate': 7,
                'basic': 5
            },
            FileCategory.CODE_ACTIF: {
                'substantial': 8,
                'moderate': 6,
                'basic': 4
            },
            FileCategory.TESTS_ORPHELINS: {
                'substantial': 6,
                'moderate': 4,
                'basic': 2
            },
            FileCategory.SCRIPTS_TEMPORAIRES: {
                'substantial': 4,
                'moderate': 2,
                'basic': 1
            },
            FileCategory.DOCUMENTATION_OBSOLETE: {
                'substantial': 3,
                'moderate': 2,
                'basic': 1
            },
            FileCategory.FICHIERS_CONFIGURATION: {
                'substantial': 2,
                'moderate': 1,
                'basic': 1
            }
        }
        
        base_priority = priority_matrix.get(category, {}).get(code_quality, 1)
        
        # Ajustements basés sur les références Oracle
        if reference_count > 30:
            base_priority += 2
        elif reference_count > 15:
            base_priority += 1
            
        # Ajustements basés sur la taille
        if file_size > 15000:
            base_priority += 1
            
        priority = min(base_priority, 10)
        
        # Recommandations textuelles
        recommendations = {
            (9, 10): "PRIORITÉ CRITIQUE - Récupération immédiate nécessaire",
            (7, 8): "PRIORITÉ HAUTE - Récupération recommandée dans les 48h",
            (5, 6): "PRIORITÉ MOYENNE - Récupération à planifier",
            (3, 4): "PRIORITÉ BASSE - Récupération optionnelle",
            (1, 2): "PRIORITÉ MINIMALE - Archivage ou suppression"
        }
        
        for (min_p, max_p), rec in recommendations.items():
            if min_p <= priority <= max_p:
                return rec, priority
                
        return "PRIORITÉ INDÉTERMINÉE", priority

    def analyze_file(self, file_data: Dict[str, Any]) -> FileAnalysis:
        """Analyse complète d'un fichier"""
        # Catégorisation
        category, confidence = self.categorize_file(file_data)
        
        # Analyse de qualité
        quality_metrics = self.analyze_code_quality(file_data)
        
        # Évaluation du potentiel de récupération
        recommendation, priority = self.assess_recovery_potential(file_data, category)
        
        # Évaluation des risques
        risk_factors = []
        file_size = file_data.get('file_size', 0)
        if file_size > 50000:
            risk_factors.append("Fichier volumineux")
        if 'venv_test' in file_data.get('file_path', ''):
            risk_factors.append("Dépendance externe")
        if file_data.get('integration_status') == 'test_file':
            risk_factors.append("Tests orphelins")
            
        risk_assessment = "FAIBLE" if not risk_factors else f"MOYEN ({', '.join(risk_factors)})"
        
        return FileAnalysis(
            file_path=file_data.get('file_path', ''),
            file_size=file_data.get('file_size', 0),
            file_type=file_data.get('file_type', ''),
            category=category,
            confidence_score=confidence,
            oracle_references={
                'keywords': file_data.get('keyword_matches', []),
                'reference_count': file_data.get('reference_count', 0),
                'content_preview': file_data.get('content_preview', '')[:200] + '...'
            },
            code_quality_metrics=quality_metrics,
            integration_potential=file_data.get('integration_status', 'unknown'),
            recommendation=recommendation,
            risk_assessment=risk_assessment,
            recovery_priority=priority
        )

    def run_detailed_analysis(self) -> Dict[str, Any]:
        """Lance l'analyse détaillée complète"""
        logger.info("Début de l'analyse détaillée des fichiers Oracle")
        
        # Chargement des données
        data = self.load_data()
        code_recovery = data.get('organization_plan', {}).get('code_recovery', [])
        
        logger.info(f"Analyse de {len(code_recovery)} fichiers avec références Oracle")
        
        categorized_files = {category: [] for category in FileCategory}
        all_analyses = []
        
        for file_data in code_recovery:
            analysis = self.analyze_file(file_data.get('analysis', {}))
            all_analyses.append(analysis)
            categorized_files[analysis.category].append(analysis)
            
        # Calcul des statistiques
        self.categorization_stats = {
            'total_files_analyzed': len(all_analyses),
            'category_distribution': {
                category.value: len(files) for category, files in categorized_files.items()
            },
            'priority_distribution': {
                f'priority_{i}': len([a for a in all_analyses if a.recovery_priority == i])
                for i in range(1, 11)
            },
            'quality_distribution': {
                'substantial': len([a for a in all_analyses if a.code_quality_metrics['maintainability'] == 'high']),
                'moderate': len([a for a in all_analyses if a.code_quality_metrics['maintainability'] == 'medium']),
                'basic': len([a for a in all_analyses if a.code_quality_metrics['maintainability'] == 'low'])
            }
        }
        
        results = {
            'analysis_metadata': {
                'timestamp': datetime.now().isoformat(),
                'analyzer_version': '1.0.0',
                'total_files_analyzed': len(all_analyses),
                'analysis_criteria': [cat.value for cat in self.category_patterns.keys()]
            },
            'categorization_summary': self.categorization_stats,
            'detailed_analyses': {
                category.value: [
                    {
                        'file_path': analysis.file_path,
                        'file_size': analysis.file_size,
                        'file_type': analysis.file_type,
                        'category': analysis.category.value,
                        'confidence_score': analysis.confidence_score,
                        'oracle_references': analysis.oracle_references,
                        'code_quality_metrics': analysis.code_quality_metrics,
                        'integration_potential': analysis.integration_potential,
                        'recommendation': analysis.recommendation,
                        'risk_assessment': analysis.risk_assessment,
                        'recovery_priority': analysis.recovery_priority
                    }
                    for analysis in files
                ]
                for category, files in categorized_files.items()
            },
            'high_priority_files': [
                {
                    'file_path': analysis.file_path,
                    'category': analysis.category.value,
                    'priority': analysis.recovery_priority,
                    'recommendation': analysis.recommendation
                }
                for analysis in sorted(all_analyses, key=lambda x: x.recovery_priority, reverse=True)[:20]
            ]
        }
        
        logger.info("Analyse détaillée terminée")
        return results

def main():
    """Fonction principale"""
    try:
        # Vérification du fichier de données
        data_file = "logs/orphan_files_data_20250607_142422.json"
        if not Path(data_file).exists():
            logger.error(f"Fichier de données non trouvé: {data_file}")
            return
            
        # Analyse détaillée
        analyzer = OracleFileAnalyzer(data_file)
        results = analyzer.run_detailed_analysis()
        
        # Sauvegarde des résultats
        output_file = f"logs/oracle_files_categorization_detailed.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Résultats sauvegardés dans {output_file}")
        
        # Affichage du résumé
        print("\n" + "="*80)
        print("RÉSUMÉ DE L'ANALYSE DÉTAILLÉE DES FICHIERS ORACLE")
        print("="*80)
        print(f"Total de fichiers analysés: {results['analysis_metadata']['total_files_analyzed']}")
        print("\nDistribution par catégorie:")
        for category, count in results['categorization_summary']['category_distribution'].items():
            print(f"  {category.replace('_', ' ').title()}: {count} fichiers")
            
        print(f"\nFichiers haute priorité identifiés: {len(results['high_priority_files'])}")
        print(f"Rapport détaillé généré: {output_file}")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {e}")
        raise

if __name__ == "__main__":
    main()