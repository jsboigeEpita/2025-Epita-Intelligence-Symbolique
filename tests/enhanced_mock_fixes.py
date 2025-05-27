"""
Corrections avancées pour les mocks - Résolution des erreurs de tests
"""

import sys
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Ajout du chemin du projet
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class EnhancedMockState:
    """Mock amélioré pour TacticalState avec tous les attributs nécessaires"""
    
    def __init__(self):
        self.task_dependencies = {}
        self.tasks = {}
        self.agents = {}
        self.conflicts = []
        self.objectives = []
        self.intermediate_results = []
        self.rhetorical_analysis_results = {}
        self.tactical_actions = []
        self.agent_utilization = {}
        self.task_completion_rate = 0.0
        self.conflict_resolution_rate = 0.0
    
    def get_task_dependencies(self, task_id):
        return self.task_dependencies.get(task_id, [])
    
    def add_task(self, task):
        self.tasks[task.get('id', 'unknown')] = task
    
    def update_task_progress(self, task_id, progress):
        if task_id in self.tasks:
            self.tasks[task_id]['progress'] = progress
    
    def add_conflict(self, conflict):
        self.conflicts.append(conflict)
    
    def resolve_conflict(self, conflict_id):
        self.conflicts = [c for c in self.conflicts if c.get('id') != conflict_id]

class EnhancedExtractDefinitions:
    """Mock amélioré pour ExtractDefinitions avec model_validate"""
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def model_validate(cls, data):
        """Méthode de compatibilité Pydantic v1/v2"""
        if isinstance(data, dict):
            return cls(**data)
        return data
    
    @classmethod
    def parse_obj(cls, data):
        """Méthode Pydantic v1"""
        return cls.model_validate(data)

def apply_mock_fixes():
    """Applique toutes les corrections de mocks"""
    
    # Patch pour ExtractDefinitions
    import argumentation_analysis.core.extract_definitions as extract_def_module
    if hasattr(extract_def_module, 'ExtractDefinitions'):
        original_class = extract_def_module.ExtractDefinitions
        if not hasattr(original_class, 'model_validate'):
            original_class.model_validate = EnhancedExtractDefinitions.model_validate
    
    print("[MOCK_FIXES] Corrections de mocks appliquées avec succès")

if __name__ == "__main__":
    apply_mock_fixes()
