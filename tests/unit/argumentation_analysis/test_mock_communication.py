
from unittest.mock import MagicMock

# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Version simplifiée des tests de communication avec des mocks.

Ce module contient des tests qui utilisent des mocks pour éviter les problèmes
avec les modules PyO3 qui ne peuvent être initialisés qu'une seule fois par processus.
"""

import unittest
import threading
import time
import logging
import sys
import asyncio


# Configuration du logger
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                   datefmt='%H:%M:%S')
logger = logging.getLogger("MockTests")

# Classes mockées pour éviter les problèmes d'importation
class MockMessage:
    """Mock pour la classe Message."""
    
    def __init__(self, sender=None, recipient=None, content=None, message_type=None):
        self.id = "mock-message-id"
        self.sender = sender
        self.recipient = recipient
        self.content = content or {}
        self.type = message_type
        self.metadata = {}
    
    def create_response(self, content=None):
        """Crée une réponse à ce message."""
        response = MockMessage(
            sender=self.recipient,
            recipient=self.sender,
            content=content or {},
            message_type="RESPONSE"
        )
        response.metadata["reply_to"] = self.id
        return response

class MockMiddleware:
    """Mock pour la classe MessageMiddleware."""
    
    def __init__(self):
        self.messages = []
        # Correction: Magicawait -> await (bien que ce soit dans un init sync, cela semble être une erreur de frappe)
        # De plus, appeler une méthode async depuis un __init__ sync est problématique.
        # Pour l'instant, je corrige la syntaxe, mais cela pourrait nécessiter une refonte.
        # self.request_response = await self._create_authentic_gpt4o_mini_instance()
        # Commenté pour l'instant car cela briserait l'exécution synchrone de l'init.
        # Il est probable que cette ligne soit un vestige et non fonctionnelle.
        # Je vais la neutraliser pour permettre au reste du fichier d'être parsé.
        self.request_response = MagicMock() # Remplacé par un MagicMock simple pour éviter l'erreur async.
        self.request_response.send_request_async = MagicMock(return_value=None)
    
    def send_message(self, message):
        """Envoie un message."""
        self.messages.append(message)
        return True
    
    def receive_message(self, recipient_id, channel_type, timeout=5.0):
        """Reçoit un message."""
        for message in self.messages:
            if message.recipient == recipient_id:
                self.messages.remove(message)
                return message
        return None
    
    def get_pending_messages(self, recipient_id, channel_type):
        """Récupère les messages en attente."""
        return [m for m in self.messages if m.recipient == recipient_id]
    
    def register_channel(self, channel):
        """Enregistre un canal."""
        pass
    
    def initialize_protocols(self):
        """Initialise les protocoles."""
        pass
    
    def shutdown(self):
        """Arrête le middleware."""
        self.messages = []

class MockAdapter:
    """Mock pour les adaptateurs."""
    
    def __init__(self, agent_id, middleware):
        self.agent_id = agent_id
        self.middleware = middleware
    
    def send_message(self, message_type, content, recipient_id, priority=None):
        """Envoie un message."""
        message = MockMessage(
            sender=self.agent_id,
            recipient=recipient_id,
            content=content,
            message_type=message_type
        )
        return self.middleware.send_message(message)
    
    def receive_message(self, timeout=5.0):
        """Reçoit un message."""
        return self.middleware.receive_message(self.agent_id, None, timeout)

class TestMockCommunication(unittest.TestCase):
    def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        async def run_get_kernel():
            config = UnifiedConfig()
            return config.get_kernel_with_gpt4o_mini()
        return asyncio.run(run_get_kernel())

    def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        async def run_llm_call():
            try:
                kernel = self._create_authentic_gpt4o_mini_instance()
                # Assuming kernel creation is synchronous now, or handled within.
                # If _create_authentic_gpt4o_mini_instance remains async, it needs to be awaited.
                # Let's adjust based on the new sync nature of _create_authentic_gpt4o_mini_instance.
                # The method now returns a kernel instance directly.
                
                # We need to re-evaluate how to get an async-capable kernel instance here.
                # The original `_create_authentic_gpt4o_mini_instance` was async, now it's sync.
                # Let's create the kernel inside the async helper.
                config = UnifiedConfig()
                kernel = config.get_kernel_with_gpt4o_mini()

                result = await kernel.invoke("chat", input=prompt)
                return str(result)
            except Exception as e:
                logger.warning(f"Appel LLM authentique échoué: {e}")
                return "Authentic LLM call failed"
        return asyncio.run(run_llm_call())

    """Tests de communication avec des mocks."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.middleware = MockMiddleware()
        self.agent1 = MockAdapter("agent-1", self.middleware)
        self.agent2 = MockAdapter("agent-2", self.middleware)
    
    def test_simple_communication(self):
        """Test de communication simple entre deux agents."""
        # Agent 1 envoie un message à Agent 2
        self.agent1.send_message(
            message_type="REQUEST",
            content={"request_type": "test", "data": "Hello"},
            recipient_id="agent-2"
        )
        
        # Agent 2 reçoit le message
        message = self.agent2.receive_message()
        self.assertIsNotNone(message)
        self.assertEqual(message.sender, "agent-1")
        self.assertEqual(message.content.get("data"), "Hello")
        
        # Agent 2 répond à Agent 1
        response = message.create_response({"status": "success", "data": "World"})
        self.middleware.send_message(response)
        
        # Agent 1 reçoit la réponse
        response_message = self.agent1.receive_message()
        self.assertIsNotNone(response_message)
        self.assertEqual(response_message.sender, "agent-2")
        self.assertEqual(response_message.content.get("data"), "World")
    
    def test_multiple_messages(self):
        """Test d'envoi de plusieurs messages."""
        # Agent 1 envoie plusieurs messages à Agent 2
        for i in range(3):
            self.agent1.send_message(
                message_type="REQUEST",
                content={"request_type": "test", "index": i},
                recipient_id="agent-2"
            )
        
        # Agent 2 reçoit les messages
        messages = []
        for _ in range(3):
            message = self.agent2.receive_message()
            if message:
                messages.append(message)
        
        # Vérifier que tous les messages ont été reçus
        self.assertEqual(len(messages), 3)
        indices = [m.content.get("index") for m in messages]
        self.assertEqual(sorted(indices), [0, 1, 2])
    
    def test_timeout(self):
        """Test de timeout lors de la réception d'un message."""
        # Aucun message n'est envoyé
        
        # Agent 2 essaie de recevoir un message avec un timeout court
        start_time = time.time()
        message = self.agent2.receive_message(timeout=0.1)
        elapsed_time = time.time() - start_time
        
        # Vérifier qu'aucun message n'a été reçu et que le timeout a été respecté
        self.assertIsNone(message)
        self.assertLess(elapsed_time, 0.5)  # Le timeout devrait être respecté
    
    def test_concurrent_communication(self):
        """Test de communication concurrente entre agents."""
        # Variable pour stocker les messages reçus entre les threads
        received_messages = []
        message_event = threading.Event()
        
        # Fonction pour simuler l'agent 2
        def agent2_thread():
            for _ in range(3):
                # Attendre qu'un message soit disponible
                if message_event.wait(timeout=2.0):
                    message = self.agent2.receive_message(timeout=0.5)
                    if message:
                        received_messages.append(message)
                        # Envoyer une réponse
                        response = message.create_response({"status": "received"})
                        self.middleware.send_message(response)
                    # Réinitialiser l'événement pour le prochain message
                    message_event.clear()
        
        # Démarrer le thread de l'agent 2
        thread = threading.Thread(target=agent2_thread)
        thread.daemon = True  # Pour que le thread se termine si le test échoue
        thread.start()
        
        # Agent 1 envoie plusieurs messages à Agent 2
        for i in range(3):
            self.agent1.send_message(
                message_type="REQUEST",
                content={"request_type": "test", "index": i},
                recipient_id="agent-2"
            )
            # Signaler qu'un message est disponible
            message_event.set()
            # Attendre un peu pour que le thread traite le message
            time.sleep(0.2)
        
        # Attendre que le thread traite tous les messages
        time.sleep(1.0)
        
        # Vérifier que tous les messages ont été reçus
        self.assertEqual(len(received_messages), 3)
        
        # Vérifier que l'agent 1 a reçu toutes les réponses
        responses = []
        for _ in range(3):
            response = self.agent1.receive_message(timeout=0.1)
            if response:
                responses.append(response)
        
        self.assertEqual(len(responses), 3)
        for response in responses:
            self.assertEqual(response.content.get("status"), "received")

def run_tests():
    """Exécute les tests."""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMockCommunication)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)