import unittest
import threading
import time
import logging

from argumentation_analysis.core.communication.message import Message, MessageType, AgentLevel, MessagePriority
from argumentation_analysis.core.communication.middleware import MessageMiddleware
from argumentation_analysis.core.communication.operational_adapter import OperationalAdapter
from argumentation_analysis.core.communication.hierarchical_channel import HierarchicalChannel
from argumentation_analysis.core.communication.channel_interface import ChannelType


# Configuration du logger
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger("CommunicationIntegrationTests")


class TestCommunicationIntegration(unittest.TestCase):
    """Tests d'intégration pour la communication entre agents."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.middleware = MessageMiddleware()
        self.hierarchical_channel = HierarchicalChannel(channel_id="hierarchical-test-channel", config={})
        self.middleware.register_channel(self.hierarchical_channel)
        self.middleware.initialize_protocols() # Important pour request-response

        self.agent1_id = "agent-op-1"
        self.agent2_id = "agent-op-2"
        
        # Les adaptateurs ne sont pas strictement nécessaires si on utilise directement le middleware pour les tests d'intégration bas niveau,
        # mais ils peuvent être utiles pour simuler le comportement d'un agent.
        # Pour ce premier test, nous allons interagir plus directement avec le middleware pour contrôler le flux.
        # self.adapter1 = OperationalAdapter(self.agent1_id, self.middleware)
        # self.adapter2 = OperationalAdapter(self.agent2_id, self.middleware)

    def tearDown(self):
        """Nettoyage après chaque test."""
        self.middleware.shutdown()

    def test_simple_communication_integration(self):
        """Test de communication simple requête-réponse entre deux agents."""
        
        original_request_id_store = {}
        response_from_send_request_store = {}
        send_request_finished_event = threading.Event()
        agent1_listener_stop_event = threading.Event()

        def agent2_responder_thread_func():
            request_msg = self.middleware.receive_message(
                recipient_id=self.agent2_id,
                channel_type=ChannelType.HIERARCHICAL,
                timeout=5.0
            )
            self.assertIsNotNone(request_msg, "Agent 2 n'a pas reçu de message de requête")
            if not request_msg: return

            self.assertEqual(request_msg.sender, self.agent1_id)
            self.assertEqual(request_msg.type, MessageType.REQUEST)
            original_request_id_store['id'] = request_msg.id
            
            response_content = {"status": "success", "data": "World"}
            actual_response_msg = request_msg.create_response(
                content=response_content,
                sender_level=AgentLevel.OPERATIONAL
            )
            actual_response_msg.sender = self.agent2_id
            self.middleware.send_message(actual_response_msg)

        def agent1_main_send_request_func():
            request_content = {"request_type": "test_data_request", "data": "Hello"}
            response = self.middleware.send_request(
                sender=self.agent1_id,
                sender_level=AgentLevel.OPERATIONAL,
                recipient=self.agent2_id,
                request_type="test_data_request",
                content=request_content,
                timeout=7.0,
                channel=ChannelType.HIERARCHICAL.value
            )
            response_from_send_request_store['response'] = response
            send_request_finished_event.set()

        def agent1_listener_func():
            # Ce thread pompe les messages pour agent1, permettant à RRP.handle_response d'être appelé.
            while not agent1_listener_stop_event.is_set() and not send_request_finished_event.is_set():
                self.middleware.receive_message(recipient_id=self.agent1_id, timeout=0.1)
        
        responder_thread = threading.Thread(target=agent2_responder_thread_func)
        agent1_main_thread = threading.Thread(target=agent1_main_send_request_func)
        agent1_listener_thread = threading.Thread(target=agent1_listener_func)

        responder_thread.start()
        agent1_listener_thread.start() # Démarrer le listener avant l'appel bloquant
        agent1_main_thread.start()

        # Attendre que send_request (dans agent1_main_thread) se termine
        send_request_finished_event.wait(timeout=10.0) # Timeout global pour le test
        
        agent1_listener_stop_event.set() # Arrêter le listener d'agent1

        # Joindre les threads
        responder_thread.join(timeout=2.0)
        agent1_listener_thread.join(timeout=2.0)
        agent1_main_thread.join(timeout=2.0) # Devrait être déjà terminé si l'événement est mis

        self.assertTrue(send_request_finished_event.is_set(), "send_request n'a pas terminé ou a expiré.")
        response_message = response_from_send_request_store.get('response')

        self.assertIsNotNone(response_message, "Agent 1 n'a pas reçu de réponse via send_request")
        if not response_message: return

        self.assertEqual(response_message.sender, self.agent2_id)
        self.assertIn('id', original_request_id_store, "L'ID de la requête originale n'a pas été stocké par agent2.")
        self.assertTrue(response_message.is_response_to(original_request_id_store['id']),
                        f"La réponse {response_message.id} (reply_to: {response_message.metadata.get('reply_to')}) "
                        f"ne correspond pas à la requête {original_request_id_store.get('id')}")
        self.assertEqual(response_message.content.get("status"), "success")
        self.assertEqual(response_message.content.get("data"), "World")

    def test_multiple_messages_integration(self):
        """Test d'envoi et de réception de plusieurs messages."""
        num_messages = 3
        received_messages_agent2 = []
        
        # Agent 1 envoie plusieurs messages à Agent 2
        for i in range(num_messages):
            message_content = {"request_type": "multi_msg_test", "index": i}
            msg = Message(
                message_type=MessageType.INFORMATION, # Ou COMMAND, selon le scénario
                sender=self.agent1_id,
                sender_level=AgentLevel.OPERATIONAL,
                content=message_content,
                recipient=self.agent2_id,
                channel=ChannelType.HIERARCHICAL.value
            )
            send_success = self.middleware.send_message(msg)
            self.assertTrue(send_success, f"L'envoi du message {i} par l'Agent 1 a échoué")

        # Agent 2 reçoit les messages
        for _ in range(num_messages):
            # Utiliser un timeout pour éviter un blocage infini si un message n'arrive pas
            message = self.middleware.receive_message(
                recipient_id=self.agent2_id,
                channel_type=ChannelType.HIERARCHICAL,
                timeout=1.0  # Timeout court pour chaque message
            )
            if message:
                received_messages_agent2.append(message)
            else:
                # Si un message n'est pas reçu dans le délai, le test échouera à l'assertion de longueur
                logger.warning(f"Agent 2 n'a pas reçu un message attendu dans le délai imparti.")
                break
        
        self.assertEqual(len(received_messages_agent2), num_messages,
                         f"Agent 2 n'a pas reçu tous les messages. Reçus: {len(received_messages_agent2)}, Attendus: {num_messages}")
        
        # Vérifier le contenu des messages reçus
        indices = sorted([m.content.get("index") for m in received_messages_agent2 if m.content])
        expected_indices = list(range(num_messages))
        self.assertEqual(indices, expected_indices,
                         f"Les indices des messages reçus ne correspondent pas. Reçus: {indices}, Attendus: {expected_indices}")

    def test_timeout_integration(self):
        """Test de timeout lors de la réception d'un message."""
        # Aucun message n'est envoyé à agent2_id sur le canal HIERARCHICAL
        
        start_time = time.time()
        # Agent 2 essaie de recevoir un message avec un timeout court
        message = self.middleware.receive_message(
            recipient_id=self.agent2_id, # L'agent qui attend un message
            channel_type=ChannelType.HIERARCHICAL,
            timeout=0.1  # Timeout court
        )
        elapsed_time = time.time() - start_time
        
        # Vérifier qu'aucun message n'a été reçu
        self.assertIsNone(message, "Un message a été reçu alors qu'aucun n'était attendu.")
        
        # Vérifier que le timeout a été respecté (avec une petite marge)
        # Le temps écoulé doit être au moins égal au timeout, et pas beaucoup plus.
        self.assertGreaterEqual(elapsed_time, 0.1, "Le délai de réception était plus court que le timeout spécifié.")
        self.assertLess(elapsed_time, 0.5, "Le délai de réception était significativement plus long que le timeout.")

    def test_concurrent_communication_integration(self):
        """Test de communication concurrente requête-réponse."""
        num_concurrent_messages = 3
        responses_received_by_agent1 = [None] * num_concurrent_messages
        agent1_send_request_threads = []
        agent1_listener_stop_event = threading.Event()
        all_agent1_sends_finished_event = threading.Event()
        
        # Listener pour Agent1 pour pomper les messages et permettre à RRP.handle_response de fonctionner
        def agent1_listener_func_concurrent():
            processed_responses_count = 0
            while not agent1_listener_stop_event.is_set() and processed_responses_count < num_concurrent_messages:
                msg = self.middleware.receive_message(recipient_id=self.agent1_id, timeout=0.1)
                if msg and msg.type == MessageType.RESPONSE:
                     # Le RRP.handle_response sera appelé par le middleware.receive_message
                    processed_responses_count +=1
                elif all_agent1_sends_finished_event.is_set() and processed_responses_count >= num_concurrent_messages:
                    break # Tous les sends sont finis et on a traité assez de réponses

        agent1_listener_thread_concurrent = threading.Thread(target=agent1_listener_func_concurrent)

        def agent2_concurrent_responder_func(index):
            request_msg = self.middleware.receive_message(
                recipient_id=self.agent2_id,
                channel_type=ChannelType.HIERARCHICAL,
                timeout=5.0
            )
            if request_msg:
                response_content = {"status": "received_concurrently", "original_index": request_msg.content.get("index")}
                actual_response_msg = request_msg.create_response(content=response_content, sender_level=AgentLevel.OPERATIONAL)
                actual_response_msg.sender = self.agent2_id
                self.middleware.send_message(actual_response_msg)
            else:
                logger.warning(f"Agent2 (thread {index}) n'a pas reçu de message.")

        agent2_responder_threads = []
        for i in range(num_concurrent_messages):
            thread = threading.Thread(target=agent2_concurrent_responder_func, args=(i,))
            agent2_responder_threads.append(thread)
            thread.start()
        
        agent1_listener_thread_concurrent.start() # Démarrer le listener d'Agent1

        def agent1_send_request_concurrent_func(index):
            request_content = {"request_type": "concurrent_test", "index": index}
            response = self.middleware.send_request(
                sender=self.agent1_id,
                sender_level=AgentLevel.OPERATIONAL,
                recipient=self.agent2_id,
                request_type="concurrent_test",
                content=request_content,
                timeout=10.0, # Augmenté pour la concurrence
                channel=ChannelType.HIERARCHICAL.value
            )
            if response:
                responses_received_by_agent1[index] = response
            else:
                logger.warning(f"Agent1 n'a pas reçu de réponse pour l'index {index} dans send_request.")

        for i in range(num_concurrent_messages):
            thread = threading.Thread(target=agent1_send_request_concurrent_func, args=(i,))
            agent1_send_request_threads.append(thread)
            thread.start()

        # Attendre que tous les threads d'envoi de l'agent1 se terminent
        for thread in agent1_send_request_threads:
            thread.join(timeout=12.0)
        
        all_agent1_sends_finished_event.set() # Signaler que tous les sends sont terminés
        agent1_listener_stop_event.set() # Arrêter le listener d'Agent1
        agent1_listener_thread_concurrent.join(timeout=2.0)

        for thread in agent2_responder_threads:
            thread.join(timeout=2.0)

        # Filtrer les None au cas où certains send_request auraient timeout
        valid_responses = [r for r in responses_received_by_agent1 if r is not None]
        self.assertEqual(len(valid_responses), num_concurrent_messages,
                         f"Agent 1 n'a pas reçu toutes les réponses. Reçues: {len(valid_responses)}, Attendues: {num_concurrent_messages}. "
                         f"Détails: {[r.id if r else None for r in responses_received_by_agent1]}")

        received_indices = sorted([r.content.get("original_index") for r in valid_responses if r.content])
        expected_indices = list(range(num_concurrent_messages))
        self.assertEqual(received_indices, expected_indices,
                         f"Les indices originaux dans les réponses ne correspondent pas. Reçus: {received_indices}, Attendus: {expected_indices}")
        for r in valid_responses:
            self.assertEqual(r.content.get("status"), "received_concurrently")

if __name__ == "__main__":
    unittest.main()