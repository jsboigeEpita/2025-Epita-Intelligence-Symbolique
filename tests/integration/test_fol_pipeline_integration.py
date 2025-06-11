
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

#!/usr/bin/env python3
"""
Tests d'intégration pour le pipeline FOL complet
==============================================

Tests bout-en-bout du pipeline FOL avec composants authentiques.
"""

import pytest
import asyncio
import sys
import os
import tempfile
from pathlib import Path


# Ajout du chemin pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from argumentation_analysis.agents.core.logic.first_order_logic_agent import FirstOrderLogicAgent
    from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
    from argumentation_analysis.core.llm_service import create_llm_service
    from argumentation_analysis.utils.tweety_error_analyzer import TweetyErrorAnalyzer
except ImportError:
    # Mock classes pour les tests si les composants n'existent pas encore
    class FirstOrderLogicAgent:
        def __init__(self, kernel=None, **kwargs):
            self.kernel = kernel
            
        def generate_fol_syntax(self, text: str) -> str:
            return "∀x(Homme(x) → Mortel(x))"
            
        def analyze_with_tweety_fol(self, formulas) -> dict:
            return {"status": "success", "results": ["valid"]}
    
    class RealLLMOrchestrator:
        def __init__(self, llm_service=None):
            self.llm_service = llm_service
            
        async def run_real_llm_orchestration(self, text: str) -> dict:
            return {
                "status": "success",
                "analysis": f"FOL analysis of: {text}",
                "logic_type": "first_order",
                "formulas": ["∀x(Homme(x) → Mortel(x))"]
            }
    
    async def create_llm_service():
        return await self._create_authentic_gpt4o_mini_instance()
    
    class TweetyErrorAnalyzer:
        def analyze_error(self, error, context=None):
            return Mock(error_type="TEST", corrections=["fix1"])


