"""
Tests de performance pour le système de communication multi-canal.

Ces tests évaluent les performances du système de communication sous différentes charges
et configurations, mesurant des métriques comme le débit, la latence et l'utilisation
des ressources.
"""

import unittest
import time
import threading
import asyncio
import statistics
import concurrent.futures
from typing import List, Dict, Any, Tuple

from argumentiation_analysis.core.communication.message import (
    Message, MessageType, MessagePriority, AgentLevel
)
from argumentiation_analysis.core.communication.channel_interface import ChannelType
from argumentiation_analysis.core.communication.middleware import MessageMiddleware
from argumentiation_analysis.core.communication.hierarchical_channel import HierarchicalChannel
from argumentiation_analysis.core.communication.collaboration_channel import CollaborationChannel
from argumentiation_analysis.core.communication.data_channel import DataChannel
from argumentiation_analysis.core.communication.strategic_adapter import StrategicAdapter
from argumentiation_analysis.core.communication.tactical_adapter import TacticalAdapter
from argumentiation_analysis.core.communication.operational_adapter import OperationalAdapter

from argumentiation_analysis.paths import DATA_DIR



class TestCommunicationPerformance(unittest.TestCase):
    """Tests de performance pour le système de communication multi-canal."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer le middleware
        self.middleware = MessageMiddleware()
        
        # Enregistrer les canaux
        self.hierarchical_channel = HierarchicalChannel("hierarchical")
        self.collaboration_channel = CollaborationChannel("collaboration")
        self.data_channel = DataChannel(DATA_DIR)
        
        self.middleware.register_channel(self.hierarchical_channel)
        self.middleware.register_channel(self.collaboration_channel)
        self.middleware.register_channel(self.data_channel)
        
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
    
    def test_message_throughput(self):
        """Test du débit de messages."""
        # Paramètres du test
        num_messages = 1000
        num_senders = 5
        num_recipients = 5
        
        # Créer les adaptateurs pour les agents
        senders = [
            StrategicAdapter(f"strategic-agent-{i}", self.middleware)
            for i in range(num_senders)
        ]
        
        # Fonction pour envoyer des messages
        def send_messages(sender_idx, num_msgs_per_sender):
            sender = senders[sender_idx]
            start_time = time.time()
            
            for i in range(num_msgs_per_sender):
                recipient_idx = i % num_recipients
                
                # Envoyer un message
                sender.issue_directive(
                    directive_type="test_directive",
                    parameters={"test_id": f"test-{sender_idx}-{i}"},
                    recipient_id=f"tactical-agent-{recipient_idx}",
                    priority=MessagePriority.NORMAL
                )
            
            end_time = time.time()
            return end_time - start_time
        
        # Démarrer les threads pour envoyer des messages
        threads = []
        msgs_per_sender = num_messages // num_senders
        
        start_time = time.time()
        
        for i in range(num_senders):
            thread = threading.Thread(target=send_messages, args=(i, msgs_per_sender))
            threads.append(thread)
            thread.start()
        
        # Attendre que tous les threads se terminent
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Calculer le débit
        throughput = num_messages / total_time
        
        print(f"\nDébit de messages: {throughput:.2f} messages/seconde")
        print(f"Temps total: {total_time:.2f} secondes")
        
        # Vérifier que le débit est acceptable
        self.assertGreater(throughput, 100, "Le débit de messages est trop faible")
    
    def test_message_latency(self):
        """Test de la latence des messages."""
        # Paramètres du test
        num_messages = 100
        latencies = []
        
        # Créer les adaptateurs pour les agents
        sender = StrategicAdapter("strategic-agent", self.middleware)
        
        # Fonction pour recevoir des messages
        def receive_messages():
            tactical_adapter = TacticalAdapter("tactical-agent", self.middleware)
            
            for _ in range(num_messages):
                # Recevoir un message
                message = tactical_adapter.receive_directive(timeout=5.0)
                
                if message:
                    # Calculer la latence
                    send_time = float(message.metadata["send_time"])
                    receive_time = time.time()
                    latency = receive_time - send_time
                    latencies.append(latency)
        
        # Démarrer le thread pour recevoir des messages
        receiver_thread = threading.Thread(target=receive_messages)
        receiver_thread.start()
        
        # Envoyer des messages
        for i in range(num_messages):
            # Envoyer un message avec l'horodatage
            directive = Message(
                message_type=MessageType.COMMAND,
                sender="strategic-agent",
                sender_level=AgentLevel.STRATEGIC,
                content={"command_type": "test_directive", "parameters": {"test_id": f"test-{i}"}},
                recipient="tactical-agent",
                channel=ChannelType.HIERARCHICAL.value,
                priority=MessagePriority.NORMAL,
                metadata={"send_time": str(time.time())}
            )
            
            self.middleware.send_message(directive)
            
            # Petite pause pour éviter de surcharger le système
            time.sleep(0.01)
        
        # Attendre que le thread se termine
        receiver_thread.join()
        
        # Calculer les statistiques de latence
        avg_latency = statistics.mean(latencies) * 1000  # en millisecondes
        min_latency = min(latencies) * 1000
        max_latency = max(latencies) * 1000
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] * 1000
        
        print(f"\nLatence moyenne: {avg_latency:.2f} ms")
        print(f"Latence minimale: {min_latency:.2f} ms")
        print(f"Latence maximale: {max_latency:.2f} ms")
        print(f"Latence P95: {p95_latency:.2f} ms")
        
        # Vérifier que la latence est acceptable
        self.assertLess(avg_latency, 50, "La latence moyenne est trop élevée")
        self.assertLess(p95_latency, 100, "La latence P95 est trop élevée")
    
    def test_concurrent_channels(self):
        """Test des performances avec plusieurs canaux concurrents."""
        # Paramètres du test
        num_messages_per_channel = 500
        
        # Fonction pour envoyer des messages sur un canal
        def send_messages_on_channel(channel_type, num_messages):
            start_time = time.time()
            
            for i in range(num_messages):
                # Créer un message
                message = Message(
                    message_type=MessageType.INFORMATION,
                    sender=f"agent-{channel_type.value}-{i}",
                    sender_level=AgentLevel.SYSTEM,
                    content={"info_type": "test", DATA_DIR: {"value": i}},
                    recipient=f"recipient-{channel_type.value}",
                    channel=channel_type.value,
                    priority=MessagePriority.NORMAL
                )
                
                # Envoyer le message
                self.middleware.send_message(message)
            
            end_time = time.time()
            return end_time - start_time
        
        # Démarrer les threads pour envoyer des messages sur différents canaux
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(send_messages_on_channel, ChannelType.HIERARCHICAL, num_messages_per_channel),
                executor.submit(send_messages_on_channel, ChannelType.COLLABORATION, num_messages_per_channel),
                executor.submit(send_messages_on_channel, ChannelType.DATA, num_messages_per_channel)
            ]
            
            # Récupérer les résultats
            times = [future.result() for future in futures]
        
        # Calculer les débits par canal
        hierarchical_throughput = num_messages_per_channel / times[0]
        collaboration_throughput = num_messages_per_channel / times[1]
        data_throughput = num_messages_per_channel / times[2]
        
        # Calculer le débit total
        total_messages = num_messages_per_channel * 3
        total_time = max(times)
        total_throughput = total_messages / total_time
        
        print(f"\nDébit sur le canal hiérarchique: {hierarchical_throughput:.2f} messages/seconde")
        print(f"Débit sur le canal de collaboration: {collaboration_throughput:.2f} messages/seconde")
        print(f"Débit sur le canal de données: {data_throughput:.2f} messages/seconde")
        print(f"Débit total: {total_throughput:.2f} messages/seconde")
        
        # Vérifier que les débits sont acceptables
        self.assertGreater(hierarchical_throughput, 100, "Le débit sur le canal hiérarchique est trop faible")
        self.assertGreater(collaboration_throughput, 100, "Le débit sur le canal de collaboration est trop faible")
        self.assertGreater(data_throughput, 100, "Le débit sur le canal de données est trop faible")
        self.assertGreater(total_throughput, 300, "Le débit total est trop faible")
    
    def test_request_response_performance(self):
        """Test des performances du protocole de requête-réponse."""
        # Paramètres du test
        num_requests = 100
        response_times = []
        
        # Fonction pour traiter les requêtes
        def process_requests():
            # Recevoir et répondre aux requêtes
            for _ in range(num_requests):
                # Recevoir une requête
                request = self.middleware.receive_message(
                    recipient_id="responder",
                    channel_type=ChannelType.HIERARCHICAL,
                    timeout=5.0
                )
                
                if request:
                    # Créer une réponse
                    response = request.create_response(
                        content={"status": "success", DATA_DIR: {"value": request.content.get("value", 0) * 2}}
                    )
                    response.sender = "responder"
                    response.sender_level = AgentLevel.TACTICAL
                    
                    # Envoyer la réponse
                    self.middleware.send_message(response)
        
        # Démarrer le thread pour traiter les requêtes
        responder_thread = threading.Thread(target=process_requests)
        responder_thread.start()
        
        # Envoyer des requêtes et mesurer le temps de réponse
        for i in range(num_requests):
            start_time = time.time()
            
            # Envoyer une requête
            response = self.middleware.send_request(
                sender="requester",
                sender_level=AgentLevel.STRATEGIC,
                recipient="responder",
                request_type="test_request",
                content={"value": i},
                timeout=5.0,
                priority=MessagePriority.NORMAL,
                channel=ChannelType.HIERARCHICAL.value
            )
            
            end_time = time.time()
            
            # Vérifier que la réponse a été reçue
            self.assertIsNotNone(response)
            self.assertEqual(response.content["status"], "success")
            self.assertEqual(response.content[DATA_DIR]["value"], i * 2)
            
            # Calculer le temps de réponse
            response_time = end_time - start_time
            response_times.append(response_time)
        
        # Attendre que le thread se termine
        responder_thread.join()
        
        # Calculer les statistiques de temps de réponse
        avg_response_time = statistics.mean(response_times) * 1000  # en millisecondes
        min_response_time = min(response_times) * 1000
        max_response_time = max(response_times) * 1000
        p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)] * 1000
        
        print(f"\nTemps de réponse moyen: {avg_response_time:.2f} ms")
        print(f"Temps de réponse minimal: {min_response_time:.2f} ms")
        print(f"Temps de réponse maximal: {max_response_time:.2f} ms")
        print(f"Temps de réponse P95: {p95_response_time:.2f} ms")
        
        # Vérifier que les temps de réponse sont acceptables
        self.assertLess(avg_response_time, 100, "Le temps de réponse moyen est trop élevé")
        self.assertLess(p95_response_time, 200, "Le temps de réponse P95 est trop élevé")
    
    def test_publish_subscribe_performance(self):
        """Test des performances du protocole de publication-abonnement."""
        # Paramètres du test
        num_publications = 100
        num_subscribers = 10
        received_counts = [0] * num_subscribers
        
        # Créer les callbacks pour les abonnés
        callbacks = []
        for i in range(num_subscribers):
            def make_callback(idx):
                def callback(message):
                    received_counts[idx] += 1
                return callback
            
            callbacks.append(make_callback(i))
        
        # S'abonner au topic
        for i in range(num_subscribers):
            self.middleware.subscribe(
                subscriber_id=f"subscriber-{i}",
                topic_id="test_topic",
                callback=callbacks[i]
            )
        
        # Publier des messages
        start_time = time.time()
        
        for i in range(num_publications):
            # Publier un message
            self.middleware.publish(
                topic_id="test_topic",
                sender="publisher",
                sender_level=AgentLevel.SYSTEM,
                content={"value": i},
                priority=MessagePriority.NORMAL
            )
        
        end_time = time.time()
        publish_time = end_time - start_time
        
        # Attendre que tous les messages soient traités
        time.sleep(1.0)
        
        # Calculer le débit de publication
        publish_throughput = num_publications / publish_time
        
        # Vérifier que tous les abonnés ont reçu tous les messages
        for i in range(num_subscribers):
            self.assertEqual(received_counts[i], num_publications,
                            f"L'abonné {i} n'a pas reçu tous les messages")
        
        print(f"\nDébit de publication: {publish_throughput:.2f} messages/seconde")
        print(f"Nombre total de messages traités: {num_publications * num_subscribers}")
        
        # Vérifier que le débit est acceptable
        self.assertGreater(publish_throughput, 100, "Le débit de publication est trop faible")
    
    def test_data_channel_performance(self):
        """Test des performances du canal de données."""
        # Paramètres du test
        num_data_objects = 50
        data_sizes = [1024, 10240, 102400]  # Tailles en octets
        
        for size in data_sizes:
            # Créer des données de test
            test_data = {DATA_DIR: "x" * size}
            
            # Mesurer le temps de stockage
            start_time = time.time()
            
            for i in range(num_data_objects):
                # Stocker les données
                self.data_channel.store_data(
                    data_id=f"test-data-{size}-{i}",
                    data=test_data,
                    metadata={"size": size}
                )
            
            end_time = time.time()
            store_time = end_time - start_time
            
            # Mesurer le temps de récupération
            start_time = time.time()
            
            for i in range(num_data_objects):
                # Récupérer les données
                data = self.data_channel.get_data(
                    data_id=f"test-data-{size}-{i}"
                )
                
                # Vérifier que les données sont correctes
                self.assertEqual(len(data[DATA_DIR]), size)
            
            end_time = time.time()
            retrieve_time = end_time - start_time
            
            # Calculer les débits
            store_throughput = (num_data_objects * size) / (store_time * 1024 * 1024)  # en Mo/s
            retrieve_throughput = (num_data_objects * size) / (retrieve_time * 1024 * 1024)  # en Mo/s
            
            print(f"\nTaille des données: {size} octets")
            print(f"Débit de stockage: {store_throughput:.2f} Mo/s")
            print(f"Débit de récupération: {retrieve_throughput:.2f} Mo/s")
            
            # Vérifier que les débits sont acceptables
            self.assertGreater(store_throughput, 1.0, f"Le débit de stockage pour {size} octets est trop faible")
            self.assertGreater(retrieve_throughput, 1.0, f"Le débit de récupération pour {size} octets est trop faible")
    
    def test_scalability(self):
        """Test de la scalabilité du système."""
        # Paramètres du test
        agent_counts = [10, 50, 100]
        messages_per_agent = 10
        
        for count in agent_counts:
            # Créer les adaptateurs pour les agents
            strategic_adapters = [
                StrategicAdapter(f"strategic-agent-{i}", self.middleware)
                for i in range(count)
            ]
            
            tactical_adapters = [
                TacticalAdapter(f"tactical-agent-{i}", self.middleware)
                for i in range(count)
            ]
            
            # Fonction pour envoyer des messages
            def send_messages(adapter_idx):
                adapter = strategic_adapters[adapter_idx]
                
                for i in range(messages_per_agent):
                    # Envoyer un message
                    adapter.issue_directive(
                        directive_type="test_directive",
                        parameters={"test_id": f"test-{adapter_idx}-{i}"},
                        recipient_id=f"tactical-agent-{adapter_idx}",
                        priority=MessagePriority.NORMAL
                    )
            
            # Fonction pour recevoir des messages
            def receive_messages(adapter_idx):
                adapter = tactical_adapters[adapter_idx]
                
                for _ in range(messages_per_agent):
                    # Recevoir un message
                    message = adapter.receive_directive(timeout=5.0)
                    
                    # Vérifier que le message a été reçu
                    self.assertIsNotNone(message)
            
            # Démarrer les threads pour recevoir des messages
            receiver_threads = []
            
            for i in range(count):
                thread = threading.Thread(target=receive_messages, args=(i,))
                receiver_threads.append(thread)
                thread.start()
            
            # Démarrer les threads pour envoyer des messages
            sender_threads = []
            
            start_time = time.time()
            
            for i in range(count):
                thread = threading.Thread(target=send_messages, args=(i,))
                sender_threads.append(thread)
                thread.start()
            
            # Attendre que tous les threads se terminent
            for thread in sender_threads:
                thread.join()
            
            for thread in receiver_threads:
                thread.join()
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Calculer le débit
            total_messages = count * messages_per_agent
            throughput = total_messages / total_time
            
            print(f"\nNombre d'agents: {count}")
            print(f"Débit total: {throughput:.2f} messages/seconde")
            print(f"Débit par agent: {throughput / count:.2f} messages/seconde/agent")
            
            # Vérifier que le débit est acceptable
            self.assertGreater(throughput, count * 10, f"Le débit pour {count} agents est trop faible")


class TestAsyncCommunicationPerformance(unittest.IsolatedAsyncioTestCase):
    """Tests de performance pour la communication asynchrone."""
    
    async def asyncSetUp(self):
        """Initialisation asynchrone avant chaque test."""
        # Créer le middleware
        self.middleware = MessageMiddleware()
        
        # Enregistrer les canaux
        self.hierarchical_channel = HierarchicalChannel("hierarchical")
        self.middleware.register_channel(self.hierarchical_channel)
        
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
    
    async def test_async_request_response_performance(self):
        """Test des performances du protocole de requête-réponse asynchrone."""
        # Paramètres du test
        num_requests = 100
        concurrency = 10
        response_times = []
        
        # Fonction pour traiter les requêtes
        async def process_requests():
            # Recevoir et répondre aux requêtes
            for _ in range(num_requests):
                # Recevoir une requête
                request = await self.middleware.receive_message_async(
                    recipient_id="responder",
                    channel_type=ChannelType.HIERARCHICAL,
                    timeout=5.0
                )
                
                if request:
                    # Créer une réponse
                    response = request.create_response(
                        content={"status": "success", DATA_DIR: {"value": request.content.get("value", 0) * 2}}
                    )
                    response.sender = "responder"
                    response.sender_level = AgentLevel.TACTICAL
                    
                    # Envoyer la réponse
                    self.middleware.send_message(response)
        
        # Démarrer la tâche pour traiter les requêtes
        responder_task = asyncio.create_task(process_requests())
        
        # Fonction pour envoyer une requête
        async def send_request(i):
            start_time = time.time()
            
            # Envoyer une requête
            response = await self.middleware.send_request_async(
                sender="requester",
                sender_level=AgentLevel.STRATEGIC,
                recipient="responder",
                request_type="test_request",
                content={"value": i},
                timeout=5.0,
                priority=MessagePriority.NORMAL,
                channel=ChannelType.HIERARCHICAL.value
            )
            
            end_time = time.time()
            
            # Vérifier que la réponse a été reçue
            self.assertIsNotNone(response)
            self.assertEqual(response.content["status"], "success")
            self.assertEqual(response.content[DATA_DIR]["value"], i * 2)
            
            # Calculer le temps de réponse
            response_time = end_time - start_time
            response_times.append(response_time)
        
        # Envoyer des requêtes en parallèle
        tasks = []
        for i in range(num_requests):
            if len(tasks) >= concurrency:
                # Attendre qu'une tâche se termine avant d'en démarrer une nouvelle
                done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            
            # Démarrer une nouvelle tâche
            task = asyncio.create_task(send_request(i))
            tasks.append(task)
        
        # Attendre que toutes les tâches se terminent
        if tasks:
            await asyncio.wait(tasks)
        
        # Annuler la tâche de traitement des requêtes
        responder_task.cancel()
        try:
            await responder_task
        except asyncio.CancelledError:
            pass
        
        # Calculer les statistiques de temps de réponse
        avg_response_time = statistics.mean(response_times) * 1000  # en millisecondes
        min_response_time = min(response_times) * 1000
        max_response_time = max(response_times) * 1000
        p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)] * 1000
        
        print(f"\nTemps de réponse moyen (async): {avg_response_time:.2f} ms")
        print(f"Temps de réponse minimal (async): {min_response_time:.2f} ms")
        print(f"Temps de réponse maximal (async): {max_response_time:.2f} ms")
        print(f"Temps de réponse P95 (async): {p95_response_time:.2f} ms")
        
        # Vérifier que les temps de réponse sont acceptables
        self.assertLess(avg_response_time, 100, "Le temps de réponse moyen est trop élevé")
        self.assertLess(p95_response_time, 200, "Le temps de réponse P95 est trop élevé")


if __name__ == "__main__":
    unittest.main()