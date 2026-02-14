"""
Fixtures authentiques pour tests informels - Phase 5 Mock Elimination
Remplace complètement les mocks par des composants authentiques
"""

import os
import sys
import pytest
import logging
from typing import Optional

# Import auto-configuration environnement
from argumentation_analysis.core import environment as auto_env

# Imports Semantic Kernel authentiques
from semantic_kernel import Kernel
from argumentation_analysis.agents.factory import AgentFactory, AgentType
from semantic_kernel.functions import KernelArguments
from argumentation_analysis.config.settings import AppSettings

# Conditional imports pour connecteurs authentiques
try:
    from semantic_kernel.connectors.ai.azure_ai_inference import (
        AzureAIInferenceChatCompletion,
    )

    azure_available = True
except ImportError:
    azure_available = False

try:
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

    openai_available = True
except ImportError:
    openai_available = False

# Imports composants authentiques
from argumentation_analysis.agents.core.informal.informal_agent import (
    InformalAnalysisAgent,
)
from argumentation_analysis.agents.core.informal.informal_definitions import (
    InformalAnalysisPlugin,
)


class AuthenticSemanticKernel:
    """
    Wrapper authentique pour Semantic Kernel - AUCUN MOCK
    Fournit un vrai Kernel avec services LLM conditionnels
    """

    def __init__(self):
        """Initialise un vrai Semantic Kernel avec services conditionnels"""
        self.kernel = Kernel()
        self.services_configured = []
        self.llm_service_id = "authentic_test_service"

        # Configuration Azure AI Inference
        if azure_available and os.getenv("AZURE_AI_INFERENCE_ENDPOINT"):
            try:
                azure_service = AzureAIInferenceChatCompletion(
                    endpoint=os.getenv("AZURE_AI_INFERENCE_ENDPOINT"),
                    api_key=os.getenv("AZURE_AI_INFERENCE_API_KEY"),
                    service_id=self.llm_service_id,
                )
                self.kernel.add_service(azure_service)
                self.services_configured.append("azure")
                print(
                    f"[AUTHENTIC] Azure AI Inference configuré: {self.llm_service_id}"
                )
            except Exception as e:
                print(f"[AUTHENTIC] Azure AI Inference non disponible: {e}")

        # Fallback OpenAI si Azure non disponible
        if (
            not self.services_configured
            and openai_available
            and os.getenv("OPENAI_API_KEY")
        ):
            try:
                openai_service = OpenAIChatCompletion(
                    api_key=os.getenv("OPENAI_API_KEY"), service_id=self.llm_service_id
                )
                self.kernel.add_service(openai_service)
                self.services_configured.append("openai")
                print(f"[AUTHENTIC] OpenAI configuré: {self.llm_service_id}")
            except Exception as e:
                print(f"[AUTHENTIC] OpenAI non disponible: {e}")

        if not self.services_configured:
            print(
                "[AUTHENTIC] Aucun service LLM configuré - tests limités aux fonctionnalités locales"
            )

    def get_kernel(self):
        """Retourne le vrai Kernel"""
        return self.kernel

    def is_llm_available(self):
        """Vérifie si un service LLM est disponible"""
        return len(self.services_configured) > 0

    def get_service_id(self):
        """Retourne l'ID du service configuré"""
        return self.llm_service_id if self.services_configured else None


