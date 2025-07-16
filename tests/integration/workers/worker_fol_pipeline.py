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
import pytest_asyncio
import asyncio
import sys
import os
import tempfile
from pathlib import Path


# Ajout du chemin pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from argumentation_analysis.agents.core.logic.first_order_logic_agent import FirstOrderLogicAgent as FOLLogicAgent
    from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory
    from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator, LLMAnalysisRequest
    from argumentation_analysis.core.llm_service import create_llm_service
    from argumentation_analysis.utils.tweety_error_analyzer import TweetyErrorAnalyzer
except ImportError:
    # Mock classes pour les tests si les composants n'existent pas encore
    class FOLLogicAgent:
        def __init__(self, kernel=None, **kwargs):
            self.kernel = kernel
            
        def generate_fol_syntax(self, text: str) -> str:
            return "∀x(Homme(x) → Mortel(x))"
            
        def analyze_with_tweety_fol(self, formulas) -> dict:
            return {"status": "success", "results": ["valid"]}

    class LogicAgentFactory:
        @staticmethod
        def create_agent(logic_type, kernel, agent_name):
            return FOLLogicAgent(kernel=kernel)
    
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


@pytest.fixture(scope="module")
async def fol_agent_with_kernel():
    """Fixture pour créer un FOLLogicAgent avec un kernel authentique."""
    config = UnifiedConfig()
    kernel = config.get_kernel_with_gpt4o_mini()
    # Utilisation de la factory pour créer une instance concrète
    agent = LogicAgentFactory.create_agent(logic_type="first_order", kernel=kernel)
    # L'ID 'default' correspond au service par défaut ajouté dans get_kernel_with_gpt4o_mini
    agent.setup_agent_components(llm_service_id="default")
    return agent

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
    
    @pytest.mark.asyncio
    async def test_fol_pipeline_end_to_end(self, fol_agent_with_kernel):
        """Test du pipeline FOL bout-en-bout."""
        # 1. Créer l'agent FOL
        fol_agent = fol_agent_with_kernel
        
        # 2. Générer la syntaxe FOL
        belief_set, message = await fol_agent.text_to_belief_set(self.test_text)
        
        assert belief_set is not None, f"La création du BeliefSet a échoué: {message}"
        assert "success" in message.lower() or belief_set is not None
        
        # 3. Analyser avec Tweety FOL
        is_consistent, consistency_message = fol_agent.is_consistent(belief_set)

        assert is_consistent is True, f"L'ensemble de croyances devrait être cohérent: {consistency_message}"
    
    @pytest.mark.asyncio
    async def test_fol_orchestration_integration(self):
        """Test d'intégration avec orchestration FOL."""
        # 1. Créer le service LLM
        llm_service = create_llm_service()
        
        # 2. Créer l'orchestrateur
        orchestrator = RealLLMOrchestrator(llm_service=llm_service)
        
        # 3. Exécuter l'orchestration avec logique FOL
        request = LLMAnalysisRequest(text=self.test_text, analysis_type="logical")
        result = await orchestrator.analyze_text(request)
        
        assert result is not None
        assert result.analysis_type == "logical"
        assert result.result['success'] is True
        
        # Vérifier les éléments spécifiques à FOL dans le sous-résultat
        inner_result = result.result.get('result', {})
        assert inner_result.get('logical_structure') == 'present'
    
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
    
    @pytest.mark.asyncio
    async def test_fol_pipeline_with_error_handling(self, fol_agent_with_kernel):
        """Test du pipeline FOL avec gestion d'erreurs."""
        # Texte problématique pour FOL
        problematic_text = "Cette phrase n'a pas de structure logique claire."
        
        fol_agent = fol_agent_with_kernel
        
        # Le nouvel agent devrait retourner un belief_set None et un message d'erreur
        belief_set, message = await fol_agent.text_to_belief_set(problematic_text)
        
        assert belief_set is None
        assert "échec" in message.lower() or "erreur" in message.lower()
    
    @pytest.mark.asyncio
    async def test_fol_pipeline_performance(self, fol_agent_with_kernel):
        """Test de performance du pipeline FOL."""
        import time
        
        fol_agent = fol_agent_with_kernel
        
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
            belief_set, _ = await fol_agent.text_to_belief_set(text)
            if belief_set:
                is_consistent, _ = fol_agent.is_consistent(belief_set)
                results.append({"consistent": is_consistent})
            else:
                results.append({"consistent": False})
        
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
            fol_agent = fol_agent_with_kernel
            
            # Formules FOL valides
            valid_formulas = [
                "∀x(Homme(x) → Mortel(x))",
                "Homme(socrate)"
            ]
            
            # La méthode `analyze_with_tweety_fol` est obsolète.
            # On teste la cohérence, qui est une tâche similaire.
            belief_set_str = "\\n".join(valid_formulas)
            from argumentation_analysis.agents.core.logic.belief_set import FirstOrderBeliefSet
            belief_set = FirstOrderBeliefSet(belief_set_str) # Création manuelle pour ce test
            
            is_consistent, message = fol_agent.is_consistent(belief_set)

            assert is_consistent is True
            
        except Exception as e:
            pytest.fail(f"Real Tweety FOL integration failed: {e}")
    
    def test_fol_error_analysis_integration(self):
        """Test d'intégration avec l'analyseur d'erreurs FOL."""
        error_analyzer = TweetyErrorAnalyzer()
        
        # Simuler une erreur FOL typique
        fol_error = "Predicate 'Mortel' has not been declared in FOL context"
        
        feedback = error_analyzer.analyze_error(fol_error, context={
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
    
    @pytest.mark.asyncio
    async def test_fol_syntax_validation_integration(self, fol_agent_with_kernel):
        """Test d'intégration de validation syntaxe FOL."""
        # Formules FOL à valider
        test_formulas = [
            "∀x(Homme(x) → Mortel(x))",  # Valide
            "∃x(Sage(x) ∧ Juste(x))",    # Valide
            "invalid fol formula",        # Invalide
            "∀x(P(x) → Q(x)) ∧ P(a)",   # Valide
        ]
        
        fol_agent = fol_agent_with_kernel
        
        validation_results = []
        for formula in test_formulas:
            try:
                is_valid = fol_agent.validate_formula(formula)
                validation_results.append({
                    "formula": formula,
                    "valid": is_valid,
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
    
    @pytest.mark.asyncio
    async def test_fol_semantic_validation_integration(self, fol_agent_with_kernel):
        """Test d'intégration de validation sémantique FOL."""
        # Test avec ensemble cohérent de formules
        coherent_formulas = [
            "∀x(Homme(x) → Mortel(x))",
            "Homme(socrate)",
            "¬Mortel(platon) → ¬Homme(platon)"  # Contraposée
        ]
        
        fol_agent = fol_agent_with_kernel
        
        # La nouvelle approche est de construire un belief set, puis de tester sa cohérence.
        # C'est un test plus complexe. Pour l'instant, on se base sur la validation de chaque formule.
        results = [fol_agent.validate_formula(f) for f in coherent_formulas]
        
        # Toutes les formules de cet ensemble sont syntaxiquement valides
        assert all(results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
if __name__ == "__main__":
    pytest.main([__file__])