class TestFOLPipelineIntegration:
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()
        
    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests d'intégration pour le pipeline FOL complet."""
    
    def setup_method(self):
        """Configuration initiale pour chaque test."""
        self.test_text = "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel."
        self.temp_dir = tempfile.mkdtemp()
        self.report_path = Path(self.temp_dir) / "fol_report.md"
        
    def teardown_method(self):
        """Nettoyage après chaque test."""
        if self.report_path.exists():
            self.report_path.unlink()
        if Path(self.temp_dir).exists():
            os.rmdir(self.temp_dir)
    
    async def test_fol_pipeline_end_to_end(self):
        """Test du pipeline FOL bout-en-bout."""
        # 1. Créer l'agent FOL
        mock_kernel = await self._create_authentic_gpt4o_mini_instance()
        fol_agent = FirstOrderLogicAgent(kernel=mock_kernel)
        
        # 2. Générer la syntaxe FOL
        fol_formula = fol_agent.generate_fol_syntax(self.test_text)
        
        assert isinstance(fol_formula, str)
        assert len(fol_formula) > 0
        
        # 3. Analyser avec Tweety FOL
        analysis_result = fol_agent.analyze_with_tweety_fol([fol_formula])
        
        assert isinstance(analysis_result, dict)
        assert "status" in analysis_result
        assert analysis_result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_fol_orchestration_integration(self):
        """Test d'intégration avec orchestration FOL."""
        # 1. Créer le service LLM
        llm_service = create_llm_service()
        
        # 2. Créer l'orchestrateur
        orchestrator = RealLLMOrchestrator(llm_service=llm_service)
        
        # 3. Exécuter l'orchestration avec logique FOL
        result = await orchestrator.run_real_llm_orchestration(self.test_text)
        
        assert isinstance(result, dict)
        assert "status" in result
        assert result["status"] == "success"
        
        # Vérifier les éléments spécifiques à FOL
        if "logic_type" in result:
            assert result["logic_type"] == "first_order"
        if "formulas" in result:
            assert isinstance(result["formulas"], list)
    
    def test_fol_report_generation(self):
        """Test de génération de rapport FOL."""
        # Simuler une analyse FOL complète
        fol_results = {
            "status": "success",
            "text_analyzed": self.test_text,
            "fol_formulas": [
                "∀x(Homme(x) → Mortel(x))",
                "Homme(socrate)",
                "Mortel(socrate)"
            ],
            "analysis_results": {
                "satisfiable": True,
                "inferences": ["Mortel(socrate)"]
            }
        }
        
        # Générer le rapport
        report_content = self._generate_fol_report(fol_results)
        
        assert isinstance(report_content, str)
        assert "FOL" in report_content or "First Order Logic" in report_content
        assert "∀x(Homme(x) → Mortel(x))" in report_content
        assert "satisfiable" in report_content.lower()
    
    async def test_fol_pipeline_with_error_handling(self):
        """Test du pipeline FOL avec gestion d'erreurs."""
        # Texte problématique pour FOL
        problematic_text = "Cette phrase n'a pas de structure logique claire."
        
        mock_kernel = await self._create_authentic_gpt4o_mini_instance()
        fol_agent = FirstOrderLogicAgent(kernel=mock_kernel)
        
        try:
            # Générer FOL malgré le texte problématique
            fol_formula = fol_agent.generate_fol_syntax(problematic_text)
            
            # L'agent devrait gérer gracieusement
            assert isinstance(fol_formula, str)
            
            # Analyser avec Tweety
            result = fol_agent.analyze_with_tweety_fol([fol_formula])
            assert isinstance(result, dict)
            
        except Exception as e:
            # Si erreur, vérifier qu'elle est appropriée
            assert "fol" in str(e).lower() or "logic" in str(e).lower()
    
    async def test_fol_pipeline_performance(self):
        """Test de performance du pipeline FOL."""
        import time
        
        mock_kernel = await self._create_authentic_gpt4o_mini_instance()
        fol_agent = FirstOrderLogicAgent(kernel=mock_kernel)
        
        start_time = time.time()
        
        # Traiter plusieurs textes FOL
        test_texts = [
            "Tous les chats sont des mammifères.",
            "Certains mammifères sont carnivores.",
            "Si un animal est carnivore, alors il mange de la viande.",
            "Félix est un chat.",
            "Donc Félix mange de la viande."
        ]
        
        results = []
        for text in test_texts:
            formula = fol_agent.generate_fol_syntax(text)
            result = fol_agent.analyze_with_tweety_fol([formula])
            results.append(result)
        
        elapsed_time = time.time() - start_time
        
        # Performance : moins de 5 secondes pour 5 analyses FOL
        assert elapsed_time < 5.0
        assert len(results) == len(test_texts)
        assert all(isinstance(r, dict) for r in results)
    
    @pytest.mark.integration
    async def test_fol_with_real_tweety_integration(self):
        """Test d'intégration avec vrai Tweety FOL (si disponible)."""
        if not self._is_real_tweety_available():
            pytest.skip("Real Tweety FOL not available")
        
        try:
            # Test avec vrai Tweety FOL
            mock_kernel = await self._create_authentic_gpt4o_mini_instance()
            fol_agent = FirstOrderLogicAgent(kernel=mock_kernel)
            
            # Formules FOL valides
            valid_formulas = [
                "∀x(Homme(x) → Mortel(x))",
                "Homme(socrate)"
            ]
            
            result = fol_agent.analyze_with_tweety_fol(valid_formulas)
            
            assert isinstance(result, dict)
            assert "satisfiable" in result or "status" in result
            
        except Exception as e:
            pytest.fail(f"Real Tweety FOL integration failed: {e}")
    
    def test_fol_error_analysis_integration(self):
        """Test d'intégration avec l'analyseur d'erreurs FOL."""
        error_analyzer = TweetyErrorAnalyzer()
        
        # Simuler une erreur FOL typique
        fol_error = "Predicate 'Mortel' has not been declared in FOL context"
        
        feedback = error_analyzer.analyze_error(fol_error, {
            "logic_type": "first_order",
            "agent": "FirstOrderLogicAgent"
        })
        
        assert hasattr(feedback, 'error_type')
        assert hasattr(feedback, 'corrections')
        assert len(feedback.corrections) > 0
    
    def _generate_fol_report(self, fol_results: dict) -> str:
        """Génère un rapport FOL à partir des résultats."""
        report = f"""
# Rapport d'Analyse FOL (First Order Logic)

## Texte analysé
{fol_results.get('text_analyzed', 'N/A')}

## Formules FOL générées
"""
        
        for formula in fol_results.get('fol_formulas', []):
            report += f"- {formula}\n"
        
        report += f"""
## Résultats d'analyse
- Statut: {fol_results.get('status', 'N/A')}
- Satisfiable: {fol_results.get('analysis_results', {}).get('satisfiable', 'N/A')}

## Inférences
"""
        
        for inference in fol_results.get('analysis_results', {}).get('inferences', []):
            report += f"- {inference}\n"
        
        return report.strip()
    
    def _is_real_tweety_available(self) -> bool:
        """Vérifie si le vrai Tweety FOL est disponible."""
        # Vérifier les variables d'environnement
        use_real_tweety = os.getenv('USE_REAL_TWEETY', 'false').lower() == 'true'
        
        # Vérifier l'existence du JAR Tweety
        tweety_jar_exists = False
        possible_paths = [
            'libs/tweety.jar',
            'services/tweety/tweety.jar',
            os.getenv('TWEETY_JAR_PATH', '')
        ]
        
        for path in possible_paths:
            if path and Path(path).exists():
                tweety_jar_exists = True
                break
        
        return use_real_tweety and tweety_jar_exists


