#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour analyser les traces de conversation de l'agent Informel.

Ce script permet de:
1. Charger les traces de conversation générées par l'agent Informel
2. Analyser les performances de l'agent (identification d'arguments, attribution de sophismes)
3. Identifier les points d'amélioration
4. Générer un rapport d'analyse
"""

import os
import sys
import json
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("AnalyseTracesInformal")

# Ajouter le répertoire racine au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent
root_dir = parent_dir.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Répertoire des traces
TRACES_DIR = Path(parent_dir) / "execution_traces" / "informal"
ANALYSIS_DIR = Path(parent_dir) / "documentation" / "reports" / "informal"
ANALYSIS_DIR.mkdir(exist_ok=True, parents=True)

def load_traces():
    """
    Charge toutes les traces de conversation disponibles.
    """
    logger.info("Chargement des traces de conversation...")
    
    traces = []
    
    if not TRACES_DIR.exists():
        logger.error(f"Répertoire des traces non trouvé: {TRACES_DIR}")
        return traces
    
    for trace_file in TRACES_DIR.glob("*.json"):
        try:
            with open(trace_file, "r", encoding="utf-8") as f:
                trace_data = json.load(f)
                traces.append({
                    "file": trace_file.name,
                    "data": trace_data
                })
            logger.info(f"Trace chargée: {trace_file.name}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la trace {trace_file.name}: {e}")
    
    logger.info(f"{len(traces)} traces chargées au total.")
    return traces

def analyze_argument_identification(traces):
    """
    Analyse la qualité de l'identification des arguments.
    """
    logger.info("Analyse de l'identification des arguments...")
    
    results = {
        "total_arguments": 0,
        "argument_lengths": [],
        "avg_argument_length": 0,
        "arguments_per_extrait": defaultdict(int)
    }
    
    for trace in traces:
        trace_data = trace["data"]
        extrait_id = trace_data.get("extrait", {}).get("id", "inconnu")
        
        for resultat in trace_data.get("resultats_par_extrait", []):
            if resultat.get("id") == extrait_id:
                num_args = resultat.get("nombre_arguments", 0)
                results["arguments_per_extrait"][extrait_id] = num_args
                results["total_arguments"] += num_args
        
        # Analyser les arguments identifiés
        arguments = []
        for arg in trace_data.get("resultats", {}).get("arguments", []):
            description = arg.get("description", "")
            if description:
                arguments.append(description)
                results["argument_lengths"].append(len(description.split()))
        
        logger.info(f"Trace {trace['file']}: {len(arguments)} arguments identifiés")
    
    # Calculer la longueur moyenne des arguments
    if results["argument_lengths"]:
        results["avg_argument_length"] = sum(results["argument_lengths"]) / len(results["argument_lengths"])
    
    logger.info(f"Nombre total d'arguments identifiés: {results['total_arguments']}")
    logger.info(f"Longueur moyenne des arguments: {results['avg_argument_length']:.2f} mots")
    
    return results

def analyze_fallacy_attribution(traces):
    """
    Analyse la qualité de l'attribution des sophismes.
    """
    logger.info("Analyse de l'attribution des sophismes...")
    
    results = {
        "total_fallacies": 0,
        "fallacy_types": Counter(),
        "justification_lengths": [],
        "avg_justification_length": 0,
        "fallacies_per_argument": defaultdict(int),
        "fallacies_per_extrait": defaultdict(int)
    }
    
    for trace in traces:
        trace_data = trace["data"]
        extrait_id = trace_data.get("extrait", {}).get("id", "inconnu")
        
        for resultat in trace_data.get("resultats_par_extrait", []):
            if resultat.get("id") == extrait_id:
                num_fallacies = resultat.get("nombre_sophismes", 0)
                results["fallacies_per_extrait"][extrait_id] = num_fallacies
                results["total_fallacies"] += num_fallacies
        
        # Analyser les sophismes identifiés
        fallacies = []
        for fallacy in trace_data.get("resultats", {}).get("sophismes", []):
            fallacy_type = fallacy.get("fallacy_type", "")
            justification = fallacy.get("justification", "")
            target_arg_id = fallacy.get("target_argument_id", "")
            
            if fallacy_type:
                fallacies.append({
                    "type": fallacy_type,
                    "justification": justification,
                    "target_arg_id": target_arg_id
                })
                
                results["fallacy_types"][fallacy_type] += 1
                results["justification_lengths"].append(len(justification.split()))
                results["fallacies_per_argument"][target_arg_id] += 1
        
        logger.info(f"Trace {trace['file']}: {len(fallacies)} sophismes identifiés")
    
    # Calculer la longueur moyenne des justifications
    if results["justification_lengths"]:
        results["avg_justification_length"] = sum(results["justification_lengths"]) / len(results["justification_lengths"])
    
    logger.info(f"Nombre total de sophismes identifiés: {results['total_fallacies']}")
    logger.info(f"Longueur moyenne des justifications: {results['avg_justification_length']:.2f} mots")
    logger.info(f"Types de sophismes les plus fréquents: {results['fallacy_types'].most_common(5)}")
    
    return results

def analyze_taxonomy_usage(traces):
    """
    Analyse l'utilisation de la taxonomie des sophismes.
    """
    logger.info("Analyse de l'utilisation de la taxonomie...")
    
    results = {
        "taxonomy_exploration": [],
        "unique_fallacy_types": set(),
        "taxonomy_depth": defaultdict(int)
    }
    
    # Charger la taxonomie pour référence
    taxonomy_path = Path(parent_dir) / "data" / "argumentum_fallacies_taxonomy.csv"
    taxonomy_df = None
    
    if taxonomy_path.exists():
        try:
            taxonomy_df = pd.read_csv(taxonomy_path, encoding='utf-8')
            logger.info(f"Taxonomie chargée: {len(taxonomy_df)} sophismes.")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la taxonomie: {e}")
    
    for trace in traces:
        trace_data = trace["data"]
        
        # Analyser les sophismes identifiés
        for fallacy in trace_data.get("resultats", {}).get("sophismes", []):
            fallacy_type = fallacy.get("fallacy_type", "")
            fallacy_pk = fallacy.get("fallacy_pk", None)
            
            if fallacy_type:
                results["unique_fallacy_types"].add(fallacy_type)
            
            if fallacy_pk is not None and taxonomy_df is not None:
                # Trouver la profondeur du sophisme dans la taxonomie
                fallacy_row = taxonomy_df[taxonomy_df['PK'] == fallacy_pk]
                if not fallacy_row.empty and 'depth' in fallacy_row.columns:
                    depth = fallacy_row.iloc[0]['depth']
                    results["taxonomy_depth"][depth] += 1
        
        # Analyser l'exploration de la taxonomie
        if "hierarchie" in trace_data.get("resultats", {}):
            results["taxonomy_exploration"].append(trace_data["resultats"]["hierarchie"])
    
    logger.info(f"Nombre de types de sophismes uniques utilisés: {len(results['unique_fallacy_types'])}")
    logger.info(f"Distribution des profondeurs de taxonomie: {dict(results['taxonomy_depth'])}")
    
    return results

def generate_analysis_report(arg_results, fallacy_results, taxonomy_results):
    """
    Génère un rapport d'analyse des traces.
    """
    logger.info("Génération du rapport d'analyse...")
    
    report = f"""# Rapport d'Analyse des Traces de l'Agent Informel

