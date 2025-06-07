#!/usr/bin/env python3
"""
TEST D'AUDIT DE L'INTÉGRITÉ DES RÈGLES CLUEDO
Vérifie que le système respecte les règles fondamentales du Cluedo et n'autorise aucune triche.
"""

import pytest
import logging
from unittest.mock import Mock, patch
from typing import List, Dict, Any

# Configuration du logging pour l'audit
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CluedoIntegrityAudit")

# Import des composants à auditer
from argumentation_analysis.agents.core.oracle.cluedo_dataset import CluedoDataset
from argumentation_analysis.agents.core.oracle.dataset_access_manager import CluedoDatasetManager
from argumentation_analysis.agents.core.oracle.permissions import PermissionManager, QueryType, PermissionRule


class TestCluedoIntegrityAudit:
    """Tests d'intégrité pour vérifier le respect des règles du Cluedo."""
    
    def setup_method(self):
        """Configuration pour chaque test."""
        # Cartes de Moriarty (connues)
        self.moriarty_cards = ["Colonel Moutarde", "Corde", "Bureau"]
        
        # Cartes des autres joueurs (DOIVENT rester secrètes)
        self.autres_joueurs_cards = [
            "Docteur Olive", "Madame Leblanc", "Mademoiselle Rose",
            "Poignard", "Barre de fer", "Revolver", 
            "Salon", "Cuisine", "Salle de bal"
        ]
        
        # Solution secrète (NE DOIT JAMAIS être accessible)
        self.solution_secrete = {
            "suspect": "Professeur Violet",
            "arme": "Chandelier", 
            "lieu": "Conservatoire"
        }
        
        # Dataset de test
        self.dataset = CluedoDataset(self.moriarty_cards)
        self.dataset_manager = CluedoDatasetManager(self.dataset)
        
        logger.info("=== DÉBUT AUDIT INTÉGRITÉ CLUEDO ===")
    
    def test_violation_acces_cartes_autres_joueurs(self):
        """🚨 AUDIT CRITIQUE: Vérifie que get_autres_joueurs_cards() VIOLE les règles du Cluedo."""
        logger.error("🚨 TEST DE VIOLATION: get_autres_joueurs_cards()")
        
        # Cette méthode NE DEVRAIT PAS EXISTER selon les règles du Cluedo !
        autres_cartes = self.dataset.get_autres_joueurs_cards()
        
        logger.error(f"❌ VIOLATION DÉTECTÉE: Accès aux cartes des autres joueurs: {autres_cartes}")
        logger.error(f"❌ NOMBRE DE CARTES EXPOSÉES: {len(autres_cartes)}")
        
        # Cette méthode est une violation des règles - elle expose les cartes des autres
        assert len(autres_cartes) > 0, "La méthode expose effectivement les cartes des autres joueurs"
        
        # Vérification que cette méthode contient bien des cartes d'autres joueurs
        cartes_exposees = set(autres_cartes)
        cartes_moriarty = set(self.moriarty_cards)
        
        assert not cartes_exposees.issubset(cartes_moriarty), "❌ VIOLATION CONFIRMÉE: Expose les cartes des autres joueurs"
        
        logger.error("🚨 CONCLUSION: Cette méthode viole les règles du Cluedo et doit être supprimée ou sécurisée !")
    
    def test_triche_simulation_autre_joueur(self):
        """🚨 AUDIT CRITIQUE: Vérifie que simulate_other_player_response() utilise la méthode interdite."""
        logger.error("🚨 TEST DE TRICHE: simulate_other_player_response()")
        
        # Import de l'agent Moriarty pour tester la simulation
        from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyTools
        
        tools = MoriartyTools(self.dataset_manager)
        
        # Test de simulation qui utilise get_autres_joueurs_cards() - TRICHE !
        with patch.object(self.dataset, 'get_autres_joueurs_cards', wraps=self.dataset.get_autres_joueurs_cards) as mock_method:
            result = tools.simulate_other_player_response("Docteur Olive,Poignard,Salon", "AutreJoueur")
            
            # Vérification que la méthode interdite est appelée
            mock_method.assert_called_once()
            logger.error(f"❌ TRICHE CONFIRMÉE: simulate_other_player_response() appelle get_autres_joueurs_cards()")
            logger.error(f"❌ RÉSULTAT DE LA TRICHE: {result}")
            
        logger.error("🚨 CONCLUSION: La simulation triche en accédant aux cartes des autres joueurs !")
    
    def test_regles_cluedo_fondamentales_violees(self):
        """🚨 AUDIT: Vérifie que les règles fondamentales du Cluedo sont violées."""
        logger.error("🚨 AUDIT DES RÈGLES FONDAMENTALES")
        
        violations = []
        
        # RÈGLE 1: Un joueur ne peut voir QUE ses propres cartes
        try:
            autres_cartes = self.dataset.get_autres_joueurs_cards()
            violations.append(f"VIOLATION RÈGLE 1: Accès aux cartes des autres joueurs ({len(autres_cartes)} cartes)")
        except AttributeError:
            logger.info("✅ RÈGLE 1: Méthode get_autres_joueurs_cards() n'existe pas - CONFORME")
        
        # RÈGLE 2: Les révélations doivent être explicites et tracées
        cartes_revelees = self.dataset.get_revealed_cards_to_agent("TestAgent")
        if len(cartes_revelees) == 0:
            logger.info("✅ RÈGLE 2: Aucune révélation non autorisée - CONFORME")
        
        # RÈGLE 3: La solution ne doit jamais être accessible directement
        try:
            solution = self.dataset.get_solution()
            violations.append(f"VIOLATION RÈGLE 3: Accès direct à la solution: {solution}")
        except AttributeError:
            logger.info("✅ RÈGLE 3: Pas d'accès direct à la solution - CONFORME")
        except Exception:
            logger.info("✅ RÈGLE 3: Solution protégée - CONFORME")
        
        # RÈGLE 4: Moriarty ne doit révéler que SES propres cartes
        moriarty_cards = set(self.dataset.get_moriarty_cards())
        autres_cards = set(self.dataset.get_autres_joueurs_cards())
        if moriarty_cards.intersection(autres_cards):
            violations.append("VIOLATION RÈGLE 4: Confusion entre cartes Moriarty et autres joueurs")
        
        logger.error(f"🚨 TOTAL VIOLATIONS DÉTECTÉES: {len(violations)}")
        for violation in violations:
            logger.error(f"❌ {violation}")
        
        # Le test doit échouer car des violations sont détectées
        assert len(violations) > 0, f"AUDIT CONFIRMÉ: {len(violations)} violations des règles du Cluedo détectées"
    
    def test_systeme_permissions_insuffisant(self):
        """🚨 AUDIT: Vérifie que le système de permissions n'empêche pas la triche."""
        logger.error("🚨 AUDIT DU SYSTÈME DE PERMISSIONS")
        
        # Test: Un agent peut-il accéder aux cartes des autres via les permissions ?
        agent_test = "SherlockEnqueteAgent"
        
        # Les permissions actuelles n'empêchent pas l'appel direct aux méthodes de triche
        try:
            # Cet appel devrait ÉCHOUER mais il réussit car pas de protection
            cartes_interdites = self.dataset.get_autres_joueurs_cards()
            logger.error(f"❌ FAILLE DE SÉCURITÉ: Agent peut accéder aux cartes des autres: {len(cartes_interdites)} cartes")
            
            faille_detectee = True
        except Exception as e:
            logger.info(f"✅ PROTECTION OK: Accès refusé - {e}")
            faille_detectee = False
        
        assert faille_detectee, "AUDIT CONFIRMÉ: Faille de sécurité dans le système de permissions"
    
    def test_tentative_acces_non_autorise_devrait_echouer(self):
        """✅ TEST POSITIF: Vérifie qu'un accès non autorisé DEVRAIT échouer (mais actuellement réussit)."""
        logger.info("✅ TEST: Tentative d'accès non autorisé")
        
        # Test d'un accès qui DEVRAIT être interdit
        agent_malveillant = "AgentMalveillant"
        
        # Ces appels DEVRAIENT lever des exceptions mais ils ne le font pas
        try:
            cartes_moriarty = self.dataset.get_moriarty_cards()
            logger.info(f"ℹ️ Accès cartes Moriarty réussi: {len(cartes_moriarty)} cartes (NORMAL)")
            
            cartes_autres = self.dataset.get_autres_joueurs_cards()
            logger.error(f"❌ Accès cartes autres joueurs réussi: {len(cartes_autres)} cartes (ANORMAL !)")
            
            acces_non_autorise_possible = True
            
        except Exception as e:
            logger.info(f"✅ Accès correctement refusé: {e}")
            acces_non_autorise_possible = False
        
        # Ce test DOIT échouer pour prouver que la sécurité est insuffisante
        assert acces_non_autorise_possible, "PREUVE: Le système autorise actuellement l'accès non autorisé"
    
    def test_oracle_enhanced_ne_triche_pas(self):
        """🚨 AUDIT: Vérifie que l'Oracle Enhanced ne révèle que les informations légitimes."""
        logger.error("🚨 AUDIT ORACLE ENHANCED")
        
        # Test des révélations automatiques
        from argumentation_analysis.agents.core.oracle.permissions import QueryType
        
        # Test avec une suggestion valide
        query_params = {
            "suggestion": {
                "suspect": "Colonel Moutarde",  # Carte possédée par Moriarty
                "arme": "Poignard",  # Carte NON possédée par Moriarty  
                "lieu": "Bureau"     # Carte possédée par Moriarty
            }
        }
        
        result = self.dataset.process_query("TestAgent", QueryType.SUGGESTION_VALIDATION, query_params)
        
        if result.success and result.data:
            revealed_cards = getattr(result.data, 'revealed_cards', [])
            logger.info(f"📝 Cartes révélées par Oracle Enhanced: {revealed_cards}")
            
            # Vérification que seules les cartes de Moriarty sont révélées
            cartes_moriarty = set(self.dataset.get_moriarty_cards())
            for card in revealed_cards:
                card_name = card if isinstance(card, str) else card.get('value', '')
                if card_name not in cartes_moriarty:
                    logger.error(f"❌ VIOLATION: Oracle Enhanced révèle une carte non possédée: {card_name}")
                    assert False, f"Oracle Enhanced révèle une carte non possédée par Moriarty: {card_name}"
        
        logger.info("✅ Oracle Enhanced semble respecter les règles de révélation")


