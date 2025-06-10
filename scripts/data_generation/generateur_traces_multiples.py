#!/usr/bin/env python3
"""
GÉNÉRATEUR DE TRACES MULTIPLES AUTOMATIQUE
==========================================

Génère plusieurs datasets avec des données synthétiques différentes
pour prouver l'authenticité et la reproductibilité du système.
"""

import asyncio
import subprocess
import json
import os
from datetime import datetime
from typing import List, Dict
import argparse

DATASETS_SCENARIOS = {
    "crypto_mysterieux": {
        "nom": "crypto_mysterieux",
        "description": "Enquête sur une cryptographie mystérieuse",
        "contexte": "Dans le centre de recherche cryptographique de l'EPITA",
        "victime": "Professeur Turing",
        "indices": [
            "Algorithme RSA incomplet sur l'écran",
            "Clé privée effacée du serveur",
            "Message chiffré mystérieux dans la corbeille"
        ],
        "suspects": [
            "Dr. Rivest (expert en chiffrement asymétrique)",
            "Prof. Diffie (spécialiste échange de clés)",
            "Mme. Hellman (cryptanalyste réputée)"
        ]
    },
    
    "reseau_compromis": {
        "nom": "reseau_compromis",
        "description": "Investigation sur une intrusion réseau",
        "contexte": "Dans le laboratoire cybersécurité de l'EPITA",
        "victime": "Administrateur réseau Chen",
        "indices": [
            "Logs système effacés entre 14h et 15h",
            "Port 443 ouvert sans autorisation",
            "Tentatives de connexion depuis IP inconnue"
        ],
        "suspects": [
            "Hacker Wilson (expert en pénétration)",
            "Tech-Lead Martinez (accès privilégié)",
            "Stagiaire Dubois (récemment licencié)"
        ]
    },
    
    "intelligence_artificielle": {
        "nom": "intelligence_artificielle",
        "description": "Mystère autour d'une IA disparue",
        "contexte": "Dans le département IA de l'EPITA",
        "victime": "Modèle GPT-Epita v3.0",
        "indices": [
            "Poids du modèle corrompus",
            "Dataset d'entraînement modifié",
            "Logs de fine-tuning interrompus"
        ],
        "suspects": [
            "Dr. Bengio (adversaire des LLM)",
            "Chercheur LeCun (partisan CNN)",
            "Prof. Hinton (expert réseaux profonds)"
        ]
    },
    
    "base_donnees": {
        "nom": "base_donnees", 
        "description": "Corruption mystérieuse d'une base de données",
        "contexte": "Dans le centre de données de l'EPITA",
        "victime": "Base PostgreSQL critique",
        "indices": [
            "Index B-tree corrompu",
            "Transaction rollback inexpliquée",
            "Backup automatique échoué"
        ],
        "suspects": [
            "DBA Senior Rodriguez (accès root)",
            "Dev Backend Kim (requêtes complexes)",
            "Auditeur Externe Thompson (accès temporaire)"
        ]
    },
    
    "systeme_distribue": {
        "nom": "systeme_distribue",
        "description": "Panne en cascade dans un système distribué",
        "contexte": "Dans l'infrastructure cloud de l'EPITA",
        "victime": "Cluster Kubernetes principal",
        "indices": [
            "Service discovery en panne",
            "Load balancer déséquilibré", 
            "Pods en état CrashLoopBackOff"
        ],
        "suspects": [
            "DevOps Jackson (déploiements récents)",
            "SRE Patel (monitoring système)",
            "Cloud Architect Liu (configuration réseau)"
        ]
    }
}

