"""
Interface utilisateur pour la configuration des tâches d'analyse d'argumentation.

Ce module fournit des fonctions pour créer et gérer une interface utilisateur
basée sur ipywidgets dans un environnement Jupyter. Elle permet à l'utilisateur
de sélectionner des sources de texte (bibliothèque, URL, fichier, saisie directe),
de configurer des options d'extraction, et de lancer la préparation du texte
pour une analyse ultérieure.
"""
# ui/app.py
import ipywidgets as widgets
from IPython.display import display, clear_output
import time
import random
import traceback
import logging
from typing import Optional

# Importer les composants UI depuis les autres modules .py
from . import config as ui_config

# Importations des services de base
from ..config.settings import settings
from ..services.cache_service import CacheService
from ..services.fetch_service import FetchService

# Importer spécifiquement les fonctions/classes nécessaires des utils
from .file_operations import load_extract_definitions, save_extract_definitions
from .verification_utils import verify_extract_definitions
from .utils import reconstruct_url
from .cache_utils import load_from_cache

# Importer les constantes nécessaires depuis config
from .config import (
    ENCRYPTION_KEY,
    CONFIG_FILE,
)

# Event loop pour Jupyter
from jupyter_ui_poll import ui_events

app_logger = logging.getLogger("App.UI.App")
# Assurer un handler de base si non configuré globalement
if not app_logger.handlers and not app_logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    app_logger.addHandler(handler)
    app_logger.setLevel(logging.INFO)


