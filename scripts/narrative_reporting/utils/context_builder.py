# -*- coding: utf-8 -*-
"""
Module pour la construction du contexte technique et narratif.
"""
import json
import logging
import re
from pathlib import Path

def build_historical_context(reports_path: Path, num_chapters=2):
    """
    Charge les `num_chapters` derniers chapitres du rapport le plus récent pour servir de contexte.
    Cela évite de surcharger le contexte avec un historique complet, ce qui peut confondre le LLM.
    """
    if not reports_path.is_dir():
        logging.warning(f"Le répertoire des rapports '{reports_path}' n'existe pas.")
        return ""

    report_files = sorted([p for p in reports_path.glob("*.md") if p.name != "template_rapport.md"])
    if not report_files:
        logging.info("Aucun rapport historique trouvé.")
        return ""

    latest_report_path = report_files[-1]
    logging.info(f"Chargement du contexte historique depuis : {latest_report_path.name}")

    try:
        with open(latest_report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Utiliser une regex pour trouver tous les titres de chapitres
        chapters = re.split(r'(^###\s+Chapitre .+)', content, flags=re.MULTILINE)
        
        if len(chapters) > 1:
            # Reconstituer les chapitres avec leurs titres
            full_chapters = [chapters[i] + chapters[i+1] for i in range(1, len(chapters) -1, 2)]
            # Garder les N derniers chapitres
            context = "".join(full_chapters[-num_chapters:])
            logging.info(f"Extrait de {len(full_chapters)} chapitres. Utilisation des {num_chapters} derniers comme contexte.")
            return context
        else:
            # Si aucun chapitre n'est trouvé, retourner le contenu complet comme fallback
            logging.warning("Aucune structure de chapitre trouvée dans le dernier rapport, utilisation du contenu complet.")
            return content

    except Exception as e:
        logging.error(f"Impossible de lire ou de parser le rapport {latest_report_path}: {e}")
        return ""


def build_context(batch_files, full_report_content, historical_context, strategic_preamble):
    """
    Assemble le contexte enrichi (technique, narratif, historique, stratégique) pour le LLM.

    Args:
        batch_files (list): Liste des chemins vers les fichiers JSON du lot.
        full_report_content (str): Le contenu intégral du rapport en cours de rédaction.
        historical_context (str): La concaténation des rapports précédents.
        strategic_preamble (str): Le préambule expliquant le contexte métier.

    Returns:
        dict: Un dictionnaire contenant les quatre blocs de contexte.
    """
    technical_context = _build_technical_context(batch_files)
    narrative_context = _build_narrative_context(full_report_content)

    return {
        "technical_context": technical_context,
        "narrative_context": narrative_context,
        "historical_context": historical_context,
        "strategic_preamble": strategic_preamble,
    }

def _build_technical_context(batch_files, max_tokens=8000):
    """
    Construit le contexte technique en s'assurant de ne pas dépasser max_tokens.
    """
    context_parts = []
    total_tokens = 0
    
    start_commit = Path(batch_files[0]).stem
    end_commit = Path(batch_files[-1]).stem
    
    header = f"### Contexte Technique pour les Commits {start_commit} à {end_commit}\n\n"
    context_parts.append(header)
    total_tokens += len(header.split()) # Approximation rapide

    for file_path in batch_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            analysis_data = {}
            is_valid_format = False

            if "qualitative_analysis" in data:
                analysis_data = data["qualitative_analysis"]
                if "detailed_summary" in analysis_data:
                    is_valid_format = True
            elif "llm_summary" in data:
                analysis_data = {
                    "detailed_summary": data.get("llm_summary", ""),
                    "technical_debt_signals": [],
                    "quality_leaps": []
                }
                is_valid_format = True

            if is_valid_format:
                commit_hash = "N/A"
                filename = Path(file_path).stem
                relative_path = str(Path(file_path)).replace('\\', '/')
                parts = filename.split('-')
                if len(parts) > 6:
                    commit_hash = parts[-1]

                commit_summary = analysis_data.get('detailed_summary', 'N/A')
                # Simplification pour estimation de tokens; une vraie fonction serait plus précise.
                commit_tokens = len(commit_summary.split())
                
                if total_tokens + commit_tokens > max_tokens:
                    logging.warning(f"Limite de tokens atteinte. Troncature du contexte technique. Dernier commit traité : {filename}")
                    break
                
                total_tokens += commit_tokens

                context_parts.append(f"#### Analyse du Commit `{commit_hash[:7]}`\n")
                context_parts.append(f"**Source pour le référencement :** [{filename}]({relative_path})\n\n")
                context_parts.append(f"**Résumé Détaillé:**\n{commit_summary}\n")
                
                if analysis_data.get('technical_debt_signals'):
                    context_parts.append("\n**Signaux de Dette Technique Potentielle:**\n")
                    for signal in analysis_data['technical_debt_signals']:
                        context_parts.append(f"- {signal}\n")
                
                if analysis_data.get('quality_leaps'):
                    context_parts.append("\n**Sauts Qualitatifs Identifiés:**\n")
                    for leap in analysis_data['quality_leaps']:
                        context_parts.append(f"- {leap}\n")
                        
                context_parts.append("\n---\n")
            else:
                logging.warning(f"Structure de données non reconnue dans {file_path}. Clés présentes: {list(data.keys())}. Le fichier est ignoré.")

        except json.JSONDecodeError:
            logging.warning(f"Impossible de décoder JSON de {file_path}. Ignoré.")
        except Exception as e:
            logging.error(f"Erreur inattendue avec {file_path}: {e}")

    return "".join(context_parts)

def _build_narrative_context(full_report_content):
    """Construit le bloc de contexte narratif à partir du rapport existant."""
    if not full_report_content.strip():
        return "### Contexte Narratif Existant\n\nAucun chapitre n'a encore été rédigé. C'est le début du rapport."

    # Cette implémentation est une simplification. Une version plus robuste
    # pourrait parser les sections de manière plus intelligente (ex: avec regex).
    # Pour l'instant, on prend tout le contenu précédent.
    header = "### Contexte Narratif Existant\n\nVoici le contenu des chapitres déjà rédigés. Assurez la cohérence thématique et stylistique avec ce qui suit.\n\n"
    
    # On retire le premier en-tête pour ne pas le dupliquer
    report_body = "\n".join(full_report_content.split('\n')[2:])
    
    return f"{header}{report_body}"