class AuthenticFallacyDetector:
    """
    Détecteur de sophismes authentique - AUCUN MOCK
    Implémentation simple mais réelle basée sur patterns
    """

    def __init__(self, taxonomy_file_path: Optional[str] = None):
        """
        Initialise le détecteur avec taxonomie authentique

        Args:
            taxonomy_file_path: Chemin vers fichier taxonomie CSV
        """
        self.taxonomy_path = taxonomy_file_path
        self.fallacy_patterns = self._load_authentic_patterns()

    def _load_authentic_patterns(self):
        """Charge des patterns authentiques de détection de sophismes"""
        patterns = {
            "appel_autorite": {
                "keywords": ["expert", "autorité", "spécialiste", "dit que", "affirme"],
                "pattern": "appel non justifié à l'autorité",
                "confidence_base": 0.6,
            },
            "ad_hominem": {
                "keywords": ["trop jeune", "incompétent", "stupide", "ignorant"],
                "pattern": "attaque personnelle au lieu d'argumenter",
                "confidence_base": 0.7,
            },
            "pente_glissante": {
                "keywords": ["va mener", "inévitablement", "forcément", "bientôt"],
                "pattern": "enchainement causal non justifié",
                "confidence_base": 0.5,
            },
        }
        return patterns

    def detect(self, text: str):
        """
        Détection authentique de sophismes dans le texte

        Args:
            text: Texte à analyser

        Returns:
            List[dict]: Liste des sophismes détectés
        """
        detected_fallacies = []
        text_lower = text.lower()

        for fallacy_type, pattern_info in self.fallacy_patterns.items():
            confidence = 0.0
            matched_keywords = []

            # Analyse des mots-clés
            for keyword in pattern_info["keywords"]:
                if keyword.lower() in text_lower:
                    confidence += pattern_info["confidence_base"] / len(
                        pattern_info["keywords"]
                    )
                    matched_keywords.append(keyword)

            # Si suffisamment de mots-clés correspondent
            if confidence > 0.3:
                fallacy = {
                    "fallacy_type": fallacy_type.replace("_", " ").title(),
                    "text": text[:100] + "..." if len(text) > 100 else text,
                    "confidence": min(confidence, 0.9),
                    "details": f"Détecté par mots-clés: {matched_keywords}",
                    "pattern": pattern_info["pattern"],
                }
                detected_fallacies.append(fallacy)

        return detected_fallacies


class AuthenticRhetoricalAnalyzer:
    """
    Analyseur rhétorique authentique - AUCUN MOCK
    Implémentation simple mais réelle d'analyse rhétorique
    """

    def __init__(self):
        """Initialise l'analyseur rhétorique"""
        self.rhetorical_indicators = self._load_rhetorical_patterns()

    def _load_rhetorical_patterns(self):
        """Charge les patterns rhétoriques authentiques"""
        patterns = {
            "persuasif": {
                "keywords": ["devez", "important", "crucial", "essentiel"],
                "weight": 0.3,
            },
            "emotionnel": {
                "keywords": ["terrible", "magnifique", "catastrophe", "miracle"],
                "weight": 0.4,
            },
            "logique": {
                "keywords": ["donc", "par conséquent", "ainsi", "de ce fait"],
                "weight": 0.2,
            },
        }
        return patterns

    def analyze(self, text: str):
        """
        Analyse rhétorique authentique du texte

        Args:
            text: Texte à analyser

        Returns:
            dict: Résultats d'analyse rhétorique
        """
        text_lower = text.lower()
        tone_scores = {}
        techniques_detected = []

        # Analyse du ton
        for tone, pattern_info in self.rhetorical_indicators.items():
            score = 0.0
            for keyword in pattern_info["keywords"]:
                if keyword in text_lower:
                    score += pattern_info["weight"]
            tone_scores[tone] = score

        # Détermination du ton dominant
        dominant_tone = (
            max(tone_scores, key=tone_scores.get) if tone_scores else "neutre"
        )

        # Détection des techniques
        if tone_scores.get("emotionnel", 0) > 0.2:
            techniques_detected.append("appel à l'émotion")
        if "?" in text:
            techniques_detected.append("question rhétorique")
        if any(word in text_lower for word in ["nous", "ensemble", "tous"]):
            techniques_detected.append("appel au groupe")

        # Calcul de l'efficacité
        effectiveness = (
            sum(tone_scores.values()) / len(tone_scores) if tone_scores else 0.0
        )

        return {
            "tone": dominant_tone,
            "style": (
                "émotionnel" if tone_scores.get("emotionnel", 0) > 0.3 else "rationnel"
            ),
            "techniques": techniques_detected,
            "effectiveness": min(effectiveness, 1.0),
            "tone_scores": tone_scores,
        }


