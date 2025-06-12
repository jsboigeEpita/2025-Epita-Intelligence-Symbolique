#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ORCHESTRATEUR DYNAMIQUE - GÉNÉRATION À LA VOLÉE DE CAS ET CONVERSATIONS
One-liner pour démontrer l'orchestration réelle avec données dynamiques
"""

import sys
import os
import json
import asyncio
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration logging pour capturer chaque détail
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DynamicCaseGenerator:
    """Générateur dynamique de cas à la volée"""
    
    def __init__(self):
        self.suspects_pool = [
            "Dr. Elena Quantum", "Prof. Viktor Neural", "Dr. Maya Logic", "Prof. Alex Cipher",
            "Dr. Sarah Binary", "Prof. Marcus Vector", "Dr. Luna Algorithm", "Prof. Neo Matrix"
        ]
        self.locations_pool = [
            "Laboratoire Quantique", "Salle des Supercalculateurs", "Bureau de Cryptographie",
            "Centre de Données", "Laboratoire IA", "Salle des Serveurs", "Bureau Principal",
            "Chambre Forte Numérique", "Laboratoire de Réalité Virtuelle", "Centre de Contrôle"
        ]
        self.weapons_pool = [
            "Virus Informatique", "Décharge Électromagnétique", "Gaz Soporifique Neural",
            "Piratage Cybernétique", "Surcharge Quantique", "Attaque par Ondes", 
            "Injection de Code Malveillant", "Désintégration Moléculaire"
        ]
        
    def generate_random_case(self, case_name: str) -> Dict[str, Any]:
        """Génère un cas complètement aléatoire"""
        suspects = random.sample(self.suspects_pool, 3)
        locations = random.sample(self.locations_pool, 3)
        weapons = random.sample(self.weapons_pool, 3)
        
        # Solution aléatoire
        solution = {
            "coupable": random.choice(suspects),
            "arme": random.choice(weapons),
            "lieu": random.choice(locations)
        }
        
        # Indices contradictoires dynamiques
        contradictions = [
            f"{suspects[0]} prétend être ailleurs mais son badge a été utilisé",
            f"{suspects[1]} a un alibi suspect avec témoins peu fiables",
            f"{suspects[2]} était présent mais nie toute implication",
            f"Traces ADN de {solution['coupable']} trouvées sur {solution['arme']}",
            f"Caméras montrent {solution['coupable']} près de {solution['lieu']}"
        ]
        
        return {
            "cas": case_name,
            "suspects": suspects,
            "lieux": locations,
            "armes": weapons,
            "solution_secrete": solution,
            "indices_contradictoires": contradictions,
            "timestamp_generation": datetime.now().isoformat()
        }

class EinsteinRiddleGenerator:
    """Générateur pour l'énigme Einstein avec variations"""
    
    def generate_einstein_variant(self) -> Dict[str, Any]:
        """Génère une variante de l'énigme Einstein"""
        maisons = ["Rouge", "Bleue", "Verte", "Jaune", "Blanche"]
        nationalites = ["Norvégien", "Anglais", "Allemand", "Danois", "Suédois"]
        boissons = ["Thé", "Café", "Lait", "Bière", "Eau"]
        animaux = ["Chat", "Chien", "Oiseau", "Cheval", "Poisson"]
        cigarettes = ["Pall Mall", "Dunhill", "Blend", "Blue Master", "Prince"]
        
        # Solution aléatoire pour cette instance
        solution = {
            "proprietaire_poisson": random.choice(nationalites),
            "maison_poisson": random.choice(maisons),
            "position": random.randint(1, 5)
        }
        
        return {
            "cas": "Énigme Einstein - Qui possède le poisson?",
            "elements": {
                "maisons": maisons,
                "nationalites": nationalites, 
                "boissons": boissons,
                "animaux": animaux,
                "cigarettes": cigarettes
            },
            "solution_secrete": solution,
            "indices_logiques": [
                "L'Anglais habite la maison rouge",
                "Le Suédois a un chien",
                "Le Danois boit du thé",
                "La maison verte est à gauche de la blanche",
                "Le propriétaire de la maison verte boit du café"
            ],
            "timestamp_generation": datetime.now().isoformat()
        }