# --- Fonction Principale de l'UI ---
def configure_analysis_task() -> Optional[str]:
    """
    Définit et gère l'interface utilisateur pour configurer la tâche d'analyse.
    Appelée depuis un environnement Jupyter, elle retourne le texte préparé.
    """
    app_logger.info("Lancement de configure_analysis_task...")
    texte_analyse_prepare_local = ""
    analyse_ready_to_run_local = False

    # --- Initialisation des Services ---
    app_logger.info("Initialisation des services (Cache, Fetch)...")
    cache_service = CacheService(settings)
    fetch_service = FetchService(cache_service, settings)
    app_logger.info("Services initialisés.")

    # Utiliser les variables importées depuis ui.config
    local_current_extract_definitions = load_extract_definitions(
        CONFIG_FILE, ENCRYPTION_KEY
    )

    # --- Création des Widgets ---
    source_mode_radio = widgets.RadioButtons(
        options=["Source Aléatoire", "Choisir Document & Extrait"],
        description="Mode:",
        value="Source Aléatoire",
        disabled=False,
        style={"description_width": "initial"},
    )
    valid_source_names = [
        s.get("source_name", f"Erreur Def #{i}")
        for i, s in enumerate(local_current_extract_definitions)
        if isinstance(s, dict)
    ]
    if not valid_source_names:
        app_logger.warning(
            "Aucune définition de source valide trouvée pour le dropdown."
        )
        valid_source_names = ["Erreur Chargement Config"]

    source_doc_dropdown = widgets.Dropdown(
        options=valid_source_names,
        description="Document:",
        disabled=True,
        style={"description_width": "initial"},
        layout={"width": "90%"},
    )
    extract_dropdown = widgets.Dropdown(
        options=[],
        description="Extrait:",
        disabled=True,
        style={"description_width": "initial"},
        layout={"width": "90%"},
    )
    tab_library = widgets.VBox(
        [source_mode_radio, source_doc_dropdown, extract_dropdown]
    )

    url_input = widgets.Text(
        placeholder="Entrez l'URL",
        description="URL:",
        layout={"width": "90%"},
        style={"description_width": "initial"},
    )
    url_processing_type_radio = widgets.RadioButtons(
        options=[
            ("Page Web (via Jina)", "jina"),
            ("Document PDF/Office (via Tika)", "tika"),
        ],
        description="Type:",
        value="jina",
        disabled=False,
        style={"description_width": "initial"},
    )
    tab_url = widgets.VBox(
        [
            widgets.Label("Entrez l'URL et choisissez le type:"),
            url_input,
            url_processing_type_radio,
        ]
    )

    file_uploader = widgets.FileUpload(
        accept=".txt,.pdf,.doc,.docx,.html,.xml,.md",
        multiple=False,
        description="Fichier:",
        style={"description_width": "initial"},
    )
    tab_file = widgets.VBox(
        [
            widgets.Label("Téléversez fichier (traité par Tika si besoin):"),
            file_uploader,
        ]
    )

    direct_text_input = widgets.Textarea(
        placeholder="Collez texte ici...", layout={"width": "90%", "height": "200px"}
    )
    tab_direct = widgets.VBox(
        [widgets.Label("Saisissez le texte :"), direct_text_input]
    )

    start_marker_input = widgets.Text(
        placeholder="(Optionnel) Début (exclus)",
        description="Début Extrait:",
        layout={"width": "90%"},
        style={"description_width": "initial"},
    )
    end_marker_input = widgets.Text(
        placeholder="(Optionnel) Fin (exclue)",
        description="Fin Extrait:",
        layout={"width": "90%"},
        style={"description_width": "initial"},
    )
    extraction_box = widgets.VBox(
        [
            widgets.HTML("<hr><h4>Options d'Extraction (Optionnel)</h4>"),
            widgets.HTML(
                "<p style='font-size:0.9em; color:grey;'>Marqueurs uniques. Exclus du résultat.</p>"
            ),
            start_marker_input,
            end_marker_input,
        ]
    )

    # --- Déplacer la config dans son propre widget/tab ---
    config_output_area = widgets.HTML(
        value="<i>Chargement...</i>",
        layout={
            "border": "1px solid #ccc",
            "padding": "5px",
            "margin_top": "5px",
            "max_height": "200px",
            "overflow_y": "auto",
        },
    )
    load_config_button = widgets.Button(
        description="Charger/Actualiser Déf.",
        icon="refresh",
        button_style="info",
        tooltip="Charge les définitions",
    )
    save_config_button = widgets.Button(
        description="Sauvegarder Déf.",
        icon="save",
        button_style="warning",
        disabled=(not ENCRYPTION_KEY),
        tooltip="Sauvegarde les définitions",
    )
    verify_button = widgets.Button(
        description="Vérifier Marqueurs",
        icon="check",
        button_style="primary",
        tooltip="Vérifie les marqueurs",
    )
    config_management_box = widgets.VBox(
        [
            widgets.HTML("<h3>Gestion Configuration Sources</h3>"),
            widgets.HTML(
                "<p>Chargez, sauvegardez (si une passphrase est définie dans .env), ou vérifiez les marqueurs des sources prédéfinies.</p>"
            ),
            widgets.HBox([load_config_button, save_config_button, verify_button]),
            config_output_area,
        ]
    )
    tab_config_mgmt = (
        config_management_box  # Le VBox entier devient le contenu du nouvel onglet
    )

    # --- Modification: Ajout tab_config_mgmt aux enfants des onglets ---
    tabs = widgets.Tab(
        children=[tab_library, tab_url, tab_file, tab_direct, tab_config_mgmt]
    )
    tabs.set_title(0, "📚 Bibliothèque")
    tabs.set_title(1, "🌐 URL")
    tabs.set_title(2, "📄 Fichier")
    tabs.set_title(3, "✍️ Texte Direct")
    tabs.set_title(4, "⚙️ Config Sources")  # Titre du nouvel onglet

    prepare_button = widgets.Button(
        description="Préparer le Texte",
        button_style="info",
        icon="cogs",
        tooltip="Charge, extrait et prépare texte.",
    )
    run_button = widgets.Button(
        description="Lancer l'Analyse",
        button_style="success",
        icon="play",
        disabled=True,
        tooltip="Démarre l'analyse.",
    )
    main_output_area = widgets.Output(
        layout={
            "border": "1px solid #ccc",
            "padding": "10px",
            "margin_top": "10px",
            "min_height": "100px",
        }
    )

    # --- Callbacks ---
    def update_extract_options_ui(change):
        nonlocal extract_dropdown, source_doc_dropdown
        # Utilise la variable locale contenant les définitions chargées
        selected_doc_name = change.get("new", source_doc_dropdown.value)
        source_info = next(
            (
                s
                for s in local_current_extract_definitions
                if isinstance(s, dict) and s.get("source_name") == selected_doc_name
            ),
            None,
        )
        if source_info:
            extract_options = ["Texte Complet"] + [
                e.get("extract_name", "Sans Nom")
                for e in source_info.get("extracts", [])
                if isinstance(e, dict)
            ]
            current_extract_value = extract_dropdown.value
            extract_dropdown.options = extract_options
            if current_extract_value in extract_options:
                extract_dropdown.value = current_extract_value
            elif extract_options:
                extract_dropdown.value = extract_options[0]
            else:
                extract_dropdown.value = None
        else:
            extract_dropdown.options = []
            extract_dropdown.value = None
        # Visibilité MAJ via l'observeur sur extract_dropdown

    def handle_source_mode_change_ui(change):
        nonlocal source_doc_dropdown, extract_dropdown, source_mode_radio
        # --- Ajout Debug Prints ---
        print(
            f"DEBUG: handle_source_mode_change_ui appelé. Nouvelle valeur: {change.get('new', source_mode_radio.value)}"
        )
        is_manual_choice = (
            change.get("new", source_mode_radio.value) == "Choisir Document & Extrait"
        )
        print(f"DEBUG: is_manual_choice = {is_manual_choice}")

        # Mise à jour état disabled
        source_doc_dropdown.disabled = not is_manual_choice
        extract_dropdown.disabled = not is_manual_choice
        print(f"DEBUG: source_doc_dropdown.disabled = {source_doc_dropdown.disabled}")
        print(f"DEBUG: extract_dropdown.disabled = {extract_dropdown.disabled}")
        # --- Fin Debug Prints ---

        if is_manual_choice:
            if source_doc_dropdown.options and source_doc_dropdown.value:
                update_extract_options_ui({"new": source_doc_dropdown.value})
            else:
                extract_dropdown.options = []
                extract_dropdown.value = None
        else:  # Cas 'Source Aléatoire'
            extract_dropdown.options = []
            extract_dropdown.value = None
        update_extraction_box_visibility()

    def display_definitions_in_ui(definitions_list):
        # Utilise reconstruct_url importé
        if not definitions_list:
            return "Aucune définition chargée."
        MAX_EXTRACTS_DISPLAY = 5
        html = "<ul style='list-style-type: none; padding-left: 0;'>"
        for source in definitions_list:
            if not isinstance(source, dict):
                continue
            source_name_display = source.get("source_name", "Erreur: Nom Manquant")
            html += f"<li style='margin-bottom: 10px;'><b>{source_name_display}</b> ({source.get('source_type', 'N/A')})"
            reconstructed = reconstruct_url(
                source.get("schema"), source.get("host_parts", []), source.get("path")
            )
            html += f"<br/><small style='color:grey;'>{reconstructed or 'URL Invalide'}</small>"
            extracts = source.get("extracts", [])
            if extracts and isinstance(extracts, list):
                html += "<ul style='margin-top: 4px; font-size: 0.9em; list-style-type: none; padding-left: 10px;'>"
                for i, extract in enumerate(extracts):
                    if not isinstance(extract, dict):
                        continue
                    if i >= MAX_EXTRACTS_DISPLAY:
                        html += f"<li>... et {len(extracts) - MAX_EXTRACTS_DISPLAY} autre(s)</li>"
                        break
                    extract_name_display = extract.get(
                        "extract_name", "Erreur: Nom Extrait Manquant"
                    )
                    html += f"<li>- {extract_name_display}</li>"
                html += "</ul>"
            html += "</li>"
        html += "</ul>"
        return html

    def on_load_config_click_ui(b):
        nonlocal config_output_area, source_doc_dropdown, save_config_button, extract_dropdown, main_output_area, local_current_extract_definitions
        with main_output_area:
            clear_output(wait=True)
            app_logger.info("⏳ Chargement définitions depuis fichier chiffré...")
        # Met à jour la variable locale
        local_current_extract_definitions = load_extract_definitions(
            CONFIG_FILE, ENCRYPTION_KEY
        )
        valid_defs = [
            s
            for s in local_current_extract_definitions
            if isinstance(s, dict) and "source_name" in s
        ]
        if len(valid_defs) != len(local_current_extract_definitions):
            app_logger.warning(
                "⚠️ Attention: Certaines définitions chargées/par défaut étaient invalides."
            )
        local_current_extract_definitions = valid_defs  # Garder seulement les valides

        config_output_area.value = display_definitions_in_ui(
            local_current_extract_definitions
        )
        current_doc_selection = source_doc_dropdown.value
        source_doc_options = [
            s["source_name"] for s in local_current_extract_definitions
        ]
        source_doc_dropdown.options = source_doc_options
        if current_doc_selection in source_doc_options:
            source_doc_dropdown.value = current_doc_selection
        elif source_doc_options:
            source_doc_dropdown.value = source_doc_options[0]
        else:
            source_doc_dropdown.value = None

        if source_doc_dropdown.value:
            update_extract_options_ui({"new": source_doc_dropdown.value})
        else:
            extract_dropdown.options = []
            update_extraction_box_visibility()

        with main_output_area:
            clear_output(wait=True)
            app_logger.info("[OK] Définitions chargées/actualisées.")
        save_config_button.disabled = not ENCRYPTION_KEY

    def on_save_config_click_ui(b):
        nonlocal main_output_area, local_current_extract_definitions
        with main_output_area:
            clear_output(wait=True)
            app_logger.info("⏳ Sauvegarde définitions...")
        success = save_extract_definitions(
            local_current_extract_definitions, CONFIG_FILE, ENCRYPTION_KEY
        )
        if success:
            app_logger.info("[OK] Définitions sauvegardées.")
        else:
            app_logger.error("❌ Échec sauvegarde.")

    def on_verify_click_ui(b):
        nonlocal main_output_area, local_current_extract_definitions
        with main_output_area:
            clear_output(wait=True)
            app_logger.info("Lancement de la vérification (peut prendre du temps)...")
            summary = verify_extract_definitions(
                local_current_extract_definitions, fetch_service
            )
            clear_output(wait=True)
            display(widgets.HTML(summary))
            app_logger.info("Vérification terminée.")

    def on_prepare_click_ui(b):
        nonlocal texte_analyse_prepare_local, analyse_ready_to_run_local, run_button, main_output_area, local_current_extract_definitions
        analyse_ready_to_run_local = False
        run_button.disabled = True
        texte_brut_source = ""
        source_description = ""
        start_marker_final = ""
        end_marker_final = ""

        with main_output_area:
            clear_output(wait=True)
            app_logger.info("⏳ Préparation texte...")
            selected_tab_index = tabs.selected_index
            try:
                # --- Logique de récupération texte_brut_source ---
                if selected_tab_index == 0:  # Bibliothèque
                    source_info = None
                    extract_info = None
                    reconstructed_url = None
                    if source_mode_radio.value == "Source Aléatoire":
                        if not local_current_extract_definitions:
                            raise ValueError("Biblio vide!")
                        source_info = random.choice(local_current_extract_definitions)
                        extracts_available = source_info.get("extracts", [])
                        potential_extracts = [
                            {"extract_name": "Texte Complet"}
                        ] + extracts_available
                        extract_info = random.choice(potential_extracts)
                        app_logger.info(
                            f"-> Choix Aléatoire: Doc='{source_info.get('source_name', '?')}', Extrait='{extract_info['extract_name']}'"
                        )
                    else:  # Choisir Document & Extrait
                        selected_doc_name = source_doc_dropdown.value
                        selected_extract_name = extract_dropdown.value
                        if not selected_doc_name:
                            raise ValueError("Aucun document sélectionné.")
                        source_info = next(
                            (
                                s
                                for s in local_current_extract_definitions
                                if s.get("source_name") == selected_doc_name
                            ),
                            None,
                        )
                        if not source_info:
                            raise ValueError(f"Doc '{selected_doc_name}' non trouvé.")
                        if selected_extract_name == "Texte Complet":
                            extract_info = {"extract_name": "Texte Complet"}
                        else:
                            extract_info = next(
                                (
                                    e
                                    for e in source_info.get("extracts", [])
                                    if e.get("extract_name") == selected_extract_name
                                ),
                                None,
                            )
                        if not extract_info:
                            raise ValueError(
                                f"Extrait '{selected_extract_name}' non trouvé."
                            )
                        app_logger.info(
                            f"-> Choix Manuel: Doc='{source_info['source_name']}', Extrait='{extract_info['extract_name']}'"
                        )

                    # Utiliser les marqueurs prédéfinis SI PAS "Texte Complet"
                    start_marker_final = (
                        extract_info.get("start_marker", "")
                        if extract_info.get("extract_name") != "Texte Complet"
                        else ""
                    )
                    end_marker_final = (
                        extract_info.get("end_marker", "")
                        if extract_info.get("extract_name") != "Texte Complet"
                        else ""
                    )
                    # Si c'est "Texte Complet", vérifier si marqueurs manuels sont fournis
                    if extract_info.get("extract_name") == "Texte Complet":
                        manual_start = start_marker_input.value.strip()
                        manual_end = end_marker_input.value.strip()
                        if manual_start:
                            start_marker_final = manual_start
                        if manual_end:
                            end_marker_final = manual_end

                    reconstructed_url = reconstruct_url(
                        source_info.get("schema"),
                        source_info.get("host_parts", []),
                        source_info.get("path"),
                    )
                    if not reconstructed_url:
                        raise ValueError("URL source invalide.")
                    source_description = f"Biblio: {source_info.get('source_name','?')} ({extract_info.get('extract_name','?')})"

                    # Vérifier d'abord si full_text est disponible dans source_info
                    texte_brut_source = source_info.get("full_text")
                    if texte_brut_source:
                        app_logger.info(
                            f"-> Texte chargé depuis le champ 'full_text' embarqué pour: {source_info.get('source_name')}"
                        )
                    else:
                        app_logger.info(
                            f"-> 'full_text' non trouvé ou vide pour {source_info.get('source_name')}. Tentative de récupération classique..."
                        )
                        cached_text = load_from_cache(reconstructed_url)
                        if cached_text is not None:
                            texte_brut_source = cached_text
                            app_logger.info(
                                f"   -> Texte chargé depuis cache fichier pour: {reconstructed_url}"
                            )
                        else:
                            source_type = source_info.get("source_type")
                            original_path_str = source_info.get("path", "")
                            is_plaintext_url = any(
                                original_path_str.lower().endswith(ext)
                                for ext in ui_config.PLAINTEXT_EXTENSIONS
                            )
                            app_logger.info(
                                f"   -> Cache vide. Récupération (Type: {source_type}, URL: ...)..."
                            )
                            if source_type == "jina":
                                texte_brut_source = fetch_service.fetch_website_content(
                                    reconstructed_url
                                )
                            elif source_type == "direct_download":
                                texte_brut_source = fetch_service.fetch_direct_text(
                                    reconstructed_url
                                )
                            elif source_type == "tika":
                                # Le FetchService gère la distinction plaintext/binaire pour Tika
                                texte_brut_source = (
                                    fetch_service.fetch_document_content(
                                        source_url=reconstructed_url
                                    )
                                )
                            else:
                                raise ValueError(
                                    f"Type source inconnu '{source_type}'."
                                )

                        # Si le texte a été fetché (et non chargé depuis full_text initial), le stocker dans source_info
                        # pour les utilisations futures au sein de cette session.
                        # Cela n'affecte pas le fichier extract_sources.json.gz.enc sans sauvegarde explicite.
                        if (
                            source_info
                            and texte_brut_source is not None
                            and not source_info.get("full_text")
                        ):
                            source_info[
                                "full_text"
                            ] = texte_brut_source  # Mettre à jour l'objet en mémoire
                            app_logger.info(
                                f"   -> Champ 'full_text' mis à jour en mémoire pour la source biblio: {source_info.get('source_name')} après fetch."
                            )

                elif selected_tab_index in [1, 2, 3]:  # URL, Fichier, Texte Direct
                    start_marker_final = start_marker_input.value.strip()
                    end_marker_final = end_marker_input.value.strip()
                    # ... [Code identique pour récupérer texte_brut_source pour URL/Fichier/Texte Direct] ...
                    if selected_tab_index == 1:  # URL
                        url = url_input.value.strip()
                        processing_type = url_processing_type_radio.value
                        if not url or not url.startswith(("http://", "https://")):
                            raise ValueError("URL invalide.")
                        source_description = f"URL ({processing_type.upper()}): {url}"
                        cached_text = load_from_cache(url)
                        if cached_text is not None:
                            texte_brut_source = cached_text
                        else:
                            if processing_type == "jina":
                                texte_brut_source = fetch_service.fetch_website_content(
                                    url
                                )
                            elif processing_type == "tika":
                                # Le FetchService gère la distinction plaintext/binaire
                                texte_brut_source = (
                                    fetch_service.fetch_document_content(source_url=url)
                                )
                            else:
                                raise ValueError(
                                    f"Type traitement inconnu: {processing_type}"
                                )
                    elif selected_tab_index == 2:  # Fichier
                        if not file_uploader.value:
                            raise ValueError("Veuillez téléverser un fichier.")
                        uploaded_file_info = file_uploader.value[0]
                        file_name = uploaded_file_info["name"]
                        cache_key = f"file://{file_name}"
                        cached_text = load_from_cache(cache_key)
                        if cached_text is not None:
                            texte_brut_source = cached_text
                            source_description = f"Fichier (Cache): {file_name}"
                        else:
                            is_plaintext_file = any(
                                file_name.lower().endswith(ext)
                                for ext in ui_config.PLAINTEXT_EXTENSIONS
                            )
                            file_content_bytes = uploaded_file_info["content"]
                            source_description = f"Fichier: {file_name}"
                            texte_brut_source = fetch_service.fetch_document_content(
                                file_content=file_content_bytes, file_name=file_name
                            )
                        try:
                            file_uploader.value = {}
                            file_uploader._counter = 0
                        except Exception:
                            pass
                    elif selected_tab_index == 3:  # Texte Direct
                        texte_brut_source = direct_text_input.value
                        source_description = "Texte Direct"
                        if not texte_brut_source:
                            raise ValueError("Veuillez saisir du texte.")
                        app_logger.info(
                            f"-> Utilisation texte direct (longueur: {len(texte_brut_source)})."
                        )

                else:
                    raise ValueError("Onglet inconnu.")

                # --- Application finale des marqueurs ---
                # (Logique identique, utilise start_marker_final et end_marker_final définis ci-dessus)
                texte_final = texte_brut_source
                if start_marker_final or end_marker_final:
                    # ... [Code identique pour appliquer marqueurs] ...
                    app_logger.info("\n-> Application marqueurs...")
                    start_index = 0
                    end_index = len(texte_brut_source)

                    # Récupérer le template si disponible (pour les extraits avec lettres manquantes)
                    template_start = None
                    if (
                        selected_tab_index == 0
                        and extract_info
                        and extract_info.get("extract_name") != "Texte Complet"
                    ):
                        template_start = extract_info.get("template_start")

                    if start_marker_final:
                        try:
                            # Essayer d'abord avec le marqueur tel quel
                            found_start = texte_brut_source.index(start_marker_final)
                            start_index = found_start + len(start_marker_final)
                            app_logger.info("   -> Début trouvé.")
                        except ValueError:
                            # Si échec et template disponible, essayer avec le template
                            if template_start:
                                app_logger.info(
                                    f"   -> Tentative avec template '{template_start}' pour marqueur début..."
                                )
                                # Le template est de la forme "X{0}" où X est la lettre manquante
                                # et {0} est remplacé par le reste du marqueur
                                try:
                                    # Remplacer {0} dans le template par le marqueur original
                                    complete_marker = template_start.replace(
                                        "{0}", start_marker_final
                                    )
                                    found_start = texte_brut_source.index(
                                        complete_marker
                                    )
                                    start_index = found_start + len(complete_marker)
                                    app_logger.info(
                                        f"   -> Début trouvé avec template: '{complete_marker}'"
                                    )
                                except ValueError:
                                    app_logger.warning(
                                        "   ⚠️ Marqueur début non trouvé même avec template."
                                    )
                                    start_index = 0
                            else:
                                app_logger.warning("   ⚠️ Marqueur début non trouvé.")
                                start_index = 0

                    if end_marker_final:
                        try:
                            found_end = texte_brut_source.index(
                                end_marker_final, start_index
                            )
                            end_index = found_end
                            app_logger.info("   -> Fin trouvée.")
                        except ValueError:
                            app_logger.warning(
                                "   ⚠️ Marqueur fin non trouvé (après début)."
                            )
                            end_index = len(texte_brut_source)
                    if start_index < end_index:
                        texte_final = texte_brut_source[start_index:end_index].strip()
                        if texte_final and (start_marker_final or end_marker_final):
                            source_description += " (Extrait)"
                        if not texte_final and texte_brut_source:
                            app_logger.warning("   -> Résultat extraction vide.")
                    else:
                        app_logger.warning(
                            f"   -> Conflit marqueurs (start={start_index}, end={end_index}). Résultat vide."
                        )
                        texte_final = ""

                # --- Finalisation ---
                texte_analyse_prepare_local = texte_final
                if not texte_analyse_prepare_local:
                    app_logger.warning("\n⚠️ Texte préparé final est vide !")
                # ... [Reste du code identique pour afficher preview et activer bouton run] ...
                with main_output_area:
                    clear_output(wait=True)
                    print("--- Aperçu Texte Préparé ---")
                    preview = texte_analyse_prepare_local[:1500]
                    print(
                        preview
                        + ("\n[...]" if len(texte_analyse_prepare_local) > 1500 else "")
                    )
                    print("-" * 30)
                    print(
                        f"\n[OK] Texte préparé (Source: {source_description}, Longueur: {len(texte_analyse_prepare_local)})."
                    )
                    if len(texte_analyse_prepare_local) > 0:
                        print("\n➡️ Cliquez sur 'Lancer l'Analyse'.")
                        run_button.disabled = False
                    else:
                        print("\nTexte vide. Impossible de lancer l'analyse.")
                        run_button.disabled = True

            except Exception as e:
                app_logger.error(
                    f"\n❌ Erreur Préparation : {type(e).__name__} - {e}", exc_info=True
                )
                with main_output_area:
                    clear_output(wait=True)
                    print(f"\n❌ Erreur Préparation : {type(e).__name__} - {e}")
                    print("\n--- Traceback ---")
                    traceback.print_exc()
                    print("-" * 25)
                run_button.disabled = True
                texte_analyse_prepare_local = ""

    def on_run_click_ui(b):
        # ... [Code identique pour on_run_click_ui] ...
        nonlocal analyse_ready_to_run_local, texte_analyse_prepare_local
        if run_button.disabled or not texte_analyse_prepare_local:
            with main_output_area:
                clear_output(wait=True)
                print("⚠️ Préparez un texte non vide avant.")
        else:
            analyse_ready_to_run_local = True
            prepare_button.disabled = True
            run_button.disabled = True
            tabs.disabled = True
            start_marker_input.disabled = True
            end_marker_input.disabled = True
            load_config_button.disabled = True
            save_config_button.disabled = True
            verify_button.disabled = True
            source_mode_radio.disabled = True
            source_doc_dropdown.disabled = True
            extract_dropdown.disabled = True
            url_input.disabled = True
            url_processing_type_radio.disabled = True
            file_uploader.disabled = True
            direct_text_input.disabled = True
            extraction_box.layout.display = "none"
            with main_output_area:
                clear_output(wait=True)
                print(
                    f"📝 Texte final prêt (Longueur: {len(texte_analyse_prepare_local)})."
                )
                print("\n🚀 Lancement analyse demandé...")
            app_logger.info("Bouton 'Lancer l'Analyse' cliqué. Fin interaction UI.")

    # Fonction pour gérer la visibilité de extraction_box
    def update_extraction_box_visibility(*args):
        nonlocal tabs, source_mode_radio, extract_dropdown, extraction_box
        try:
            is_library_tab = tabs.selected_index == 0
            is_random_mode = source_mode_radio.value == "Source Aléatoire"
            is_full_text_extract = extract_dropdown.value == "Texte Complet"
            # Visible si: PAS Bibliothèque OU (Bibliothèque ET (Aléatoire OU Texte Complet sélectionné))
            should_be_visible = (not is_library_tab) or (
                is_library_tab and (is_random_mode or is_full_text_extract)
            )
            extraction_box.layout.display = "" if should_be_visible else "none"
            app_logger.debug(f"Visibilité extraction_box: {should_be_visible}")
        except Exception as e_vis:
            app_logger.error(
                f"Erreur maj visibilité extraction_box: {e_vis}", exc_info=True
            )
            extraction_box.layout.display = ""  # Fallback visible

    # --- Lier Callbacks ---
    prepare_button.on_click(on_prepare_click_ui)
    run_button.on_click(on_run_click_ui)
    load_config_button.on_click(on_load_config_click_ui)
    save_config_button.on_click(on_save_config_click_ui)
    verify_button.on_click(on_verify_click_ui)
    # Lier widgets pour visibilité extraction_box
    tabs.observe(update_extraction_box_visibility, names="selected_index")
    source_mode_radio.observe(
        handle_source_mode_change_ui, names="value"
    )  # Modifié pour appeler handle qui appelle update_visibility
    extract_dropdown.observe(update_extraction_box_visibility, names="value")
    # Lier dropdown doc pour mettre à jour options extrait
    source_doc_dropdown.observe(update_extract_options_ui, names="value")

    # --- Affichage et Boucle ---
    app_logger.info("Construction de l'interface principale VBox...")
    # --- Modification: Utiliser le VBox principal ui_container ---
    ui_container = widgets.VBox(
        [
            widgets.HTML("<h2>Configuration Tâche Analyse</h2>"),
            widgets.HTML("<h3>1. Source & Extraction</h3>"),  # Titre regroupant
            tabs,  # Contient maintenant l'onglet Config Sources
            extraction_box,  # Options d'extraction manuelles (visibilité gérée)
            widgets.HTML(
                "<hr style='margin-top: 20px'><h3>2. Préparation & Lancement</h3>"
            ),  # Nouveau titre section
            prepare_button,
            main_output_area,
            run_button,
        ]
    )

    # --- Affichage Final ---
    app_logger.info("Affichage de l'interface utilisateur...")
    print("Initialisation interface...")  # Message pour l'utilisateur final
    display(ui_container)

    # --- Initialisation État UI ---
    # Charger la config ET mettre à jour l'état initial des options + visibilité
    # Note: on_load_config_click_ui déclenchera les mises à jour nécessaires via observe
    on_load_config_click_ui(None)
    # Mettre à jour l'état initial des dropdowns et la visibilité
    handle_source_mode_change_ui(
        {}
    )  # Important de le faire APRES on_load pour avoir les bonnes options

    print("\n⏳ En attente interaction...")
    app_logger.info("Interface affichée, en attente interaction via ui_events...")
    with ui_events() as poll:
        while not analyse_ready_to_run_local:
            poll(10)
            time.sleep(0.1)

    app_logger.info("Interaction UI terminée.")
    print("\n🏁 Configuration tâche terminée. Retour au notebook principal...")
    return texte_analyse_prepare_local