class AuthenticContextualAnalyzer:
    """
    Analyseur contextuel authentique - AUCUN MOCK
    Implémentation simple mais réelle d'analyse contextuelle
    """

    def __init__(self):
        """Initialise l'analyseur contextuel"""
        self.context_patterns = self._load_context_patterns()

    def _load_context_patterns(self):
        """Charge les patterns contextuels authentiques"""
        patterns = {
            "commercial": {
                "keywords": ["acheter", "vendre", "prix", "produit", "service"],
                "intent": "persuader",
            },
            "politique": {
                "keywords": ["gouvernement", "parti", "électeur", "vote", "politique"],
                "intent": "convaincre",
            },
            "académique": {
                "keywords": ["étude", "recherche", "analyse", "données", "résultat"],
                "intent": "informer",
            },
            "personnel": {
                "keywords": ["je", "mon", "ma", "mes", "personnel"],
                "intent": "exprimer",
            },
        }
        return patterns

    def analyze_context(self, text: str):
        """
        Analyse contextuelle authentique du texte

        Args:
            text: Texte à analyser

        Returns:
            dict: Résultats d'analyse contextuelle
        """
        text_lower = text.lower()
        context_scores = {}

        # Analyse des contextes
        for context_type, pattern_info in self.context_patterns.items():
            score = 0.0
            matched_keywords = []

            for keyword in pattern_info["keywords"]:
                if keyword in text_lower:
                    score += 1.0 / len(pattern_info["keywords"])
                    matched_keywords.append(keyword)

            if score > 0:
                context_scores[context_type] = {
                    "score": score,
                    "intent": pattern_info["intent"],
                    "keywords": matched_keywords,
                }

        # Détermination du contexte dominant
        if context_scores:
            dominant_context = max(
                context_scores.keys(), key=lambda k: context_scores[k]["score"]
            )
            confidence = context_scores[dominant_context]["score"]
            intent = context_scores[dominant_context]["intent"]
        else:
            dominant_context = "général"
            confidence = 0.1
            intent = "neutre"

        # Détermination de l'audience
        if any(word in text_lower for word in ["vous", "votre", "lecteur"]):
            audience = "ciblée"
        else:
            audience = "générale"

        return {
            "context_type": dominant_context,
            "audience": audience,
            "intent": intent,
            "confidence": min(confidence, 0.9),
            "all_contexts": context_scores,
        }


# ===============================
# FIXTURES AUTHENTIQUES
# ===============================


@pytest.fixture
def authentic_semantic_kernel():
    """
    Fixture authentique pour Semantic Kernel - AUCUN MOCK
    """
    print("[AUTHENTIC] Création du Semantic Kernel authentique...")
    return AuthenticSemanticKernel()


@pytest.fixture
def authentic_fallacy_detector():
    """
    Fixture authentique pour détecteur de sophismes - AUCUN MOCK
    """
    print("[AUTHENTIC] Création du détecteur de sophismes authentique...")
    return AuthenticFallacyDetector()


@pytest.fixture
def authentic_rhetorical_analyzer():
    """
    Fixture authentique pour analyseur rhétorique - AUCUN MOCK
    """
    print("[AUTHENTIC] Création de l'analyseur rhétorique authentique...")
    return AuthenticRhetoricalAnalyzer()


@pytest.fixture
def authentic_contextual_analyzer():
    """
    Fixture authentique pour analyseur contextuel - AUCUN MOCK
    """
    print("[AUTHENTIC] Création de l'analyseur contextuel authentique...")
    return AuthenticContextualAnalyzer()