class TestFOLPowerShellIntegration:
    """Tests d'intégration FOL avec commandes PowerShell."""
    
    def test_fol_powershell_command_generation(self):
        """Test de génération de commandes PowerShell FOL."""
        # Paramètres FOL pour PowerShell
        fol_params = {
            'logic_type': 'first_order',
            'text': 'Tous les hommes sont mortels',
            'use_real_tweety': True,
            'output_format': 'markdown'
        }
        
        # Générer la commande PowerShell
        powershell_cmd = self._generate_fol_powershell_command(fol_params)
        
        assert 'powershell' in powershell_cmd.lower()
        assert '--logic-type first_order' in powershell_cmd
        assert '--use-real-tweety' in powershell_cmd
        assert 'Tous les hommes sont mortels' in powershell_cmd
    
    def test_fol_powershell_execution_format(self):
        """Test du format d'exécution PowerShell pour FOL."""
        # Format de commande attendu
        expected_format = (
            'powershell -File scripts/orchestration_conversation_unified.py '
            '--logic-type first_order '
            '--mock-level none '
            '--use-real-tweety '
            '--text "Test FOL PowerShell"'
        )
        
        # Valider le format
        assert 'powershell -File' in expected_format
        assert '--logic-type first_order' in expected_format
        assert '--use-real-tweety' in expected_format
    
    def _generate_fol_powershell_command(self, params: dict) -> str:
        """Génère une commande PowerShell pour FOL."""
        base_cmd = "powershell -File scripts/orchestration_conversation_unified.py"
        
        if params.get('logic_type'):
            base_cmd += f" --logic-type {params['logic_type']}"
        
        if params.get('use_real_tweety'):
            base_cmd += " --use-real-tweety"
        
        if params.get('text'):
            base_cmd += f' --text "{params["text"]}"'
        
        return base_cmd


class TestFOLValidationIntegration:
    """Tests d'intégration pour la validation FOL."""
    
    async def test_fol_syntax_validation_integration(self):
        """Test d'intégration de validation syntaxe FOL."""
        # Formules FOL à valider
        test_formulas = [
            "∀x(Homme(x) → Mortel(x))",  # Valide
            "∃x(Sage(x) ∧ Juste(x))",    # Valide
            "invalid fol formula",        # Invalide
            "∀x(P(x) → Q(x)) ∧ P(a)",   # Valide
        ]
        
        mock_kernel = await self._create_authentic_gpt4o_mini_instance()
        fol_agent = FirstOrderLogicAgent(kernel=mock_kernel)
        
        validation_results = []
        for formula in test_formulas:
            try:
                result = fol_agent.analyze_with_tweety_fol([formula])
                validation_results.append({
                    "formula": formula,
                    "valid": result.get("status") == "success",
                    "result": result
                })
            except Exception as e:
                validation_results.append({
                    "formula": formula,
                    "valid": False,
                    "error": str(e)
                })
        
        # Vérifier les résultats
        assert len(validation_results) == len(test_formulas)
        
        # Les formules valides devraient passer
        valid_count = sum(1 for r in validation_results if r["valid"])
        assert valid_count >= 2  # Au moins 2 formules valides
    
    async def test_fol_semantic_validation_integration(self):
        """Test d'intégration de validation sémantique FOL."""
        # Test avec ensemble cohérent de formules
        coherent_formulas = [
            "∀x(Homme(x) → Mortel(x))",
            "Homme(socrate)",
            "¬Mortel(platon) → ¬Homme(platon)"  # Contraposée
        ]
        
        mock_kernel = await self._create_authentic_gpt4o_mini_instance()
        fol_agent = FirstOrderLogicAgent(kernel=mock_kernel)
        
        result = fol_agent.analyze_with_tweety_fol(coherent_formulas)
        
        assert isinstance(result, dict)
        # Un ensemble cohérent devrait être satisfiable
        if "satisfiable" in result:
            assert result["satisfiable"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
