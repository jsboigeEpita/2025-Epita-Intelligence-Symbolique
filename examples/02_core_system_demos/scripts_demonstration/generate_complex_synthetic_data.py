#!/usr/bin/env python3
"""
Script de génération de données synthétiques complexes pour démonstration système IS
"""

import sys
import os

# Ajout pour résoudre les problèmes d'import de project_core
current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_script_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
import project_core.core_from_scripts.environment_manager
import argparse
import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import os
from typing import Dict, List, Any, Tuple


class ComplexSyntheticDataGenerator:
    """Générateur de données synthétiques complexes pour système IS"""

    def __init__(self):
        self.current_time = datetime.now()
        self.complexity_levels = {
            "low": {"args_per_scenario": 3, "contradictions": 2, "depth": 2},
            "medium": {"args_per_scenario": 5, "contradictions": 4, "depth": 3},
            "high": {"args_per_scenario": 8, "contradictions": 6, "depth": 4},
        }

        # Templates d'arguments sophistiqués
        self.argument_templates = {
            "epistemic": [
                "Si nous savons que {premise}, alors nous devons accepter que {conclusion}",
                "L'évidence suggère que {premise}, mais cela contredit notre compréhension de {contradiction}",
                "En supposant que {premise} soit vrai, nous pouvons inférer que {conclusion} avec un degré de certitude de {confidence}%",
            ],
            "modal": [
                "Il est nécessaire que {premise} pour que {conclusion} soit possible",
                "Il est possible que {premise}, mais improbable que {conclusion}",
                "Dans tous les mondes possibles où {premise}, nous observons {conclusion}",
            ],
            "pragmatic": [
                "Étant donné le contexte {context}, l'argument {premise} implique pragmatiquement {conclusion}",
                "L'intention communicative derrière {premise} suggère que {conclusion}",
                "Dans cette situation discursive, {premise} présuppose {conclusion}",
            ],
        }

        # Sujets complexes pour arguments
        self.complex_topics = [
            {
                "domain": "intelligence_artificielle",
                "premises": [
                    "l'IA peut simuler la conscience",
                    "l'IA possède une forme d'intentionnalité",
                    "l'IA peut éprouver des émotions synthétiques",
                    "l'IA peut développer une personnalité distincte",
                ],
                "conclusions": [
                    "l'IA est consciente",
                    "l'IA possède une subjectivité",
                    "l'IA mérite des droits",
                    "l'IA peut souffrir",
                ],
                "contradictions": [
                    "la conscience nécessite un substrat biologique",
                    "l'intentionnalité requiert une embodiment physique",
                    "les émotions sont intrinsèquement biologiques",
                ],
            },
            {
                "domain": "epistemologie",
                "premises": [
                    "la connaissance empirique est fiable",
                    "la logique formelle capture la rationalité",
                    "l'introspection révèle la structure mentale",
                    "l'intersubjectivité garantit l'objectivité",
                ],
                "conclusions": [
                    "nous pouvons atteindre la vérité",
                    "la science progresse vers la vérité",
                    "la rationalité est universelle",
                    "l'objectivité est possible",
                ],
                "contradictions": [
                    "nos sens nous trompent régulièrement",
                    "la logique a ses limites paradoxales",
                    "l'inconscient influence notre jugement",
                ],
            },
            {
                "domain": "éthique_ia",
                "premises": [
                    "l'IA doit maximiser le bien-être humain",
                    "l'IA doit respecter l'autonomie humaine",
                    "l'IA doit être transparente et explicable",
                    "l'IA doit traiter tous les humains équitablement",
                ],
                "conclusions": [
                    "l'IA peut prendre des décisions morales",
                    "l'IA est responsable de ses actions",
                    "l'IA peut juger les humains",
                    "l'IA doit avoir des droits",
                ],
                "contradictions": [
                    "maximiser le bien-être peut violer l'autonomie",
                    "la transparence peut compromettre l'efficacité",
                    "l'équité peut nécessiter la discrimination",
                ],
            },
        ]

    def generate_complex_scenario(
        self, complexity: str, scenario_id: str
    ) -> Dict[str, Any]:
        """Génère un scénario argumentatif complexe"""
        config = self.complexity_levels[complexity]
        topic = random.choice(self.complex_topics)

        # Génération des arguments avec structures rhétoriques imbriquées
        arguments = []
        for i in range(config["args_per_scenario"]):
            arg_type = random.choice(["epistemic", "modal", "pragmatic"])
            template = random.choice(self.argument_templates[arg_type])

            premise = random.choice(topic["premises"])
            conclusion = random.choice(topic["conclusions"])
            contradiction = random.choice(topic["contradictions"])

            # Création de l'argument avec métadonnées riches
            argument = {
                "id": f"{scenario_id}_arg_{i+1}",
                "type": arg_type,
                "content": template.format(
                    premise=premise,
                    conclusion=conclusion,
                    contradiction=contradiction,
                    context=topic["domain"],
                    confidence=random.randint(60, 95),
                ),
                "strength": random.uniform(0.3, 0.9),
                "rhetorical_structure": {
                    "premise": premise,
                    "conclusion": conclusion,
                    "warrants": [f"warrant_{j}" for j in range(random.randint(1, 3))],
                    "rebuttals": [contradiction] if random.random() > 0.5 else [],
                },
                "epistemic_metadata": {
                    "certainty_level": random.choice(["high", "medium", "low"]),
                    "source_reliability": random.uniform(0.4, 1.0),
                    "temporal_validity": random.choice(
                        ["permanent", "contextual", "temporal"]
                    ),
                    "modal_status": random.choice(
                        ["necessary", "possible", "contingent"]
                    ),
                },
                "pragmatic_context": {
                    "speech_act": random.choice(
                        ["assertion", "question", "command", "promise"]
                    ),
                    "implicature": random.choice(
                        ["scalar", "conversational", "conventional", "none"]
                    ),
                    "presupposition": premise if random.random() > 0.6 else None,
                },
            }
            arguments.append(argument)

        # Génération des contradictions multiples
        contradictions = []
        for i in range(config["contradictions"]):
            arg1, arg2 = random.sample(arguments, 2)
            contradiction = {
                "id": f"{scenario_id}_contradiction_{i+1}",
                "type": random.choice(["logical", "pragmatic", "epistemic", "modal"]),
                "argument_1": arg1["id"],
                "argument_2": arg2["id"],
                "description": f"Contradiction entre '{arg1['rhetorical_structure']['conclusion']}' et '{arg2['rhetorical_structure']['conclusion']}'",
                "severity": random.choice(["weak", "moderate", "strong"]),
                "resolution_strategies": [
                    random.choice(
                        [
                            "reject_premise",
                            "modify_conclusion",
                            "context_differentiation",
                            "temporal_separation",
                        ]
                    )
                    for _ in range(random.randint(1, 3))
                ],
            }
            contradictions.append(contradiction)

        # Problématiques épistémologiques complexes
        epistemic_issues = {
            "foundational_problems": [
                "Problème de régression infinie dans la justification",
                "Circularité épistémique dans l'auto-référence",
                "Problème de Gettier généralisé",
                "Incommensurabilité des paradigmes",
            ],
            "modal_complexities": [
                "Logiques modales multiples incompatibles",
                "Problème de l'identité trans-monde",
                "Nécessité métaphysique vs logique",
                "Possibilité épistémique vs métaphysique",
            ],
            "pragmatic_paradoxes": [
                "Paradoxe du menteur pragma-sémantique",
                "Auto-défaite des assertions performatives",
                "Indétermination radicale de la traduction",
                "Holisme confirmationnel de Quine",
            ],
        }

        selected_issues = {
            category: random.sample(issues, min(2, len(issues)))
            for category, issues in epistemic_issues.items()
        }

        scenario = {
            "id": scenario_id,
            "timestamp": self.current_time.isoformat(),
            "complexity_level": complexity,
            "domain": topic["domain"],
            "title": f"Scénario complexe {complexity} - {topic['domain']}",
            "description": f"Analyse argumentative de {config['args_per_scenario']} arguments avec {config['contradictions']} contradictions",
            "arguments": arguments,
            "contradictions": contradictions,
            "epistemic_issues": selected_issues,
            "global_coherence_score": random.uniform(0.2, 0.8),
            "complexity_metrics": {
                "argument_depth": config["depth"],
                "contradiction_density": len(contradictions) / len(arguments),
                "epistemic_complexity": len(
                    [item for sublist in selected_issues.values() for item in sublist]
                ),
                "rhetorical_sophistication": random.uniform(0.5, 1.0),
            },
        }

        return scenario

    def generate_multiple_scenarios(
        self, complexity: str, num_scenarios: int
    ) -> List[Dict[str, Any]]:
        """Génère plusieurs scénarios complexes"""
        scenarios = []
        for i in range(num_scenarios):
            scenario_id = f"complex_scenario_{complexity}_{i+1}_{uuid.uuid4().hex[:8]}"
            scenario = self.generate_complex_scenario(complexity, scenario_id)
            scenarios.append(scenario)

        return scenarios

    def save_datasets(self, scenarios: List[Dict[str, Any]], output_dir: str):
        """Sauvegarde les datasets dans la structure appropriée"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Sauvegarde globale
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        global_file = output_path / f"complex_synthetic_data_{timestamp}.json"

        dataset = {
            "metadata": {
                "generation_time": datetime.now().isoformat(),
                "generator_version": "1.0.0",
                "total_scenarios": len(scenarios),
                "complexity_distribution": {},
            },
            "scenarios": scenarios,
        }

        # Calcul distribution complexité
        for scenario in scenarios:
            level = scenario["complexity_level"]
            dataset["metadata"]["complexity_distribution"][level] = (
                dataset["metadata"]["complexity_distribution"].get(level, 0) + 1
            )

        with open(global_file, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)

        # Sauvegarde par niveau de complexité
        by_complexity = {}
        for scenario in scenarios:
            level = scenario["complexity_level"]
            if level not in by_complexity:
                by_complexity[level] = []
            by_complexity[level].append(scenario)

        for level, level_scenarios in by_complexity.items():
            level_file = output_path / f"scenarios_{level}_{timestamp}.json"
            with open(level_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "metadata": {
                            "complexity_level": level,
                            "scenario_count": len(level_scenarios),
                            "generation_time": datetime.now().isoformat(),
                        },
                        "scenarios": level_scenarios,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

        # Rapport de génération
        report = {
            "generation_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_scenarios": len(scenarios),
                "complexity_breakdown": dataset["metadata"]["complexity_distribution"],
                "output_files": {
                    "global_dataset": str(global_file),
                    "by_complexity": {
                        level: str(output_path / f"scenarios_{level}_{timestamp}.json")
                        for level in by_complexity.keys()
                    },
                },
            },
            "quality_metrics": {
                "avg_arguments_per_scenario": sum(
                    len(s["arguments"]) for s in scenarios
                )
                / len(scenarios),
                "avg_contradictions_per_scenario": sum(
                    len(s["contradictions"]) for s in scenarios
                )
                / len(scenarios),
                "avg_coherence_score": sum(
                    s["global_coherence_score"] for s in scenarios
                )
                / len(scenarios),
                "epistemic_complexity_distribution": {},
            },
        }

        report_file = output_path / f"generation_report_{timestamp}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        return {
            "global_dataset": str(global_file),
            "by_complexity": {
                level: str(output_path / f"scenarios_{level}_{timestamp}.json")
                for level in by_complexity.keys()
            },
            "report": str(report_file),
            "output_directory": str(output_path),
        }


def main():
    parser = argparse.ArgumentParser(
        description="Génération de données synthétiques complexes"
    )
    parser.add_argument(
        "--complexity",
        choices=["low", "medium", "high"],
        default="high",
        help="Niveau de complexité des données",
    )
    parser.add_argument(
        "--scenarios",
        choices=["single", "multiple", "comprehensive"],
        default="multiple",
        help="Type de scénarios à générer",
    )
    parser.add_argument(
        "--output-dir", default="data/synthetic_complex", help="Répertoire de sortie"
    )
    parser.add_argument(
        "--count", type=int, default=5, help="Nombre de scénarios à générer"
    )

    args = parser.parse_args()

    print(f"[GENERATION] DONNEES SYNTHETIQUES COMPLEXES")
    print(f"=" * 60)
    print(f"Complexite: {args.complexity}")
    print(f"Type: {args.scenarios}")
    print(f"Nombre: {args.count}")
    print(f"Sortie: {args.output_dir}")
    print()

    generator = ComplexSyntheticDataGenerator()

    if args.scenarios == "single":
        scenarios = [
            generator.generate_complex_scenario(
                args.complexity, f"single_{uuid.uuid4().hex[:8]}"
            )
        ]
    elif args.scenarios == "multiple":
        scenarios = generator.generate_multiple_scenarios(args.complexity, args.count)
    else:  # comprehensive
        scenarios = []
        for level in ["low", "medium", "high"]:
            level_scenarios = generator.generate_multiple_scenarios(
                level, args.count // 3 + 1
            )
            scenarios.extend(level_scenarios)

    print(f"[STATS] Generation de {len(scenarios)} scenarios...")

    # Sauvegarde
    results = generator.save_datasets(scenarios, args.output_dir)

    print(f"[SUCCESS] GENERATION TERMINEE")
    print(f"Dataset global: {results['global_dataset']}")
    print(f"Repertoire: {results['output_directory']}")
    print(f"Rapport: {results['report']}")
    print()

    # Statistiques détaillées
    total_args = sum(len(s["arguments"]) for s in scenarios)
    total_contradictions = sum(len(s["contradictions"]) for s in scenarios)
    avg_coherence = sum(s["global_coherence_score"] for s in scenarios) / len(scenarios)

    print(f"[METRICS] STATISTIQUES DETAILLEES:")
    print(f"   Total arguments: {total_args}")
    print(f"   Total contradictions: {total_contradictions}")
    print(f"   Coherence moyenne: {avg_coherence:.3f}")
    print(
        f"   Complexite epistemologique moyenne: {sum(s['complexity_metrics']['epistemic_complexity'] for s in scenarios) / len(scenarios):.1f}"
    )

    return results


if __name__ == "__main__":
    results = main()