class GenerateurTracesMultiples:
    """Générateur de multiples datasets de traces."""
    
    def __init__(self):
        self.resultats = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    async def generer_dataset(self, scenario_key: str, scenario: Dict) -> Dict:
        """Génère un dataset spécifique."""
        print(f"\n[DATASET] Génération: {scenario_key}")
        print(f"[INFO] {scenario['description']}")
        
        # Lancement du générateur pour ce dataset
        try:
            cmd = ["python", "test_traces_completes_auto_fixed.py", scenario_key]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode == 0:
                print(f"[OK] Dataset {scenario_key} généré avec succès")
                
                # Lecture du rapport final
                rapport_pattern = f"reports/rapport_final_{scenario_key}_*.json"
                import glob
                rapports = glob.glob(rapport_pattern)
                
                if rapports:
                    rapport_file = sorted(rapports)[-1]  # Le plus récent
                    with open(rapport_file, 'r', encoding='utf-8') as f:
                        rapport = json.load(f)
                    
                    return {
                        "scenario": scenario_key,
                        "status": "SUCCESS",
                        "rapport": rapport,
                        "output_lines": len(result.stdout.split('\n')),
                        "traces_files": {
                            "rapport": rapport_file,
                            "traces": rapport["files"]["traces_completes"],
                            "synthese": rapport["files"]["synthese_automatique"]
                        }
                    }
                else:
                    print(f"[WARN] Aucun rapport trouvé pour {scenario_key}")
                    return {"scenario": scenario_key, "status": "NO_REPORT", "error": "Rapport introuvable"}
            else:
                print(f"[ERROR] Échec génération {scenario_key}: {result.stderr[:200]}...")
                return {
                    "scenario": scenario_key, 
                    "status": "FAILED", 
                    "error": result.stderr[:500],
                    "stdout": result.stdout[:500]
                }
                
        except Exception as e:
            print(f"[ERROR] Exception pour {scenario_key}: {e}")
            return {"scenario": scenario_key, "status": "EXCEPTION", "error": str(e)}
    
    async def generer_tous_datasets(self, scenarios_keys: List[str]) -> Dict:
        """Génère tous les datasets sélectionnés."""
        print(f"[MULTI] Génération de {len(scenarios_keys)} datasets")
        print("=" * 60)
        
        for scenario_key in scenarios_keys:
            if scenario_key not in DATASETS_SCENARIOS:
                print(f"[ERROR] Scénario '{scenario_key}' inconnu")
                continue
                
            scenario = DATASETS_SCENARIOS[scenario_key]
            resultat = await self.generer_dataset(scenario_key, scenario)
            self.resultats.append(resultat)
        
        # Synthèse finale
        synthese_finale = self.generer_synthese_finale()
        
        # Sauvegarde du rapport multi-datasets
        rapport_multi_file = f"reports/rapport_multi_datasets_{self.timestamp}.json"
        with open(rapport_multi_file, 'w', encoding='utf-8') as f:
            json.dump({
                "meta": {
                    "timestamp": self.timestamp,
                    "scenarios_generes": len(self.resultats),
                    "scenarios_reussis": len([r for r in self.resultats if r["status"] == "SUCCESS"])
                },
                "resultats": self.resultats,
                "synthese_finale": synthese_finale,
                "fichiers_generes": rapport_multi_file
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n[FINAL] Rapport multi-datasets: {rapport_multi_file}")
        return synthese_finale
    
    def generer_synthese_finale(self) -> Dict:
        """Génère une synthèse finale automatique."""
        reussis = [r for r in self.resultats if r["status"] == "SUCCESS"]
        
        if not reussis:
            return {
                "verdict": "ECHEC_COMPLET",
                "taux_reussite": 0,
                "recommandation": "Aucun dataset généré avec succès"
            }
        
        # Calcul des métriques agrégées
        scores_authenticite = []
        durees_totales = []
        appels_api_totaux = 0
        
        for resultat in reussis:
            rapport = resultat["rapport"]
            scores_authenticite.append(rapport["authenticite"]["score_confiance"])
            durees_totales.append(rapport["resume"]["duree_totale_secondes"])
            appels_api_totaux += rapport["resume"]["appels_api_reussis"]
        
        score_moyen = sum(scores_authenticite) / len(scores_authenticite)
        duree_moyenne = sum(durees_totales) / len(durees_totales)
        
        # Détection d'indicateurs de mocks agrégés
        indicateurs_mocks_total = []
        for resultat in reussis:
            indicateurs_mocks_total.extend(
                resultat["rapport"]["authenticite"]["indicateurs_mocks"]
            )
        
        # Verdict final automatique
        if score_moyen >= 0.9 and len(indicateurs_mocks_total) == 0:
            verdict = "AUTHENTIQUE_CONFIRME"
        elif score_moyen >= 0.8:
            verdict = "AUTHENTIQUE_PROBABLE"
        elif score_moyen >= 0.6:
            verdict = "SUSPECT"
        else:
            verdict = "MOCKS_DETECTES"
        
        return {
            "verdict": verdict,
            "taux_reussite": len(reussis) / len(self.resultats) * 100,
            "datasets_reussis": len(reussis),
            "datasets_totaux": len(self.resultats),
            "metriques_agregees": {
                "score_authenticite_moyen": score_moyen,
                "duree_execution_moyenne": duree_moyenne,
                "appels_api_totaux": appels_api_totaux,
                "indicateurs_mocks_total": len(indicateurs_mocks_total)
            },
            "variabilite": {
                "scores_authenticite": scores_authenticite,
                "durees_execution": durees_totales,
                "ecart_type_durees": self._ecart_type(durees_totales)
            },
            "recommandation": self._generer_recommandation_finale(verdict, score_moyen, indicateurs_mocks_total)
        }
    
    def _ecart_type(self, valeurs: List[float]) -> float:
        """Calcule l'écart-type."""
        if len(valeurs) <= 1:
            return 0.0
        moyenne = sum(valeurs) / len(valeurs)
        variance = sum((x - moyenne) ** 2 for x in valeurs) / len(valeurs)
        return variance ** 0.5
    
    def _generer_recommandation_finale(self, verdict: str, score_moyen: float, indicateurs_mocks: List) -> str:
        """Génère une recommandation finale automatique."""
        if verdict == "AUTHENTIQUE_CONFIRME":
            return f"SYSTÈME AUTHENTIQUE CONFIRMÉ - Score: {score_moyen:.2f}, Aucun mock détecté"
        elif verdict == "AUTHENTIQUE_PROBABLE":
            return f"SYSTÈME PROBABLEMENT AUTHENTIQUE - Score: {score_moyen:.2f}, Vérifications supplémentaires recommandées"
        elif verdict == "SUSPECT":
            return f"SYSTÈME SUSPECT - Score: {score_moyen:.2f}, Investigation approfondie nécessaire"
        else:
            return f"MOCKS DÉTECTÉS - Score: {score_moyen:.2f}, {len(indicateurs_mocks)} indicateurs trouvés"

async def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Générateur de traces multiples")
    parser.add_argument(
        "scenarios", 
        nargs="*", 
        choices=list(DATASETS_SCENARIOS.keys()) + ["all"],
        default=["all"],
        help="Scénarios à générer (défaut: all)"
    )
    parser.add_argument(
        "--liste", 
        action="store_true", 
        help="Affiche la liste des scénarios disponibles"
    )
    
    args = parser.parse_args()
    
    if args.liste:
        print("SCÉNARIOS DISPONIBLES:")
        print("=" * 50)
        for key, scenario in DATASETS_SCENARIOS.items():
            print(f"- {key}: {scenario['description']}")
        return
    
    # Détermination des scénarios à exécuter
    if "all" in args.scenarios:
        scenarios_a_executer = list(DATASETS_SCENARIOS.keys())
    else:
        scenarios_a_executer = args.scenarios
    
    print("GÉNÉRATEUR DE TRACES MULTIPLES AUTOMATIQUE")
    print("=" * 60)
    print(f"Scénarios sélectionnés: {', '.join(scenarios_a_executer)}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Génération
    generateur = GenerateurTracesMultiples()
    synthese = await generateur.generer_tous_datasets(scenarios_a_executer)
    
    # Affichage des résultats finaux
    print("\n" + "=" * 60)
    print("SYNTHÈSE FINALE AUTOMATIQUE")
    print("=" * 60)
    print(f"[VERDICT] {synthese['verdict']}")
    print(f"[TAUX] Réussite: {synthese['taux_reussite']:.1f}% ({synthese['datasets_reussis']}/{synthese['datasets_totaux']})")
    print(f"[SCORE] Authenticité moyenne: {synthese['metriques_agregees']['score_authenticite_moyen']:.2f}")
    print(f"[PERF] Durée moyenne: {synthese['metriques_agregees']['duree_execution_moyenne']:.1f}s")
    print(f"[API] Appels totaux: {synthese['metriques_agregees']['appels_api_totaux']}")
    print(f"[MOCKS] Indicateurs détectés: {synthese['metriques_agregees']['indicateurs_mocks_total']}")
    print(f"\n[RECOMMANDATION] {synthese['recommandation']}")
    
    if synthese["variabilite"]["ecart_type_durees"] > 0:
        print(f"[VARIABILITÉ] Écart-type durées: {synthese['variabilite']['ecart_type_durees']:.1f}s (preuve de non-uniformité)")

if __name__ == "__main__":
    asyncio.run(main())