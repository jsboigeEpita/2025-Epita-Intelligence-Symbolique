#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logique métier pour la réparation des bornes d'extraits.

Contient la classe ExtractRepairPlugin et les instructions pour les agents LLM,
ainsi que la fonction de génération de rapport.
"""

import logging
from typing import List, Dict, Any, Optional
from argumentation_analysis.models.extract_definition import (
    ExtractDefinitions,
)  # Ajuster si ExtractDefinitions est utilisé directement
from argumentation_analysis.services.extract_service import (
    ExtractService,
)  # S'assurer que ExtractService est accessible

# Configuration du logging pour ce module
logger = logging.getLogger("MarkerRepairLogic")
# Note: La configuration de base (handlers, level) est généralement faite au niveau de l'application (script d'exécution)

# --- Instructions pour les agents ---

# Instructions pour l'agent de réparation des bornes
REPAIR_AGENT_INSTRUCTIONS = """
Vous êtes un agent spécialisé dans la réparation des bornes défectueuses dans les extraits de texte.

Votre tâche est d'analyser un texte source et de trouver les bornes (marqueurs de début et de fin) 
qui correspondent le mieux à un extrait donné, même si les bornes actuelles sont incorrectes ou introuvables.

Processus à suivre:
1. Analyser le texte source fourni
2. Examiner les bornes actuelles (start_marker et end_marker)
3. Si les bornes sont introuvables, rechercher des séquences similaires dans le texte
4. Proposer des corrections pour les bornes défectueuses
5. Vérifier que les nouvelles bornes délimitent correctement l'extrait

Pour les corpus volumineux comme les discours d'Hitler:
- Utiliser une approche dichotomique pour localiser les discours
- Rechercher des motifs structurels (titres, numéros de pages, etc.)
- Créer des marqueurs plus robustes basés sur des séquences uniques

Règles importantes:
- Les bornes proposées doivent exister exactement dans le texte source
- Les bornes doivent délimiter un extrait cohérent et pertinent
- Privilégier les bornes qui correspondent à des éléments structurels du document
- Documenter clairement les modifications proposées et leur justification
"""

# Instructions pour l'agent de validation des bornes
VALIDATION_AGENT_INSTRUCTIONS = """
Vous êtes un agent spécialisé dans la validation des bornes d'extraits de texte.

Votre tâche est de vérifier que les bornes (marqueurs de début et de fin) proposées 
délimitent correctement un extrait cohérent et pertinent.

Processus à suivre:
1. Vérifier que les bornes existent exactement dans le texte source
2. Extraire le texte délimité par les bornes
3. Analyser la cohérence et la pertinence de l'extrait
4. Valider ou rejeter les bornes proposées

Critères de validation:
- Les bornes doivent exister exactement dans le texte source
- L'extrait doit être cohérent et avoir un sens complet
- L'extrait ne doit pas être trop court ni trop long
- L'extrait doit correspondre au sujet attendu

En cas de rejet:
- Expliquer clairement les raisons du rejet
- Proposer des alternatives si possible
"""

# --- Classes et fonctions ---


class ExtractRepairPlugin:
    """Plugin pour les fonctions natives de réparation des extraits."""

    def __init__(self, extract_service: ExtractService):
        """
        Initialise le plugin de réparation.

        Args:
            extract_service: Service d'extraction
        """
        self.extract_service = extract_service
        self.repair_results = []

    def find_similar_markers(
        self, text: str, marker: str, max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Trouve des marqueurs similaires dans le texte source.

        Args:
            text: Texte source
            marker: Marqueur à rechercher
            max_results: Nombre maximum de résultats

        Returns:
            Liste de marqueurs similaires
        """
        if not text or not marker:
            return []

        similar_markers = []
        # Assurez-vous que extract_service.find_similar_text est bien une méthode de ExtractService
        results = self.extract_service.find_similar_text(
            text, marker, context_size=50, max_results=max_results
        )

        for context, position, found_text in results:
            similar_markers.append(
                {"marker": found_text, "position": position, "context": context}
            )

        return similar_markers

    def update_extract_markers(
        self,
        extract_definitions: ExtractDefinitions,  # Type à vérifier/ajuster
        source_idx: int,
        extract_idx: int,
        new_start_marker: str,
        new_end_marker: str,
        template_start: Optional[str] = None,
    ) -> bool:
        """
        Met à jour les marqueurs d'un extrait.

        Args:
            extract_definitions: Définitions d'extraits (objet ExtractDefinitions)
            source_idx: Index de la source
            extract_idx: Index de l'extrait
            new_start_marker: Nouveau marqueur de début
            new_end_marker: Nouveau marqueur de fin
            template_start: Template pour le marqueur de début

        Returns:
            True si la mise à jour a réussi, False sinon
        """
        # Assumant que extract_definitions est un objet ExtractDefinitions
        # et non une liste de dictionnaires comme dans la version utils/
        if 0 <= source_idx < len(extract_definitions.sources):
            source_info = extract_definitions.sources[source_idx]
            extracts = (
                source_info.extracts
            )  # Assumant que c'est une liste d'objets Extract

            if 0 <= extract_idx < len(extracts):
                old_start = extracts[extract_idx].start_marker
                old_end = extracts[extract_idx].end_marker
                old_template = extracts[extract_idx].template_start

                extracts[extract_idx].start_marker = new_start_marker
                extracts[extract_idx].end_marker = new_end_marker

                if template_start:
                    extracts[extract_idx].template_start = template_start
                elif extracts[
                    extract_idx
                ].template_start:  # Si template_start est None/vide, on efface l'ancien
                    extracts[extract_idx].template_start = (
                        ""  # ou None, selon la définition du modèle
                    )

                # Enregistrer les modifications
                self.repair_results.append(
                    {
                        "source_name": source_info.source_name,
                        "extract_name": extracts[extract_idx].extract_name,
                        "old_start_marker": old_start,
                        "new_start_marker": new_start_marker,
                        "old_end_marker": old_end,
                        "new_end_marker": new_end_marker,
                        "old_template_start": old_template,
                        "new_template_start": template_start if template_start else "",
                    }
                )

                return True

        return False

    def get_repair_results(self) -> List[Dict[str, Any]]:
        """Récupère les résultats des réparations effectuées."""
        return self.repair_results


