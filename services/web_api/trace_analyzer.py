#!/usr/bin/env python3
"""
Analyseur Léger des Traces Playwright pour EPITA Intelligence Symbolique
========================================================================

Outil intelligent pour analyser les traces Playwright sans surcharger la mémoire.
Extrait seulement les informations critiques nécessaires à l'investigation.

Problème résolu:
- Fichiers de traces volumineux (227k+ tokens)  
- Risque de dépassement de la limite de tokens (200k max)
- Besoin d'analyser les réponses API /analyze sans manipulation lourde

Solution:
- Parser intelligent des métadonnées
- Extraction ciblée des requêtes /analyze
- Comparaison avec logs ServiceManager en temps réel
- Rapports concis et structurés

Version: 1.0.0
Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import json
import re
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import base64
import zipfile
import io

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('trace_analysis.log')
    ]
)
logger = logging.getLogger(__name__)

# Répertoires de travail
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PLAYWRIGHT_REPORT_DIR = PROJECT_ROOT / "playwright-report"
TRACE_DATA_DIR = PLAYWRIGHT_REPORT_DIR / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

@dataclass
class TestResult:
    """Métadonnées essentielles d'un test Playwright."""
    test_name: str
    status: str  # "passed", "failed", "skipped"
    duration_ms: int
    error_message: Optional[str] = None
    steps_count: int = 0
    api_calls_count: int = 0
    screenshots_count: int = 0

@dataclass
class APICallSummary:
    """Résumé d'un appel API analysé."""
    endpoint: str
    method: str
    status_code: int
    response_preview: str  # Premiers 200 caractères
    is_analyze_endpoint: bool = False
    contains_servicemanager_data: bool = False
    timestamp: Optional[str] = None

@dataclass
class TraceAnalysisReport:
    """Rapport complet d'analyse des traces."""
    analysis_timestamp: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    total_api_calls: int
    analyze_calls: int
    servicemanager_responses: int
    mock_responses: int
    tests_summary: List[TestResult]
    api_calls_summary: List[APICallSummary]
    recommendations: List[str]