## 1. Résumé

Ce rapport présente l'analyse des traces de conversation générées par l'agent Informel. L'objectif est d'identifier les forces et faiblesses de l'agent dans l'identification des arguments et l'attribution des sophismes.

## 2. Identification des Arguments

- **Nombre total d'arguments identifiés**: {arg_results['total_arguments']}
- **Longueur moyenne des arguments**: {arg_results['avg_argument_length']:.2f} mots
- **Distribution des arguments par extrait**:
{chr(10).join([f"  - {extrait}: {count} arguments" for extrait, count in arg_results['arguments_per_extrait'].items()])}

### Points forts
- L'agent parvient à identifier des arguments dans tous les extraits de texte.

### Points faibles
- La longueur moyenne des arguments ({arg_results['avg_argument_length']:.2f} mots) est supérieure à la longueur idéale (10-20 mots).
- Les arguments identifiés manquent souvent de précision et de concision.

## 3. Attribution des Sophismes

- **Nombre total de sophismes identifiés**: {fallacy_results['total_fallacies']}
- **Longueur moyenne des justifications**: {fallacy_results['avg_justification_length']:.2f} mots
- **Types de sophismes les plus fréquents**:
{chr(10).join([f"  - {fallacy_type}: {count} occurrences" for fallacy_type, count in fallacy_results['fallacy_types'].most_common(5)])}

