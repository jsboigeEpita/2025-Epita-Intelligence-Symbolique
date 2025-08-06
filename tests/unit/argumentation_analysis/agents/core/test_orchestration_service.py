import unittest
import pytest
from unittest.mock import Mock, PropertyMock
import threading

# Il faut s'assurer que OrchestrationService._instance est réinitialisé avant chaque test
# pour garantir l'isolation des tests du Singleton.
from argumentation_analysis.agents.core.orchestration_service import OrchestrationService, BasePlugin, PluginDependencyError

class TestOrchestrationService(unittest.TestCase):

    def setUp(self):
        """Réinitialise l'instance Singleton avant chaque test."""
        OrchestrationService._instance = None

    def test_singleton_get_instance_returns_same_instance(self):
        """Vérifie que get_instance() retourne toujours la même instance."""
        instance1 = OrchestrationService.get_instance()
        instance2 = OrchestrationService.get_instance()
        self.assertIs(instance1, instance2)

    def test_singleton_is_thread_safe(self):
        """Vérifie que le Singleton est thread-safe."""
        instances = []
        def get_instance_in_thread():
            instances.append(OrchestrationService.get_instance())

        threads = [threading.Thread(target=get_instance_in_thread) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        first_instance = instances[0]
        for i in range(1, len(instances)):
            self.assertIs(first_instance, instances[i])

    def test_register_and_get_plugin(self):
        """Teste l'enregistrement et la récupération d'un plugin."""
        service = OrchestrationService.get_instance()
        
        # Créer un plugin factice (mock)
        mock_plugin = Mock(spec=BasePlugin)
        mock_plugin.name = "TestPlugin"
        
        # Enregistrer le plugin
        service.register_plugin(mock_plugin)
        
        # Récupérer le plugin et vérifier que c'est le bon
        retrieved_plugin = service.get_plugin("TestPlugin")
        self.assertIs(retrieved_plugin, mock_plugin)

    def test_get_nonexistent_plugin_returns_none(self):
        """Teste que la récupération d'un plugin non enregistré retourne None."""
        service = OrchestrationService.get_instance()
        retrieved_plugin = service.get_plugin("NonExistentPlugin")
        self.assertIsNone(retrieved_plugin)
        
    def test_register_invalid_plugin_raises_error(self):
        """Vérifie qu'enregistrer un plugin invalide (None) lève une TypeError."""
        service = OrchestrationService.get_instance()
        
        with self.assertRaises(TypeError):
            service.register_plugin(None)

    def test_register_plugin_without_name_raises_error(self):
        """Vérifie qu'enregistrer un plugin sans nom lève une ValueError."""
        service = OrchestrationService.get_instance()
            
        invalid_plugin = Mock(spec=BasePlugin)
        # Assurer que l'attribut 'name' existe mais est vide, pour passer le isinstance
        type(invalid_plugin).name = PropertyMock(return_value="")
        with self.assertRaises(ValueError):
            service.register_plugin(invalid_plugin)

    def test_register_duplicate_plugin_raises_error(self):
        """Vérifie que l'enregistrement d'un plugin avec un nom existant lève une ValueError."""
        service = OrchestrationService.get_instance()
        
        # Créer et enregistrer un premier plugin
        plugin1 = Mock(spec=BasePlugin)
        plugin1.name = "DuplicateNamePlugin"
        service.register_plugin(plugin1)
        
        # Créer un deuxième plugin avec le même nom
        plugin2 = Mock(spec=BasePlugin)
        plugin2.name = "DuplicateNamePlugin"
        
        # Vérifier que l'enregistrement du deuxième plugin lève une ValueError
        with self.assertRaises(ValueError):
            service.register_plugin(plugin2)

    def test_execute_plugin_with_missing_dependency_raises_error(self):
        """
        Vérifie que l'exécution d'un plugin avec une dépendance manquante
        lève bien une PluginDependencyError.
        """
        service = OrchestrationService.get_instance()

        # 1. Créer un mock pour un plugin principal qui a une dépendance
        main_plugin = Mock(spec=BasePlugin)
        main_plugin.name = "MainPluginWithDependency"
        
        # Simuler la propriété 'dependencies' pour qu'elle retourne une dépendance
        type(main_plugin).dependencies = PropertyMock(return_value=["LoggerPlugin"])

        # 2. Ne PAS enregistrer le plugin dépendant (LoggerPlugin)

        # 3. Enregistrer uniquement le plugin principal
        service.register_plugin(main_plugin)

        # 4. Vérifier que PluginDependencyError est levée lors de l'exécution
        with pytest.raises(PluginDependencyError, match="Dépendance non satisfaite : le plugin 'LoggerPlugin' requis par 'MainPluginWithDependency' est introuvable."):
            service.execute_plugin(plugin_name="MainPluginWithDependency")


class TestOrchestrationServiceContract:
    """Tests dédiés à la validation des contrats d'entrée des méthodes."""

    def setup_method(self):
        """Réinitialise l'instance Singleton avant chaque test."""
        OrchestrationService._instance = None
        self.service = OrchestrationService.get_instance()

    @pytest.mark.parametrize("invalid_name", [123, None, [], {"key": "value"}])
    def test_get_plugin_with_invalid_type_raises_type_error(self, invalid_name):
        """Vérifie que get_plugin lève TypeError pour des types de nom non valides."""
        with pytest.raises(TypeError, match="Le nom du plugin doit être une chaîne de caractères."):
            self.service.get_plugin(invalid_name)

    @pytest.mark.parametrize("invalid_name", [123, None, [], {"key": "value"}])
    def test_execute_plugin_with_invalid_name_type_raises_type_error(self, invalid_name):
        """Vérifie que execute_plugin lève TypeError pour des types de nom non valides."""
        with pytest.raises(TypeError, match="Le nom du plugin doit être une chaîne de caractères."):
            self.service.execute_plugin(invalid_name)

    @pytest.mark.parametrize("not_a_plugin", [
        object(),
        {"name": "a dict"},
        "just a string"
    ])
    def test_register_plugin_with_invalid_instance_type_raises_error(self, not_a_plugin):
        """Vérifie que register_plugin lève une TypeError si l'objet n'est pas un BasePlugin."""
        with pytest.raises(TypeError, match="Le plugin doit être une instance de BasePlugin."):
            self.service.register_plugin(not_a_plugin)
if __name__ == '__main__':
    unittest.main()