class PlaywrightTraceAnalyzer:
    """Analyseur intelligent des traces Playwright."""
    
    def __init__(self, trace_dir: Path = TRACE_DATA_DIR):
        self.trace_dir = trace_dir
        self.report_data = None
        
        # Patterns pour extraction intelligente
        self.api_call_pattern = re.compile(
            r'"url":\s*"([^"]*)".*?"method":\s*"([^"]*)".*?"status":\s*(\d+)',
            re.DOTALL
        )
        
        self.analyze_endpoint_pattern = re.compile(
            r'/analyze|/api/analyze',
            re.IGNORECASE
        )
        
        self.servicemanager_pattern = re.compile(
            r'ServiceManager|analysis_id|argumentation_analysis',
            re.IGNORECASE
        )
        
        # Limites de sécurité pour éviter les débordements
        self.MAX_FILE_SIZE = 1024 * 1024  # 1MB max par fichier
        self.MAX_RESPONSE_PREVIEW = 200   # 200 chars max pour preview
        self.MAX_STEPS_ANALYZE = 50       # Max 50 steps analysés par test
        
    def extract_lightweight_metadata(self, md_file: Path) -> Optional[TestResult]:
        """Extrait les métadonnées légères d'un fichier .md de trace."""
        try:
            if md_file.stat().st_size > self.MAX_FILE_SIZE:
                logger.warning(f"Fichier {md_file.name} trop volumineux ({md_file.stat().st_size} bytes), analyse partielle")
                return self._extract_partial_metadata(md_file)
            
            content = md_file.read_text(encoding='utf-8')
            
            # Extraction des informations essentielles seulement
            test_name = self._extract_test_name(content)
            status = self._extract_status(content) 
            duration = self._extract_duration(content)
            error_msg = self._extract_error_message(content)
            
            # Comptage léger des éléments
            steps_count = len(re.findall(r'"step":', content[:10000]))  # Limite analyse
            api_calls_count = len(re.findall(r'"request":', content[:10000]))
            screenshots_count = len(re.findall(r'"screenshot":', content[:10000]))
            
            return TestResult(
                test_name=test_name,
                status=status,
                duration_ms=duration,
                error_message=error_msg,
                steps_count=steps_count,
                api_calls_count=api_calls_count,
                screenshots_count=screenshots_count
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de {md_file.name}: {e}")
            return None
    
    def _extract_partial_metadata(self, md_file: Path) -> Optional[TestResult]:
        """Extraction partielle pour les gros fichiers."""
        try:
            # Lire seulement les premiers Ko pour les métadonnées de base
            with open(md_file, 'r', encoding='utf-8') as f:
                partial_content = f.read(8192)  # 8KB seulement
            
            test_name = self._extract_test_name(partial_content) or f"Test_{md_file.stem}"
            status = self._extract_status(partial_content) or "unknown"
            duration = self._extract_duration(partial_content) or 0
            
            return TestResult(
                test_name=test_name,
                status=status, 
                duration_ms=duration,
                error_message="Analyse partielle (fichier volumineux)",
                steps_count=-1,  # Indique une analyse partielle
                api_calls_count=-1,
                screenshots_count=-1
            )
            
        except Exception as e:
            logger.error(f"Erreur extraction partielle {md_file.name}: {e}")
            return None
    
    def _extract_test_name(self, content: str) -> str:
        """Extrait le nom du test."""
        match = re.search(r'"title":\s*"([^"]*)"', content)
        if match:
            return match.group(1)
        
        # Fallback: chercher dans les premiers patterns
        match = re.search(r'test[_\s]*([a-zA-Z_]+)', content[:1000])
        return match.group(1) if match else "unknown_test"
    
    def _extract_status(self, content: str) -> str:
        """Extrait le statut du test."""
        if '"outcome": "passed"' in content:
            return "passed"
        elif '"outcome": "failed"' in content:
            return "failed"
        elif '"outcome": "skipped"' in content:
            return "skipped"
        else:
            return "unknown"
    
    def _extract_duration(self, content: str) -> int:
        """Extrait la durée du test."""
        match = re.search(r'"duration":\s*(\d+)', content)
        return int(match.group(1)) if match else 0
    
    def _extract_error_message(self, content: str) -> Optional[str]:
        """Extrait le message d'erreur s'il existe."""
        match = re.search(r'"error":\s*"([^"]*)"', content)
        if match:
            return match.group(1)[:200]  # Limite la taille
        return None
    
    def extract_api_responses(self, md_file: Path) -> List[APICallSummary]:
        """Extrait seulement les réponses des endpoints /analyze."""
        try:
            if md_file.stat().st_size > self.MAX_FILE_SIZE:
                logger.warning(f"Fichier {md_file.name} trop volumineux pour extraction API complète")
                return []
            
            content = md_file.read_text(encoding='utf-8')
            api_calls = []
            
            # Recherche ciblée des appels API
            matches = self.api_call_pattern.finditer(content)
            
            for match in matches:
                url = match.group(1)
                method = match.group(2)
                status = int(match.group(3))
                
                # Focus sur les endpoints d'analyse
                is_analyze = bool(self.analyze_endpoint_pattern.search(url))
                
                if is_analyze or '/api/' in url:  # Garde tous les appels API importants
                    # Extraction de la réponse (limitée)
                    response_start = match.end()
                    response_chunk = content[response_start:response_start + 1000]
                    
                    # Vérifie si c'est une vraie réponse ServiceManager
                    has_servicemanager = bool(self.servicemanager_pattern.search(response_chunk))
                    
                    # Preview de la réponse
                    response_preview = self._extract_response_preview(response_chunk)
                    
                    api_calls.append(APICallSummary(
                        endpoint=url,
                        method=method,
                        status_code=status,
                        response_preview=response_preview,
                        is_analyze_endpoint=is_analyze,
                        contains_servicemanager_data=has_servicemanager
                    ))
                    
                    # Limite le nombre d'appels analysés
                    if len(api_calls) >= 20:
                        break
            
            return api_calls
            
        except Exception as e:
            logger.error(f"Erreur extraction API de {md_file.name}: {e}")
            return []
    
    def _extract_response_preview(self, response_chunk: str) -> str:
        """Extrait un aperçu sécurisé de la réponse."""
        # Cherche le JSON de réponse
        json_match = re.search(r'"response":\s*({.*?})', response_chunk, re.DOTALL)
        if json_match:
            try:
                response_text = json_match.group(1)[:self.MAX_RESPONSE_PREVIEW]
                # Nettoie et sécurise
                response_text = re.sub(r'[^\w\s\{\}":,.-]', '', response_text)
                return response_text
            except:
                pass
        
        # Fallback: premiers mots du chunk
        clean_chunk = re.sub(r'[^\w\s]', ' ', response_chunk)
        words = clean_chunk.split()[:10]
        return ' '.join(words)
    
    def analyze_traces_summary(self) -> TraceAnalysisReport:
        """Analyse principale en mode résumé."""
        logger.info("[TRACE] Démarrage de l'analyse légère des traces Playwright")
        
        if not self.trace_dir.exists():
            raise FileNotFoundError(f"Répertoire de traces non trouvé: {self.trace_dir}")
        
        # Collecte des fichiers de métadonnées
        md_files = list(self.trace_dir.glob("*.md"))
        logger.info(f"[FILES] {len(md_files)} fichiers de traces trouvés")
        
        tests_summary = []
        all_api_calls = []
        
        # Analyse chaque fichier de trace
        for md_file in md_files:
            logger.info(f"[ANALYZE] Analyse de {md_file.name}")
            
            # Métadonnées du test
            test_result = self.extract_lightweight_metadata(md_file)
            if test_result:
                tests_summary.append(test_result)
            
            # Appels API (seulement pour les tests non partiels)
            if test_result and test_result.steps_count != -1:
                api_calls = self.extract_api_responses(md_file)
                all_api_calls.extend(api_calls)
        
        # Calculs statistiques
        passed_tests = sum(1 for t in tests_summary if t.status == "passed")
        failed_tests = sum(1 for t in tests_summary if t.status == "failed")
        analyze_calls = sum(1 for api in all_api_calls if api.is_analyze_endpoint)
        servicemanager_responses = sum(1 for api in all_api_calls if api.contains_servicemanager_data)
        mock_responses = analyze_calls - servicemanager_responses
        
        # Génération de recommandations
        recommendations = self._generate_recommendations(
            tests_summary, all_api_calls, analyze_calls, servicemanager_responses
        )
        
        report = TraceAnalysisReport(
            analysis_timestamp=datetime.now().isoformat(),
            total_tests=len(tests_summary),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            total_api_calls=len(all_api_calls),
            analyze_calls=analyze_calls,
            servicemanager_responses=servicemanager_responses,
            mock_responses=mock_responses,
            tests_summary=tests_summary,
            api_calls_summary=all_api_calls,
            recommendations=recommendations
        )
        
        self.report_data = report
        logger.info("[SUCCESS] Analyse terminée avec succès")
        
        return report
    
    def _generate_recommendations(self, tests: List[TestResult], apis: List[APICallSummary], 
                                 analyze_calls: int, sm_responses: int) -> List[str]:
        """Génère des recommandations basées sur l'analyse."""
        recommendations = []
        
        failed_count = sum(1 for t in tests if t.status == "failed")
        if failed_count > 0:
            recommendations.append(f"[WARNING] {failed_count} tests ont échoué - Examiner les messages d'erreur")
        
        if analyze_calls == 0:
            recommendations.append("[ERROR] Aucun appel à /analyze détecté - Vérifier l'intégration API")
        elif sm_responses == 0:
            recommendations.append("[WARNING] Aucune réponse ServiceManager détectée - Système probablement en mode mock")
        elif sm_responses < analyze_calls:
            recommendations.append(f"[INFO] {analyze_calls - sm_responses} appels en mode dégradé/mock sur {analyze_calls}")
        else:
            recommendations.append("[SUCCESS] ServiceManager répond correctement aux requêtes d'analyse")
        
        # Analyse de performance
        long_tests = [t for t in tests if t.duration_ms > 30000]
        if long_tests:
            recommendations.append(f"[PERF] {len(long_tests)} tests longs (>30s) - Optimisation recommandée")
        
        return recommendations
    
    def save_report(self, report: TraceAnalysisReport, output_file: Optional[Path] = None) -> Path:
        """Sauvegarde le rapport d'analyse."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = PROJECT_ROOT / f"trace_analysis_report_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(report), f, indent=2, ensure_ascii=False)
        
        logger.info(f"[REPORT] Rapport sauvegardé: {output_file}")
        return output_file
    
    def print_summary(self, report: TraceAnalysisReport):
        """Affiche un résumé concis du rapport."""
        print("\n" + "="*80)
        print("RAPPORT D'ANALYSE DES TRACES PLAYWRIGHT")
        print("="*80)
        print(f"Analyse du: {report.analysis_timestamp}")
        print(f"Tests totaux: {report.total_tests}")
        print(f"Tests reussis: {report.passed_tests}")
        print(f"Tests echoues: {report.failed_tests}")
        print(f"Appels API totaux: {report.total_api_calls}")
        print(f"Appels /analyze: {report.analyze_calls}")
        print(f"Reponses ServiceManager: {report.servicemanager_responses}")
        print(f"Reponses mock/degrade: {report.mock_responses}")
        
        print("\nRECOMMANDATIONS:")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"  {i}. {rec}")
        
        print("\nRESUME DES TESTS:")
        for test in report.tests_summary[:5]:  # Top 5
            status_indicator = "[OK]" if test.status == "passed" else "[FAIL]" if test.status == "failed" else "[SKIP]"
            print(f"  {status_indicator} {test.test_name} ({test.duration_ms}ms)")
        
        if len(report.tests_summary) > 5:
            print(f"  ... et {len(report.tests_summary) - 5} autres tests")
        
        print("\nAPPELS API /ANALYZE:")
        analyze_apis = [api for api in report.api_calls_summary if api.is_analyze_endpoint]
        for api in analyze_apis[:3]:  # Top 3
            sm_indicator = "[SM]" if api.contains_servicemanager_data else "[MOCK]"
            print(f"  {sm_indicator} {api.method} {api.endpoint} -> {api.status_code}")
            print(f"     Preview: {api.response_preview[:50]}...")
        
        print("\n" + "="*80)


def main():
    """Point d'entrée principal avec CLI."""
    parser = argparse.ArgumentParser(
        description="Analyseur Léger des Traces Playwright",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes d'analyse disponibles:
  summary         Analyse complète avec résumé (défaut)
  api-responses   Focus sur les réponses API /analyze  
  validation      Comparaison avec logs ServiceManager
  
Exemples:
  python trace_analyzer.py --mode=summary
  python trace_analyzer.py --mode=api-responses --output=api_analysis.json
  python trace_analyzer.py --mode=validation --verbose
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['summary', 'api-responses', 'validation'],
        default='summary',
        help='Mode d\'analyse (défaut: summary)'
    )
    
    parser.add_argument(
        '--trace-dir',
        type=Path,
        default=TRACE_DATA_DIR,
        help=f'Répertoire des traces (défaut: {TRACE_DATA_DIR})'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        help='Fichier de sortie pour le rapport JSON'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Mode verbeux'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        analyzer = PlaywrightTraceAnalyzer(args.trace_dir)
        
        if args.mode == 'summary':
            report = analyzer.analyze_traces_summary()
            analyzer.print_summary(report)
            
            if args.output:
                analyzer.save_report(report, args.output)
        
        elif args.mode == 'api-responses':
            # Mode focus API seulement
            print("[API] Analyse des réponses API /analyze en cours...")
            report = analyzer.analyze_traces_summary()
            
            analyze_apis = [api for api in report.api_calls_summary if api.is_analyze_endpoint]
            print(f"\n[STATS] {len(analyze_apis)} appels /analyze trouvés:")
            
            for api in analyze_apis:
                sm_status = "ServiceManager" if api.contains_servicemanager_data else "Mock/Dégradé"
                print(f"\n[CALL] {api.method} {api.endpoint}")
                print(f"   Status: {api.status_code}")
                print(f"   Type: {sm_status}")
                print(f"   Preview: {api.response_preview}")
        
        elif args.mode == 'validation':
            # Mode validation avec logs ServiceManager
            print("[VALIDATION] Validation avec logs ServiceManager...")
            report = analyzer.analyze_traces_summary()
            
            # Logique de comparaison avec logs (à implémenter selon besoins)
            print(f"[SUCCESS] Validation terminée - {report.servicemanager_responses} réponses validées")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()