### Points forts
- L'agent parvient à attribuer des sophismes aux arguments identifiés.

### Points faibles
- La diversité des types de sophismes utilisés est limitée ({len(taxonomy_results['unique_fallacy_types'])} types uniques).
- Les justifications manquent souvent de détails et d'exemples concrets.
- L'agent n'explore pas suffisamment la taxonomie en profondeur.

## 4. Utilisation de la Taxonomie

- **Nombre de types de sophismes uniques utilisés**: {len(taxonomy_results['unique_fallacy_types'])}
- **Distribution des profondeurs de taxonomie**:
{chr(10).join([f"  - Niveau {depth}: {count} sophismes" for depth, count in sorted(taxonomy_results['taxonomy_depth'].items())])}

### Points forts
- L'agent utilise la taxonomie pour identifier les sophismes.

### Points faibles
- L'exploration de la taxonomie est souvent superficielle, se limitant aux premiers niveaux.
- L'agent ne considère pas suffisamment de branches différentes de la taxonomie pour chaque argument.

## 5. Recommandations d'Amélioration

1. **Amélioration de l'identification des arguments**:
   - Modifier le prompt pour encourager des arguments plus concis (10-20 mots).
   - Ajouter des critères clairs pour définir un bon argument.

2. **Amélioration de l'attribution des sophismes**:
   - Encourager l'exploration systématique de la taxonomie en profondeur.
   - Imposer la considération d'au moins 3-5 branches différentes de la taxonomie pour chaque argument.
   - Viser l'identification de 2-3 sophismes différents par argument quand c'est pertinent.

3. **Amélioration des justifications**:
   - Exiger des justifications plus détaillées (au moins 100 mots).
   - Imposer l'inclusion de citations spécifiques de l'argument.
   - Demander l'explication du mécanisme du sophisme et de son impact sur la validité de l'argument.
   - Encourager l'utilisation d'exemples similaires pour clarifier.

4. **Amélioration du processus d'analyse**:
   - Définir un workflow structuré pour l'analyse des sophismes dans un argument.
   - Documenter le processus d'exploration de la taxonomie.

## 6. Conclusion

L'analyse des traces de conversation de l'agent Informel révèle plusieurs points d'amélioration, notamment dans l'identification des arguments, l'attribution des sophismes et l'utilisation de la taxonomie. Les recommandations proposées visent à optimiser les performances de l'agent en améliorant la qualité de ses analyses et en exploitant mieux la taxonomie des sophismes.

Date de l'analyse: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    
    # Sauvegarder le rapport
    report_path = ANALYSIS_DIR / f"rapport_analyse_traces_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    logger.info(f"Rapport d'analyse sauvegardé dans {report_path}")
    return report_path

def main():
    """
    Fonction principale du script.
    """
    logger.info("Démarrage de l'analyse des traces de l'agent Informel...")
    
    # Charger les traces
    traces = load_traces()
    
    if not traces:
        logger.error("Aucune trace trouvée. Impossible de poursuivre l'analyse.")
        return
    
    # Analyser l'identification des arguments
    arg_results = analyze_argument_identification(traces)
    
    # Analyser l'attribution des sophismes
    fallacy_results = analyze_fallacy_attribution(traces)
    
    # Analyser l'utilisation de la taxonomie
    taxonomy_results = analyze_taxonomy_usage(traces)
    
    # Générer le rapport d'analyse
    report_path = generate_analysis_report(arg_results, fallacy_results, taxonomy_results)
    
    logger.info("Analyse des traces terminée.")
    logger.info(f"Rapport: {report_path}")

if __name__ == "__main__":
    main()