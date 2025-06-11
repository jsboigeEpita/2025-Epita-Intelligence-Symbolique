"""Test d'intégration rapide des composants JTMS"""

try:
    from argumentation_analysis.agents.sherlock_jtms_agent import SherlockJTMSAgent
    print("✅ SherlockJTMSAgent importé avec succès")
except Exception as e:
    print(f"❌ Erreur import SherlockJTMSAgent: {e}")

try:
    from argumentation_analysis.agents.watson_jtms_agent import WatsonJTMSAgent
    print("✅ WatsonJTMSAgent importé avec succès")
except Exception as e:
    print(f"❌ Erreur import WatsonJTMSAgent: {e}")

try:
    from argumentation_analysis.agents.jtms_communication_hub import JTMSCommunicationHub
    print("✅ JTMSCommunicationHub importé avec succès")
except Exception as e:
    print(f"❌ Erreur import JTMSCommunicationHub: {e}")

try:
    from argumentation_analysis.agents.jtms_agent_base import JTMSAgentBase
    print("✅ JTMSAgentBase importé avec succès")
except Exception as e:
    print(f"❌ Erreur import JTMSAgentBase: {e}")

print("\n🎯 TEST D'INTÉGRATION COMPOSANTS JTMS TERMINÉ")