# --- Initialisation Cache (Optionnelle) ---
def initialize_text_cache():
    """Vérifie et pré-remplit le cache fichier pour les textes complets."""
    # Utilise les fonctions et config importées
    app_logger.info("\n--- Initialisation du Cache des Textes Complets ---")
    # Tenter de récupérer les définitions actuelles (potentiellement chargées depuis fichier)
    # Sinon, utiliser celles par défaut du module config
    # Note: Ceci suppose que configure_analysis_task a déjà été appelée au moins une fois
    # pour peupler local_current_extract_definitions. C'est une faiblesse potentielle
    # si on appelle initialize_text_cache *avant* configure_analysis_task.
    # Il serait plus robuste que load_extract_definitions retourne directement
    # les définitions utilisées.
    # Pour l'instant, on se base sur les définitions du module config comme fallback.
    definitions_to_check = ui_config.EXTRACT_SOURCES

    if (
        not definitions_to_check
        or definitions_to_check == ui_config.DEFAULT_EXTRACT_SOURCES
    ):
        app_logger.info(
            " -> Aucune définition de source valide à vérifier/initialiser."
        )
        return

    initialisation_errors = 0
    app_logger.info(
        f"Vérification du cache pour {len(definitions_to_check)} source(s)..."
    )
    for i, source_info in enumerate(definitions_to_check):
        source_name = source_info.get("source_name", f"Source #{i+1}")
        try:
            reconstructed_url = reconstruct_url(
                source_info.get("schema"),
                source_info.get("host_parts", []),
                source_info.get("path"),
            )
            if not reconstructed_url:
                app_logger.warning(f"   -> ⚠️ URL invalide pour '{source_name}'.")
                initialisation_errors += 1
                continue

            filepath = get_cache_filepath(reconstructed_url)
            if not filepath.exists():
                source_type = source_info.get("source_type")
                app_logger.info(
                    f"   -> Cache texte absent pour '{source_name}'. Récupération (type: {source_type})..."
                )
                try:
                    if source_type == "jina":
                        fetch_service.fetch_website_content(reconstructed_url)
                    elif source_type == "direct_download":
                        fetch_service.fetch_direct_text(reconstructed_url)
                    elif source_type == "tika":
                        # Le FetchService s'occupe de la logique interne, incluant le cache du fichier brut
                        fetch_service.fetch_document_content(
                            source_url=reconstructed_url
                        )
                    else:
                        app_logger.warning(
                            f"   -> ⚠️ Type source inconnu '{source_type}' lors de l'init cache."
                        )
                        initialisation_errors += 1
                except Exception as e_fetch:
                    app_logger.error(
                        f"   -> ❌ Erreur fetch pendant init cache pour '{source_name}': {e_fetch}"
                    )
                    initialisation_errors += 1

        except Exception as e_loop:
            app_logger.error(
                f"   -> ❌ Erreur traitement source '{source_name}' pendant init cache: {e_loop}"
            )
            initialisation_errors += 1

    app_logger.info("\n--- Fin Initialisation du Cache ---")
    if initialisation_errors > 0:
        app_logger.warning(
            f"⚠️ {initialisation_errors} erreur(s) rencontrée(s) pendant init cache."
        )
    else:
        app_logger.info("[OK] Cache initialisé/vérifié.")


# Log de chargement du module
module_logger = logging.getLogger(__name__)
module_logger.debug("Module ui.app chargé.")