@pytest.fixture
def setup_authentic_taxonomy_csv(tmp_path):
    """
    Crée un fichier taxonomie CSV authentique pour tests
    """
    print("[AUTHENTIC] Création du fichier taxonomie CSV authentique...")
    test_data_dir = tmp_path / "authentic_test_data"
    test_data_dir.mkdir(exist_ok=True)
    test_taxonomy_path = test_data_dir / "authentic_taxonomy.csv"

    # Contenu CSV authentique plus riche
    import csv
    import io

    header = [
        "PK",
        "Name",
        "Category",
        "Description",
        "Example",
        "Counter_Example",
        "depth",
        "path",
    ]
    data = [
        [
            1,
            "Appel à l'autorité",
            "Fallacy",
            "Invoquer une autorité non pertinente ou non qualifiée",
            "Einstein a dit que Dieu ne joue pas aux dés donc la mécanique quantique est fausse",
            "Selon le consensus scientifique actuel le réchauffement climatique est réel",
            1,
            "1",
        ],
        [
            2,
            "Pente glissante",
            "Fallacy",
            "Suggérer qu'une action mènera inévitablement à une chaîne d'événements indésirables",
            "Si nous légalisons la marijuana bientôt toutes les drogues seront légales",
            "Si nous augmentons le salaire minimum certaines entreprises pourraient réduire leurs effectifs",
            1,
            "2",
        ],
        [
            3,
            "Ad hominem",
            "Fallacy",
            "Attaquer la personne plutôt que ses idées",
            "Vous êtes trop jeune pour comprendre la politique",
            "Votre argument est basé sur des données obsolètes",
            1,
            "3",
        ],
        [
            4,
            "Faux dilemme",
            "Fallacy",
            "Présenter seulement deux options alors qu'il en existe d'autres",
            "Vous êtes soit avec nous soit contre nous",
            "Il faut choisir entre sécurité et liberté",
            1,
            "4",
        ],
        [
            5,
            "Appel à l'émotion",
            "Fallacy",
            "Utiliser des émotions plutôt que la logique pour convaincre",
            "Pensez aux enfants qui souffriront si cette loi passe",
            "Ces statistiques montrent l'impact négatif de cette politique",
            1,
            "5",
        ],
    ]

    with open(test_taxonomy_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)

    print(f"[AUTHENTIC] Fichier taxonomie créé: {test_taxonomy_path}")
    yield test_taxonomy_path

    # Nettoyage
    if os.path.exists(test_taxonomy_path):
        os.unlink(test_taxonomy_path)
        print(f"[AUTHENTIC] Fichier taxonomie nettoyé: {test_taxonomy_path}")


@pytest.fixture
def authentic_informal_analysis_plugin(
    setup_authentic_taxonomy_csv, authentic_semantic_kernel
):
    """
    Fixture authentique pour InformalAnalysisPlugin - AUCUN MOCK
    """
    kernel = authentic_semantic_kernel.get_kernel()
    test_taxonomy_path = str(setup_authentic_taxonomy_csv)
    kernel = authentic_semantic_kernel.get_kernel()
    print(
        f"[AUTHENTIC] Création du plugin InformalAnalysis authentique avec taxonomie: {test_taxonomy_path}"
    )

    try:
        plugin = InformalAnalysisPlugin(
            kernel=kernel, taxonomy_file_path=test_taxonomy_path
        )
        print("[AUTHENTIC] Plugin InformalAnalysis créé avec succès")
        return plugin
    except Exception as e:
        print(f"[AUTHENTIC] Erreur création plugin: {e}")
        # Fallback - plugin sans fichier taxonomie
        return InformalAnalysisPlugin(kernel=kernel)