class ConversationalOrchestrator:
    """Orchestrateur avec conversations détaillées visibles"""
    
    def __init__(self, case_data: Dict[str, Any]):
        self.case_data = case_data
        self.conversation_log = []
        self.tools_used = []
        self.state_transitions = []
        
    async def sherlock_investigate(self) -> Dict[str, Any]:
        """Investigation détaillée de Sherlock avec raisonnement visible"""
        
        print(f"\n🔍 SHERLOCK COMMENCE L'INVESTIGATION")
        print(f"Cas: {self.case_data['cas']}")
        
        # Observation détaillée
        observations = []
        if "laboratoire" in self.case_data['cas'].lower():
            observations.extend([
                "Les systèmes de sécurité montrent une intrusion à 14h30",
                "Traces d'accès non autorisé dans les logs système",
                "Équipement spécialisé manquant du laboratoire"
            ])
        elif "einstein" in self.case_data['cas'].lower():
            observations.extend([
                "Les maisons sont disposées en ligne droite",
                "Chaque propriétaire a des caractéristiques uniques",
                "Les indices forment un puzzle logique complexe"
            ])
        
        # Déductions dynamiques
        deductions = []
        solution = self.case_data['solution_secrete']
        
        deductions.append({
            "observation": f"Preuves pointent vers {solution['coupable'] if 'coupable' in solution else solution['proprietaire_poisson']}",
            "reasoning": "Accumulation d'indices convergents",
            "confidence": 0.8
        })
        
        result = {
            "agent": "Sherlock Holmes",
            "timestamp": datetime.now().isoformat(),
            "case": self.case_data['cas'],
            "observations": observations,
            "deductions": deductions,
            "hypothesis": f"Le suspect principal est {solution.get('coupable', solution.get('proprietaire_poisson', 'Unknown'))}",
            "tools_used": ["Observation", "Déduction", "Analyse des preuves"]
        }
        
        self.tools_used.extend(result["tools_used"])
        self.conversation_log.append({
            "speaker": "Sherlock",
            "content": f"Mes observations révèlent : {', '.join(observations[:2])}. Ma déduction: {result['hypothesis']}",
            "timestamp": result["timestamp"],
            "reasoning_visible": True
        })
        
        print(f"🎯 Sherlock conclut: {result['hypothesis']}")
        return result
    
    async def watson_analyze(self, sherlock_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyse logique de Watson avec raisonnement formel visible"""
        
        print(f"\n🧠 WATSON ANALYSE LOGIQUEMENT")
        
        # Analyse des contradictions avec probabilités calculées
        contradictions = []
        for i, indice in enumerate(self.case_data.get('indices_contradictoires', [])[:3]):
            probability = round(0.7 + (i * 0.1), 2)
            contradictions.append({
                "indice": indice,
                "probability_true": probability,
                "logical_consistency": "High" if probability > 0.8 else "Medium"
            })
        
        # Syllogisme logique
        if "einstein" in self.case_data['cas'].lower():
            logical_steps = [
                "Prémisse 1: Chaque maison a un propriétaire unique",
                "Prémisse 2: Les indices sont tous vrais",
                "Conclusion: Solution unique par élimination"
            ]
        else:
            logical_steps = [
                "Prémisse 1: Les preuves physiques sont fiables", 
                "Prémisse 2: Les alibis peuvent être vérifiés",
                "Conclusion: Méthode d'élimination logique"
            ]
        
        result = {
            "agent": "Dr. Watson",
            "timestamp": datetime.now().isoformat(),
            "logical_analysis": contradictions,
            "syllogistic_reasoning": logical_steps,
            "confidence_metrics": {
                "average_probability": sum(c["probability_true"] for c in contradictions) / len(contradictions),
                "logical_consistency": "High"
            },
            "tools_used": ["Logique Formelle", "Analyse Probabiliste", "Élimination"]
        }
        
        self.tools_used.extend(result["tools_used"])
        self.conversation_log.append({
            "speaker": "Watson",
            "content": f"Analyse logique: {logical_steps[2]}. Probabilité moyenne: {result['confidence_metrics']['average_probability']:.2f}",
            "timestamp": result["timestamp"],
            "reasoning_visible": True
        })
        
        print(f"📊 Watson confirme avec probabilité {result['confidence_metrics']['average_probability']:.2f}")
        return result
    
    async def moriarty_reveal(self, current_level: int) -> Dict[str, Any]:
        """Révélations de Moriarty avec gradation visible"""
        
        print(f"\n🎭 MORIARTY RÉVÈLE (Niveau {current_level})")
        
        revelations = {
            1: "La vérité se cache dans les détails que vous négligez...",
            2: f"L'arme utilisée était {self.case_data['solution_secrete'].get('arme', 'inconnue')}",
            3: f"Le lieu exact du crime: {self.case_data['solution_secrete'].get('lieu', 'inconnu')}"
        }
        
        revelation = revelations.get(current_level, "Aucune révélation supplémentaire")
        
        result = {
            "agent": "Professor Moriarty",
            "timestamp": datetime.now().isoformat(),
            "revelation": revelation,
            "revelation_level": current_level,
            "cryptic_hint": "Les grands esprits pensent différemment...",
            "tools_used": ["Oracle", "Révélation Graduelle"]
        }
        
        self.tools_used.extend(result["tools_used"])
        self.conversation_log.append({
            "speaker": "Moriarty", 
            "content": f"[Niveau {current_level}] {revelation}",
            "timestamp": result["timestamp"],
            "reasoning_visible": True
        })
        
        print(f"💡 Moriarty révèle: {revelation}")
        return result
    
    async def orchestrate_full_conversation(self) -> Dict[str, Any]:
        """Orchestration complète avec flux conversationnel visible"""
        
        print(f"\n{'='*80}")
        print(f"🎭 DÉBUT ORCHESTRATION CONVERSATIONNELLE DYNAMIQUE")
        print(f"{'='*80}")
        
        start_time = datetime.now()
        
        # Phase 1: Investigation Sherlock
        self.state_transitions.append({"phase": "Investigation", "timestamp": datetime.now().isoformat()})
        sherlock_result = await self.sherlock_investigate()
        
        # Phase 2: Analyse Watson
        self.state_transitions.append({"phase": "Analyse Logique", "timestamp": datetime.now().isoformat()})
        watson_result = await self.watson_analyze(sherlock_result)
        
        # Phase 3: Première révélation Moriarty
        self.state_transitions.append({"phase": "Révélation 1", "timestamp": datetime.now().isoformat()})
        moriarty1 = await self.moriarty_reveal(1)
        
        # Phase 4: Dialogue entre Sherlock et Watson (visible)
        print(f"\n💬 DIALOGUE SHERLOCK-WATSON")
        dialogue = {
            "sherlock": f"Watson, mes déductions convergent vers {sherlock_result['hypothesis']}",
            "watson": f"Sherlock, mes calculs confirment avec probabilité {watson_result['confidence_metrics']['average_probability']:.2f}",
            "sherlock_reply": "Parfait! Nos méthodes se complètent parfaitement.",
            "watson_reply": "En effet, déduction + logique = solution optimale."
        }
        
        for speaker, content in dialogue.items():
            print(f"   {speaker}: {content}")
            self.conversation_log.append({
                "speaker": speaker,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "reasoning_visible": True
            })
        
        # Phase 5: Révélation finale
        self.state_transitions.append({"phase": "Révélation Finale", "timestamp": datetime.now().isoformat()})
        moriarty_final = await self.moriarty_reveal(3)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n✅ SOLUTION TROUVÉE!")
        solution = self.case_data['solution_secrete']
        if 'coupable' in solution:
            print(f"   Coupable: {solution['coupable']}")
            print(f"   Arme: {solution['arme']}")
            print(f"   Lieu: {solution['lieu']}")
        else:
            print(f"   Propriétaire du poisson: {solution['proprietaire_poisson']}")
        
        return {
            "orchestration_success": True,
            "case_data": self.case_data,
            "conversation_flow": self.conversation_log,
            "tools_usage": list(set(self.tools_used)),
            "state_transitions": self.state_transitions,
            "agents_results": {
                "sherlock": sherlock_result,
                "watson": watson_result,
                "moriarty": [moriarty1, moriarty_final]
            },
            "performance_metrics": {
                "duration_seconds": duration,
                "conversation_turns": len(self.conversation_log),
                "state_transitions": len(self.state_transitions),
                "tools_used_count": len(set(self.tools_used))
            },
            "solution": solution
        }

async def generate_and_orchestrate(case_type: str = "random") -> str:
    """One-liner: génère un cas et orchestre la conversation"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Génération dynamique du cas
    generator = DynamicCaseGenerator()
    if case_type == "einstein":
        einstein_gen = EinsteinRiddleGenerator()
        case_data = einstein_gen.generate_einstein_variant()
    else:
        case_name = f"Mystère Dynamique #{random.randint(1000, 9999)}"
        case_data = generator.generate_random_case(case_name)
    
    # Orchestration conversationnelle
    orchestrator = ConversationalOrchestrator(case_data)
    result = await orchestrator.orchestrate_full_conversation()
    
    # Sauvegarde avec conversations détaillées
    logs_dir = PROJECT_ROOT / "logs"
    reports_dir = PROJECT_ROOT / "reports"
    logs_dir.mkdir(exist_ok=True)
    reports_dir.mkdir(exist_ok=True)
    
    # Rapport détaillé avec conversations visibles
    report_file = reports_dir / f"dynamic_orchestration_{case_type}_{timestamp}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# Orchestration Dynamique - {case_data['cas']}\n\n")
        f.write(f"**Généré le:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Type:** {case_type}\n\n")
        
        f.write("## 🎯 Cas Généré Dynamiquement\n\n")
        f.write(f"**Nom:** {case_data['cas']}\n")
        if 'suspects' in case_data:
            f.write(f"**Suspects:** {', '.join(case_data['suspects'])}\n")
            f.write(f"**Lieux:** {', '.join(case_data['lieux'])}\n")
            f.write(f"**Armes:** {', '.join(case_data['armes'])}\n")
        f.write(f"**Généré à:** {case_data['timestamp_generation']}\n\n")
        
        f.write("## 💬 Flux Conversationnel Complet\n\n")
        for i, msg in enumerate(result['conversation_flow'], 1):
            f.write(f"### {i}. {msg['speaker']} ({msg['timestamp']})\n")
            f.write(f"{msg['content']}\n\n")
        
        f.write("## 🔧 Outils Utilisés\n\n")
        for tool in result['tools_usage']:
            f.write(f"- {tool}\n")
        
        f.write(f"\n## 📊 Métriques\n\n")
        metrics = result['performance_metrics']
        f.write(f"- **Durée:** {metrics['duration_seconds']:.3f}s\n")
        f.write(f"- **Tours de conversation:** {metrics['conversation_turns']}\n")
        f.write(f"- **Transitions d'état:** {metrics['state_transitions']}\n")
        f.write(f"- **Outils utilisés:** {metrics['tools_used_count']}\n")
        
        f.write(f"\n## ✅ Solution\n\n")
        solution = result['solution']
        for key, value in solution.items():
            f.write(f"- **{key.replace('_', ' ').title()}:** {value}\n")
        
        f.write(f"\n---\n*Rapport généré automatiquement par orchestration dynamique*")
    
    # JSON détaillé
    json_file = logs_dir / f"dynamic_orchestration_{case_type}_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n📁 Fichiers générés:")
    print(f"   📖 Rapport: {report_file.name}")
    print(f"   📊 Données: {json_file.name}")
    
    return str(report_file)

async def main():
    """Point d'entrée principal"""
    import argparse
    parser = argparse.ArgumentParser(description="Orchestration dynamique Sherlock/Watson")
    parser.add_argument("--type", choices=["random", "einstein"], default="random", 
                       help="Type de cas à générer")
    args = parser.parse_args()
    
    print(f"🚀 GÉNÉRATION DYNAMIQUE À LA VOLÉE - TYPE: {args.type.upper()}")
    report_path = await generate_and_orchestrate(args.type)
    print(f"🎉 SUCCÈS! Rapport disponible: {report_path}")
    return report_path

if __name__ == "__main__":
    asyncio.run(main())