def generate_report(
    results: List[Dict[str, Any]], output_file: str = "repair_report.html"
):
    """
    Génère un rapport HTML des modifications effectuées.

    Args:
        results: Résultats des réparations (liste de dictionnaires comme défini dans le script original)
        output_file: Fichier de sortie pour le rapport HTML
    """
    logger.info(f"Génération du rapport dans '{output_file}'...")

    status_counts = {
        "valid": 0,
        "repaired": 0,
        "rejected": 0,
        "unchanged": 0,
        "error": 0,
    }

    repair_types = {"first_letter_missing": 0, "other": 0}

    for (
        result
    ) in (
        results
    ):  # results est la liste des dictionnaires produits par repair_extract_markers
        status = result.get("status", "error")
        if status in status_counts:
            status_counts[status] += 1

        if status == "repaired":
            old_start = result.get("old_start_marker", "")
            new_start = result.get("new_start_marker", "")
            old_template = result.get("old_template_start", "")

            # Logique de détection du type de réparation (simplifiée de l'original)
            # Cette logique peut nécessiter un ajustement si la structure de 'result' change
            if old_template and "{0}" in old_template:
                first_letter_template = old_template.replace("{0}", "")
                if (
                    new_start.startswith(first_letter_template)
                    and old_start == new_start[len(first_letter_template) :]
                ):
                    repair_types["first_letter_missing"] += 1
                else:
                    repair_types["other"] += 1
            else:
                repair_types["other"] += 1

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Rapport de réparation des bornes d'extraits</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2, h3 {{ color: #333; }}
            .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .valid {{ color: green; }}
            .repaired {{ color: blue; }}
            .rejected {{ color: orange; }}
            .unchanged {{ color: gray; }}
            .error {{ color: red; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .details {{ margin-top: 5px; font-size: 0.9em; color: #666; }}
            .repair-types {{ margin-top: 10px; padding: 10px; background-color: #e8f4f8; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>Rapport de réparation des bornes d'extraits</h1>
        
        <div class="summary">
            <h2>Résumé</h2>
            <p>Total des extraits analysés: <strong>{len(results)}</strong></p>
            <p>Extraits valides: <strong class="valid">{status_counts["valid"]}</strong></p>
            <p>Extraits réparés: <strong class="repaired">{status_counts["repaired"]}</strong></p>
            <p>Réparations rejetées: <strong class="rejected">{status_counts["rejected"]}</strong></p>
            <p>Extraits inchangés: <strong class="unchanged">{status_counts["unchanged"]}</strong></p>
            <p>Erreurs: <strong class="error">{status_counts["error"]}</strong></p>
            
            <div class="repair-types">
                <h3>Types de réparations</h3>
                <p>Première lettre manquante: <strong>{repair_types["first_letter_missing"]}</strong></p>
                <p>Autres types de réparations: <strong>{repair_types["other"]}</strong></p>
            </div>
        </div>
        
        <h2>Détails des réparations</h2>
        <table>
            <tr>
                <th>Source</th>
                <th>Extrait</th>
                <th>Statut</th>
                <th>Détails</th>
            </tr>
    """

    for result in results:
        source_name = result.get("source_name", "Source inconnue")
        extract_name = result.get("extract_name", "Extrait inconnu")
        status = result.get("status", "error")
        message = result.get("message", "Aucun message")

        details_html = ""  # Renommé pour éviter conflit de nom
        if status == "repaired":
            details_html += f"""
            <div class="details">
                <p><strong>Ancien marqueur de début:</strong> "{result.get('old_start_marker', '')}"</p>
                <p><strong>Nouveau marqueur de début:</strong> "{result.get('new_start_marker', '')}"</p>
                <p><strong>Ancien marqueur de fin:</strong> "{result.get('old_end_marker', '')}"</p>
                <p><strong>Nouveau marqueur de fin:</strong> "{result.get('new_end_marker', '')}"</p>
                <p><strong>Explication:</strong> {result.get('explanation', '')}</p>
            </div>
            """

        html_content += f"""
        <tr class="{status}">
            <td>{source_name}</td>
            <td>{extract_name}</td>
            <td>{status}</td>
            <td>{message}{details_html}</td>
        </tr>
        """

    html_content += """
        </table>
    </body>
    </html>
    """

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info(f"Rapport généré dans '{output_file}'.")
