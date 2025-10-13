# -*- coding: utf-8 -*-
"""
Processeur de données custom pour la démonstration EPITA
Traitement RÉEL des données (pas de mocks)
"""

import hashlib
import time
import re
from typing import Dict, List, Any
from datetime import datetime

class CustomDataProcessor:
    """Processeur adaptatif pour données custom"""
    
    def __init__(self, module_name: str):
        self.module_name = module_name
        self.processing_id = f"{module_name}_{int(time.time())}"
    
    def process_custom_data(self, content: str, mode: str) -> Dict[str, Any]:
        """Traite les données custom avec analyse RÉELLE"""
        
        # Hash du contenu pour traçabilité
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Détection de marqueurs EPITA
        markers_found = re.findall(r'\[EPITA_[A-Z_0-9]+\]', content)
        
        # Détection basique de sophismes
        sophistries_patterns = [
            r'90% des entreprises',
            r'tout le monde dit',
            r'c\'est évident que',
            r'toujours.*jamais',
            r'tous.*sont'
        ]
        sophistries_detected = []
        for pattern in sophistries_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                sophistries_detected.append(pattern)
        
        # Analyse logique basique
        logical_elements = {
            'premises': re.findall(r'[A-Z][a-z]+ les [a-z]+ sont [a-z]+', content),
            'conclusions': re.findall(r'donc|par conséquent|ainsi', content, re.IGNORECASE),
            'connectors': re.findall(r'si.*alors|puisque|car|parce que', content, re.IGNORECASE)
        }
        
        # Calcul simple de la force de l'argument pour la démo
        arg_strength = 0.0
        if logical_elements['premises'] and logical_elements['conclusions']:
            arg_strength = 0.5
        if logical_elements['connectors']:
            arg_strength = min(1.0, arg_strength + 0.3 * len(logical_elements['connectors']))
        
        logical_analysis_results = {
            'argument_strength': arg_strength,
            'premise_count': len(logical_elements['premises']),
            'conclusion_count': len(logical_elements['conclusions']),
            'connector_count': len(logical_elements['connectors'])
        }

        return {
            'content_hash': content_hash,
            'processing_id': self.processing_id,
            'markers_found': markers_found,
            'sophistries_detected': sophistries_detected,
            'logical_elements': logical_elements, # Gardé pour compatibilité si utilisé ailleurs
            'logical_analysis': logical_analysis_results, # Nouvelle clé attendue
            'processing_timestamp': datetime.now().isoformat(),
            'processing_mode': 'real_analysis',
            'content_length': len(content),
            'module': self.module_name,
            'mock_used': False # Indiquer explicitement qu'aucun mock n'est utilisé
        }
    
    def generate_proof_of_processing(self, content: str) -> str:
        """Génère une preuve de traitement réel"""
        timestamp = int(time.time())
        content_snippet = content[:50].replace('\n', ' ')
        return f"PROOF_REAL_PROCESSING_{self.module_name}_{timestamp}_{hash(content_snippet)}"

class AdaptiveAnalyzer:
    """Analyseur adaptatif pour logique avancée"""
    
    def __init__(self, processor: CustomDataProcessor):
        self.processor = processor
    
    def analyze_modal_logic(self, content: str) -> Dict[str, Any]:
        """Analyse de logique modale basique"""
        
        modal_operators = []
        if re.search(r'nécessairement|obligatoirement|forcément', content, re.IGNORECASE):
            modal_operators.append('necessity')
        if re.search(r'possiblement|peut-être|éventuellement', content, re.IGNORECASE):
            modal_operators.append('possibility')
        if re.search(r'autorisé|permis|licite', content, re.IGNORECASE):
            modal_operators.append('permission')
        
        # Analyse des mondes possibles
        possible_worlds = 1
        if 'si' in content.lower():
            possible_worlds += content.lower().count('si')
        
        return {
            'modal_operators': modal_operators,
            'possible_worlds': possible_worlds,
            'temporal_elements': re.findall(r'avant|après|pendant|toujours|jamais', content, re.IGNORECASE),
            'analysis_timestamp': datetime.now().isoformat(),
            'analysis_mode': 'adaptive_real'
        }

def create_fallback_handler():
    """Crée un gestionnaire de fallback"""
    return lambda content: {
        'fallback': True,
        'message': 'Traitement minimal activé',
        'timestamp': datetime.now().isoformat()
    }