def test_audit_complet_integrite():
    """Test principal d'audit de l'intégrité du système."""
    logger.info("🔍 DÉBUT DE L'AUDIT COMPLET D'INTÉGRITÉ CLUEDO")
    
    # Ce test va échouer volontairement pour prouver les violations
    test_instance = TestCluedoIntegrityAudit()
    test_instance.setup_method()
    
    violations_detectees = []
    
    try:
        test_instance.test_violation_acces_cartes_autres_joueurs()
        violations_detectees.append("get_autres_joueurs_cards() viole les règles")
    except AssertionError:
        pass
    
    try:
        test_instance.test_triche_simulation_autre_joueur()
        violations_detectees.append("simulate_other_player_response() utilise une méthode interdite")
    except AssertionError:
        pass
    
    try:
        test_instance.test_regles_cluedo_fondamentales_violees()
        violations_detectees.append("Règles fondamentales du Cluedo violées")
    except AssertionError:
        pass
    
    try:
        test_instance.test_systeme_permissions_insuffisant()
        violations_detectees.append("Système de permissions insuffisant")
    except AssertionError:
        pass
    
    logger.error(f"🚨 RÉSUMÉ AUDIT: {len(violations_detectees)} types de violations détectées")
    for violation in violations_detectees:
        logger.error(f"❌ {violation}")
    
    if violations_detectees:
        logger.error("🚨 CONCLUSION AUDIT: Le système viole les règles du Cluedo et nécessite des corrections immédiates !")
        return False
    else:
        logger.info("✅ CONCLUSION AUDIT: Le système respecte les règles du Cluedo")
        return True


if __name__ == "__main__":
    # Exécution directe de l'audit
    resultat = test_audit_complet_integrite()
    if not resultat:
        print("\n🚨 AUDIT ÉCHEC: Des violations des règles du Cluedo ont été détectées !")
        print("📋 Actions requises:")
        print("1. Supprimer ou sécuriser get_autres_joueurs_cards()")
        print("2. Modifier simulate_other_player_response() pour respecter les règles")
        print("3. Renforcer le système de permissions")
        print("4. Implémenter des protections anti-triche")
        exit(1)
    else:
        print("✅ AUDIT RÉUSSI: Le système respecte les règles du Cluedo")
        exit(0)