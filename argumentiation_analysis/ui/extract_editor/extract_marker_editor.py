#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Éditeur de Marqueurs d'Extraits

Cet outil permet d'ajuster les bornes des extraits dans notre application d'analyse d'argumentation.

Fonctionnalités:
- Chargement des définitions d'extraits depuis `extract_sources.json`
- Visualisation des textes sources et des extraits actuels
- Vérification des marqueurs de début et de fin
- Ajustement interactif des bornes des extraits
- Sauvegarde des définitions corrigées
- Recherche de texte dans le document source
- Prévisualisation en temps réel des modifications
- Export/import des définitions modifiées
"""

# Imports nécessaires
import json
import logging
import os
import traceback
import asyncio
from pathlib import Path
import ipywidgets as widgets
from IPython.display import display, clear_output, HTML

# Importer les fonctions utiles depuis notre module ui
try:
    # Import relatif depuis le package ui
    from ...config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON, CACHE_DIR
    from ...extract_utils import (
        load_source_text, extract_text_with_markers, find_similar_text,
        highlight_text, search_in_text, highlight_search_results,
        load_extract_definitions_safely, save_extract_definitions_safely,
        export_definitions_to_json, import_definitions_from_json
    )
    from ...core.llm_service import create_llm_service
    # Import de l'agent d'extraction
    from ...agents.extract import setup_extract_agent
    config_import_success = True
except ImportError as e:
    # Fallback pour les imports absolus
    try:
        from ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON, CACHE_DIR
        from ui.extract_utils import (
            load_source_text, extract_text_with_markers, find_similar_text,
            highlight_text, search_in_text, highlight_search_results,
            load_extract_definitions_safely, save_extract_definitions_safely,
            export_definitions_to_json, import_definitions_from_json
        )
        from core.llm_service import create_llm_service
        # Import de l'agent d'extraction
        from agents.core.extract.extract_agent import setup_extract_agent
        config_import_success = True
    except ImportError as e:
        config_import_success = False
        print(f"⚠️ Erreur d'importation des modules UI: {e}")
        print("Les fonctionnalités dépendant de ces modules seront limitées.")
        # Définir des valeurs par défaut pour les variables manquantes
        ENCRYPTION_KEY = None
        CONFIG_FILE = Path("./data/extract_sources.json.gz.enc")
        CONFIG_FILE_JSON = Path("./data/extract_sources.json")
        CACHE_DIR = Path("./text_cache")

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ExtractMarkerEditor")

def create_marker_editor_ui():
    """Crée l'interface utilisateur pour l'éditeur de marqueurs."""
    # Chargement des définitions d'extraits
    print("Chargement des définitions d'extraits...")
    extract_definitions, error_message = load_extract_definitions_safely(CONFIG_FILE, ENCRYPTION_KEY, CONFIG_FILE_JSON)
    
    if not extract_definitions:
        print(f"❌ {error_message}")
        extract_definitions = []
    else:
        print(f"✅ {len(extract_definitions)} sources chargées.")

    # Widgets pour la sélection de la source et de l'extrait
    source_dropdown = widgets.Dropdown(
        options=[(s.get("source_name", f"Source #{i}"), i) for i, s in enumerate(extract_definitions)],
        description='Source:',
        style={'description_width': 'initial'},
        layout={'width': '50%'}
    )

    extract_dropdown = widgets.Dropdown(
        options=[],
        description='Extrait:',
        style={'description_width': 'initial'},
        layout={'width': '50%'}
    )

    # Widgets pour l'édition des marqueurs
    start_marker_input = widgets.Text(
        description='Marqueur début:',
        style={'description_width': 'initial'},
        layout={'width': '90%'}
    )

    end_marker_input = widgets.Text(
        description='Marqueur fin:',
        style={'description_width': 'initial'},
        layout={'width': '90%'}
    )

    template_start_input = widgets.Text(
        description='Template début:',
        style={'description_width': 'initial'},
        layout={'width': '90%'},
        placeholder="Ex: I{0} (où {0} sera remplacé par le marqueur de début)"
    )

    # Widgets pour la recherche
    search_input = widgets.Text(
        description='Rechercher:',
        style={'description_width': 'initial'},
        layout={'width': '70%'}
    )
    
    case_sensitive_checkbox = widgets.Checkbox(
        value=False,
        description='Respecter casse',
        style={'description_width': 'initial'}
    )
    
    search_button = widgets.Button(
        description='Rechercher',
        button_style='info',
        icon='search'
    )

    # Boutons d'action
    verify_button = widgets.Button(
        description='Vérifier',
        button_style='info',
        icon='check'
    )

    suggest_button = widgets.Button(
        description='Suggérer corrections',
        button_style='warning',
        icon='search'
    )
    
    extract_auto_button = widgets.Button(
        description='Extraire automatiquement',
        button_style='primary',
        icon='magic'
    )

    save_button = widgets.Button(
        description='Sauvegarder',
        button_style='success',
        icon='save'
    )
    
    # Boutons d'export/import
    export_button = widgets.Button(
        description='Exporter JSON',
        button_style='info',
        icon='download'
    )
    
    import_button = widgets.Button(
        description='Importer JSON',
        button_style='info',
        icon='upload'
    )
    
    # Widget pour le chemin d'export/import
    file_path_input = widgets.Text(
        value='./export_definitions.json',
        description='Chemin fichier:',
        style={'description_width': 'initial'},
        layout={'width': '70%'}
    )

    # Zones d'affichage
    status_output = widgets.Output()
    preview_output = widgets.Output()
    search_output = widgets.Output()

    # Affichage du texte extrait
    extract_display = widgets.HTML(
        value="<p>Sélectionnez une source et un extrait pour commencer.</p>",
        layout={'border': '1px solid #ddd', 'padding': '10px', 'margin': '10px 0', 'max_height': '300px', 'overflow': 'auto'}
    )

    # Affichage du texte source avec marqueurs en surbrillance
    source_display = widgets.HTML(
        value="<p>Texte source s'affichera ici.</p>",
        layout={'border': '1px solid #ddd', 'padding': '10px', 'margin': '10px 0', 'max_height': '500px', 'overflow': 'auto'}
    )

    # Suggestions de corrections
    suggestions_output = widgets.Output()
    
    # Navigation dans le texte source
    text_navigation = widgets.IntSlider(
        value=0,
        min=0,
        max=100,
        step=5,
        description='Position:',
        style={'description_width': 'initial'},
        layout={'width': '90%'}
    )
    
    # Prévisualisation en temps réel
    preview_checkbox = widgets.Checkbox(
        value=True,
        description='Prévisualisation en temps réel',
        style={'description_width': 'initial'}
    )

    # Fonction pour mettre à jour la liste des extraits
    def update_extract_list(change):
        source_idx = source_dropdown.value
        if source_idx is not None and 0 <= source_idx < len(extract_definitions):
            source_info = extract_definitions[source_idx]
            extracts = source_info.get("extracts", [])
            extract_dropdown.options = [(e.get("extract_name", f"Extrait #{i}"), i) for i, e in enumerate(extracts)]
        else:
            extract_dropdown.options = []

    # Fonction pour charger les détails de l'extrait sélectionné
    def load_extract_details(change):
        with status_output:
            clear_output(wait=True)
            print("Chargement des détails de l'extrait...")
        
        source_idx = source_dropdown.value
        extract_idx = extract_dropdown.value
        
        if source_idx is None or extract_idx is None:
            return
        
        source_info = extract_definitions[source_idx]
        extract_info = source_info.get("extracts", [])[extract_idx]
        
        # Mise à jour des champs d'édition
        start_marker_input.value = extract_info.get("start_marker", "")
        end_marker_input.value = extract_info.get("end_marker", "")
        template_start_input.value = extract_info.get("template_start", "")
        
        # Chargement du texte source
        source_text, url = load_source_text(source_info)
        
        if source_text:
            # Mise à jour du slider de navigation
            text_navigation.max = len(source_text)
            
            # Extraction du texte avec les marqueurs actuels
            extracted_text, status, start_found, end_found = extract_text_with_markers(
                source_text, 
                extract_info.get("start_marker", ""), 
                extract_info.get("end_marker", ""),
                extract_info.get("template_start", "")
            )
            
            # Mise en évidence des marqueurs dans le texte source
            highlighted_text, _, _ = highlight_text(
                source_text,
                extract_info.get("start_marker", ""),
                extract_info.get("end_marker", ""),
                extract_info.get("template_start", "")
            )
            
            # Affichage du texte extrait
            if extracted_text:
                extract_display.value = f"<h4>Texte extrait:</h4><p>{extracted_text[:1000]}</p>"
                if len(extracted_text) > 1000:
                    extract_display.value += "<p>[...]</p>"
            else:
                extract_display.value = "<p>Aucun texte extrait avec les marqueurs actuels.</p>"
            
            # Affichage du texte source avec marqueurs en surbrillance
            source_display.value = f"<h4>Texte source:</h4>{highlighted_text}"
            
            with status_output:
                clear_output(wait=True)
                print(f"Source: {source_info.get('source_name')}")
                print(f"Extrait: {extract_info.get('extract_name')}")
                print(f"URL: {url}")
                print(f"Statut: {status}")
        else:
            extract_display.value = "<p>Texte source non disponible.</p>"
            source_display.value = "<p>Texte source non disponible.</p>"
            
            with status_output:
                clear_output(wait=True)
                print(f"Source: {source_info.get('source_name')}")
                print(f"Extrait: {extract_info.get('extract_name')}")
                print(f"Erreur: {url}")

    # Fonction pour vérifier les marqueurs
    def verify_markers(b):
        source_idx = source_dropdown.value
        extract_idx = extract_dropdown.value
        
        if source_idx is None or extract_idx is None:
            with status_output:
                clear_output(wait=True)
                print("Veuillez sélectionner une source et un extrait.")
            return
        
        source_info = extract_definitions[source_idx]
        extract_info = source_info.get("extracts", [])[extract_idx]
        
        # Récupération des valeurs des champs d'édition
        start_marker = start_marker_input.value
        end_marker = end_marker_input.value
        template_start = template_start_input.value
        
        # Chargement du texte source
        source_text, url = load_source_text(source_info)
        
        if source_text:
            # Extraction du texte avec les marqueurs modifiés
            extracted_text, status, start_found, end_found = extract_text_with_markers(
                source_text, start_marker, end_marker, template_start
            )
            
            # Mise en évidence des marqueurs dans le texte source
            highlighted_text, _, _ = highlight_text(
                source_text, start_marker, end_marker, template_start
            )
            
            # Affichage du texte extrait
            if extracted_text:
                extract_display.value = f"<h4>Texte extrait:</h4><p>{extracted_text[:1000]}</p>"
                if len(extracted_text) > 1000:
                    extract_display.value += "<p>[...]</p>"
            else:
                extract_display.value = "<p>Aucun texte extrait avec les marqueurs actuels.</p>"
            
            # Affichage du texte source avec marqueurs en surbrillance
            source_display.value = f"<h4>Texte source:</h4>{highlighted_text}"
            
            with status_output:
                clear_output(wait=True)
                print(f"Source: {source_info.get('source_name')}")
                print(f"Extrait: {extract_info.get('extract_name')}")
                print(f"Statut: {status}")
        else:
            with status_output:
                clear_output(wait=True)
                print(f"Erreur: {url}")

    # Fonction pour suggérer des corrections
    def suggest_corrections(b):
        source_idx = source_dropdown.value
        extract_idx = extract_dropdown.value
        
        if source_idx is None or extract_idx is None:
            with suggestions_output:
                clear_output(wait=True)
                print("Veuillez sélectionner une source et un extrait.")
            return
        
        source_info = extract_definitions[source_idx]
        extract_info = source_info.get("extracts", [])[extract_idx]
        
        # Récupération des valeurs des champs d'édition
        start_marker = start_marker_input.value
        end_marker = end_marker_input.value
        
        # Chargement du texte source
        source_text, url = load_source_text(source_info)
        
        if not source_text:
            with suggestions_output:
                clear_output(wait=True)
                print(f"Erreur: {url}")
            return
        
        with suggestions_output:
            clear_output(wait=True)
            print("Recherche de suggestions...")
            
            # Recherche de textes similaires pour le marqueur de début
            if start_marker:
                print("\nSuggestions pour le marqueur de début:")
                similar_start = find_similar_text(source_text, start_marker)
                if similar_start:
                    for i, (context, pos, match) in enumerate(similar_start):
                        print(f"\nSuggestion {i+1}:")
                        print(f"Position: {pos}")
                        print(f"Contexte: ...{context}...")
                        print(f"Marqueur suggéré: {match}")
                        
                        # Bouton pour appliquer la suggestion
                        apply_button = widgets.Button(
                            description=f'Appliquer suggestion {i+1}',
                            button_style='primary',
                            layout={'margin': '5px'}
                        )
                        
                        def create_apply_handler(marker):
                            def apply_handler(b):
                                start_marker_input.value = marker
                                verify_markers(None)
                            return apply_handler
                        
                        apply_button.on_click(create_apply_handler(match))
                        display(apply_button)
                else:
                    print("Aucune suggestion trouvée pour le marqueur de début.")
            
            # Recherche de textes similaires pour le marqueur de fin
            if end_marker:
                print("\nSuggestions pour le marqueur de fin:")
                similar_end = find_similar_text(source_text, end_marker)
                if similar_end:
                    for i, (context, pos, match) in enumerate(similar_end):
                        print(f"\nSuggestion {i+1}:")
                        print(f"Position: {pos}")
                        print(f"Contexte: ...{context}...")
                        print(f"Marqueur suggéré: {match}")
                        
                        # Bouton pour appliquer la suggestion
                        apply_button = widgets.Button(
                            description=f'Appliquer suggestion {i+1}',
                            button_style='primary',
                            layout={'margin': '5px'}
                        )
                        
                        def create_apply_handler(marker):
                            def apply_handler(b):
                                end_marker_input.value = marker
                                verify_markers(None)
                            return apply_handler
                        
                        apply_button.on_click(create_apply_handler(match))
                        display(apply_button)
                else:
                    print("Aucune suggestion trouvée pour le marqueur de fin.")

    # Fonction pour rechercher du texte
    def search_text(b):
        source_idx = source_dropdown.value
        
        if source_idx is None:
            with search_output:
                clear_output(wait=True)
                print("Veuillez sélectionner une source.")
            return
        
        search_term = search_input.value
        if not search_term:
            with search_output:
                clear_output(wait=True)
                print("Veuillez entrer un terme de recherche.")
            return
        
        source_info = extract_definitions[source_idx]
        source_text, url = load_source_text(source_info)
        
        if not source_text:
            with search_output:
                clear_output(wait=True)
                print(f"Erreur: {url}")
            return
        
        with search_output:
            clear_output(wait=True)
            print(f"Recherche de '{search_term}' dans le texte source...")
            
            # Recherche et mise en évidence des résultats
            html_results, count = highlight_search_results(
                source_text, 
                search_term, 
                case_sensitive_checkbox.value
            )
            
            if count > 0:
                print(f"✅ {count} résultat(s) trouvé(s):")
                display(HTML(html_results))
            else:
                print(f"❌ Aucun résultat trouvé pour '{search_term}'.")

    # Fonction pour naviguer dans le texte source
    def navigate_text(change):
        source_idx = source_dropdown.value
        if source_idx is None:
            return
        
        source_info = extract_definitions[source_idx]
        source_text, url = load_source_text(source_info)
        
        if not source_text:
            return
        
        position = text_navigation.value
        context_size = 500  # Nombre de caractères à afficher avant et après la position
        
        start_pos = max(0, position - context_size)
        end_pos = min(len(source_text), position + context_size)
        
        visible_text = source_text[start_pos:end_pos]
        
        # Mise en évidence de la position actuelle
        html_text = visible_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        
        # Ajouter un marqueur à la position actuelle
        position_in_visible = position - start_pos
        if 0 <= position_in_visible < len(html_text):
            html_text = (
                html_text[:position_in_visible] +
                f"<span style='background-color: #FF5733; color: white;'>⬇</span>" +
                html_text[position_in_visible:]
            )
        
        source_display.value = f"<h4>Texte source (position {position}/{len(source_text)}):</h4>{html_text}"

    # Fonction pour prévisualiser en temps réel
    def preview_changes(change):
        if not preview_checkbox.value:
            return
        
        source_idx = source_dropdown.value
        extract_idx = extract_dropdown.value
        
        if source_idx is None or extract_idx is None:
            return
        
        source_info = extract_definitions[source_idx]
        source_text, _ = load_source_text(source_info)
        
        if not source_text:
            return
        
        # Récupération des valeurs des champs d'édition
        start_marker = start_marker_input.value
        end_marker = end_marker_input.value
        template_start = template_start_input.value
        
        # Extraction du texte avec les marqueurs modifiés
        extracted_text, status, _, _ = extract_text_with_markers(
            source_text, start_marker, end_marker, template_start
        )
        
        # Mise à jour de l'aperçu
        with preview_output:
            clear_output(wait=True)
            if extracted_text:
                print(f"Aperçu (prévisualisation en temps réel):")
                print(f"Statut: {status}")
                print(f"Extrait ({len(extracted_text)} caractères):")
                print(f"{extracted_text[:500]}...")
                if len(extracted_text) > 500:
                    print("...")
            else:
                print("Aucun texte extrait avec les marqueurs actuels.")

    # Fonction pour sauvegarder les modifications
    def save_modifications(b):
        source_idx = source_dropdown.value
        extract_idx = extract_dropdown.value
        
        if source_idx is None or extract_idx is None:
            with status_output:
                clear_output(wait=True)
                print("Veuillez sélectionner une source et un extrait.")
            return
        
        # Récupération des valeurs des champs d'édition
        start_marker = start_marker_input.value
        end_marker = end_marker_input.value
        template_start = template_start_input.value
        
        # Mise à jour des définitions
        extract_definitions[source_idx]["extracts"][extract_idx]["start_marker"] = start_marker
        extract_definitions[source_idx]["extracts"][extract_idx]["end_marker"] = end_marker
        if template_start:
            extract_definitions[source_idx]["extracts"][extract_idx]["template_start"] = template_start
        elif "template_start" in extract_definitions[source_idx]["extracts"][extract_idx]:
            del extract_definitions[source_idx]["extracts"][extract_idx]["template_start"]
        
        # Sauvegarde des définitions
        success, error_message = save_extract_definitions_safely(
            extract_definitions, CONFIG_FILE, ENCRYPTION_KEY, CONFIG_FILE_JSON
        )
        
        with status_output:
            clear_output(wait=True)
            if success:
                print("✅ Modifications sauvegardées avec succès.")
            else:
                print(f"❌ Erreur lors de la sauvegarde: {error_message}")

    # Fonction pour exporter les définitions
    def export_definitions(b):
        output_path = Path(file_path_input.value)
        success, message = export_definitions_to_json(extract_definitions, output_path)
        
        with status_output:
            clear_output(wait=True)
            print(message)

    # Fonction pour importer les définitions
    def import_definitions(b):
        nonlocal extract_definitions
        
        input_path = Path(file_path_input.value)
        if not input_path.exists():
            with status_output:
                clear_output(wait=True)
                print(f"❌ Fichier non trouvé: {input_path}")
            return
        
        success, result = import_definitions_from_json(input_path)
        
        with status_output:
            clear_output(wait=True)
            if success:
                extract_definitions = result
                print(f"✅ Définitions importées depuis {input_path}")
                
                # Mise à jour des dropdowns
                source_dropdown.options = [(s.get("source_name", f"Source #{i}"), i) for i, s in enumerate(extract_definitions)]
                extract_dropdown.options = []
            else:
                print(result)  # Afficher le message d'erreur

    # Fonction pour extraire automatiquement
    async def extract_automatically(b):
        source_idx = source_dropdown.value
        extract_idx = extract_dropdown.value
        
        if source_idx is None or extract_idx is None:
            with status_output:
                clear_output(wait=True)
                print("Veuillez sélectionner une source et un extrait.")
            return
        
        source_info = extract_definitions[source_idx]
        extract_info = source_info.get("extracts", [])[extract_idx]
        extract_name = extract_info.get("extract_name", f"Extrait #{extract_idx}")
        
        with status_output:
            clear_output(wait=True)
            print(f"Initialisation de l'agent d'extraction pour '{extract_name}'...")
        
        try:
            # Créer le service LLM
            llm_service = create_llm_service()
            if not llm_service:
                with status_output:
                    clear_output(wait=True)
                    print("❌ Impossible de créer le service LLM.")
                return
            
            # Initialiser l'agent d'extraction
            kernel, extract_agent = await setup_extract_agent(llm_service)
            if not extract_agent:
                with status_output:
                    clear_output(wait=True)
                    print("❌ Impossible d'initialiser l'agent d'extraction.")
                return
            
            with status_output:
                clear_output(wait=True)
                print(f"Extraction automatique en cours pour '{extract_name}'...")
            
            # Réparer l'extrait
            result = await extract_agent.repair_extract(extract_definitions, source_idx, extract_idx)
            
            if result.status == "valid":
                # Mettre à jour les champs d'édition
                start_marker_input.value = result.start_marker
                end_marker_input.value = result.end_marker
                if result.template_start:
                    template_start_input.value = result.template_start
                
                # Vérifier les marqueurs
                verify_markers(None)
                
                with status_output:
                    clear_output(wait=True)
                    print(f"✅ Extraction automatique réussie pour '{extract_name}'.")
                    print(f"Explication: {result.explanation}")
            else:
                with status_output:
                    clear_output(wait=True)
                    print(f"❌ Échec de l'extraction automatique: {result.message}")
                    if result.explanation:
                        print(f"Explication: {result.explanation}")
        except Exception as e:
            with status_output:
                clear_output(wait=True)
                print(f"❌ Erreur lors de l'extraction automatique: {str(e)}")
                traceback.print_exc()
    
    # Lier les callbacks
    source_dropdown.observe(update_extract_list, names='value')
    extract_dropdown.observe(load_extract_details, names='value')
    verify_button.on_click(verify_markers)
    suggest_button.on_click(suggest_corrections)
    extract_auto_button.on_click(lambda b: asyncio.create_task(extract_automatically(b)))
    save_button.on_click(save_modifications)
    search_button.on_click(search_text)
    export_button.on_click(export_definitions)
    import_button.on_click(import_definitions)
    text_navigation.observe(navigate_text, names='value')
    
    # Prévisualisation en temps réel
    start_marker_input.observe(preview_changes, names='value')
    end_marker_input.observe(preview_changes, names='value')
    template_start_input.observe(preview_changes, names='value')

    # Initialisation de la liste des extraits
    update_extract_list(None)

    # Création de l'interface
    editor_ui = widgets.VBox([
        widgets.HTML("<h1>Éditeur de Marqueurs d'Extraits</h1>"),
        widgets.HTML("<p>Cet outil permet d'ajuster les bornes des extraits dans l'application d'analyse d'argumentation.</p>"),
        widgets.HBox([source_dropdown, extract_dropdown]),
        widgets.HTML("<h3>Édition des marqueurs</h3>"),
        start_marker_input,
        end_marker_input,
        template_start_input,
        widgets.HBox([verify_button, suggest_button, extract_auto_button, save_button]),
        status_output,
        widgets.HTML("<h3>Prévisualisation</h3>"),
        preview_checkbox,
        preview_output,
        widgets.HTML("<h3>Navigation</h3>"),
        text_navigation,
        widgets.HTML("<h3>Recherche</h3>"),
        widgets.HBox([search_input, case_sensitive_checkbox, search_button]),
        search_output,
        widgets.HTML("<h3>Aperçu</h3>"),
        extract_display,
        source_display,
        widgets.HTML("<h3>Suggestions</h3>"),
        suggestions_output,
        widgets.HTML("<h3>Export/Import</h3>"),
        widgets.HBox([file_path_input, export_button, import_button])
    ])

    return editor_ui

# Fonction principale
def main():
    """Fonction principale pour exécuter l'éditeur de marqueurs."""
    editor_ui = create_marker_editor_ui()
    display(editor_ui)

if __name__ == "__main__":
    # Si exécuté directement, lancer l'interface
    main()