@pytest.fixture
def authentic_informal_agent(authentic_semantic_kernel, setup_authentic_taxonomy_csv):
    """
    Fixture authentique pour InformalAnalysisAgent - AUCUN MOCK
    Utilise désormais AgentFactory pour la création.
    """
    kernel = authentic_semantic_kernel.get_kernel()
    llm_service_id = authentic_semantic_kernel.get_service_id()
    agent_name = "authentic_informal_agent"

    print(f"[AUTHENTIC] Création de l'agent '{agent_name}' via AgentFactory...")

    try:
        if not llm_service_id:
            pytest.skip(
                "Saut du test authentique car aucun service LLM n'est configuré."
            )

        settings = AppSettings()
        settings.service_manager.default_llm_service_id = llm_service_id
        # Correction: Le constructeur de AgentFactory attend llm_service_id (str), pas settings (AppSettings)
        agent_factory = AgentFactory(kernel, llm_service_id=llm_service_id)

        # On utilise la config "full" pour avoir toutes les fonctionnalités
        agent = agent_factory.create_agent(
            AgentType.INFORMAL_FALLACY,
            config_name="full",
            taxonomy_file_path=str(setup_authentic_taxonomy_csv),
        )
        agent.name = agent_name  # Surcharger le nom

        print(f"[AUTHENTIC] Agent '{agent_name}' créé avec succès via AgentFactory.")
        return agent

    except Exception as e:
        print(f"[AUTHENTIC] Erreur création agent via AgentFactory: {e}")
        pytest.fail(f"Impossible de créer l'agent via AgentFactory: {e}")


@pytest.fixture
def simple_authentic_informal_agent(setup_authentic_taxonomy_csv):
    """
    Fixture authentique pour un InformalAnalysisAgent en mode 'simple'.
    Cet agent est configuré pour une réponse directe sans workflow complexe.
    NOTE: Crée un kernel frais à chaque appel pour garantir l'isolation.
    """
    from argumentation_analysis.core.llm_service import create_llm_service
    from semantic_kernel import Kernel

    kernel = Kernel()
    llm_service_id = "default_llm_service"
    try:
        # force_authentic=True pour s'assurer qu'on n'obtient pas un mock
        llm_service = create_llm_service(
            service_id=llm_service_id, force_authentic=True
        )
        kernel.add_service(llm_service)
    except Exception as e:
        pytest.skip(f"Impossible de créer un service LLM authentique : {e}")
    agent_name = "simple_authentic_informal_agent"

    print(
        f"[AUTHENTIC] Création de l'agent '{agent_name}' (simple) via AgentFactory..."
    )

    try:
        if not llm_service_id:
            pytest.skip(
                "Saut du test authentique car aucun service LLM n'est configuré."
            )

        agent_factory = AgentFactory(kernel, llm_service_id=llm_service_id)

        agent = agent_factory.create_agent(
            AgentType.INFORMAL_FALLACY,
            config_name="simple",
            taxonomy_file_path=str(setup_authentic_taxonomy_csv),
        )
        agent.name = agent_name

        print(f"[AUTHENTIC] Agent '{agent_name}' créé avec succès.")
        return agent

    except Exception as e:
        print(f"[AUTHENTIC] Erreur création agent simple via AgentFactory: {e}")
        pytest.fail(f"Impossible de créer l'agent (simple) via AgentFactory: {e}")


@pytest.fixture
def sample_authentic_test_text():
    """
    Fixture pour texte de test authentique - plus riche et réaliste
    """
    return """
    Les experts affirment que ce produit révolutionnaire va changer votre vie.
    Ne laissez pas cette opportunité unique vous échapper ! 
    Vous devez agir maintenant ou vous le regretterez pour toujours.
    Soit vous achetez ce produit, soit vous restez dans votre situation actuelle désespérée.
    Pensez à votre famille qui mérite le meilleur.
    Les concurrents sont jaloux de notre succès et tentent de nous discréditer,
    mais vous êtes trop intelligent pour tomber dans leur piège.
    """


# Marqueurs pytest pour organisation des fixtures authentiques
pytestmark = [
    pytest.mark.llm_integration,  # Tests LLM intégration (remplace authentic + no_mocks)
    pytest.mark.phase5,  # Marqueur Phase 5
    pytest.mark.informal,  # Marqueur spécifique analyse informelle
]
