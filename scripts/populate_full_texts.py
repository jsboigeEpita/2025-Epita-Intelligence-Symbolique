import json
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Définition des chemins principaux
BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_DIR = BASE_DIR / "_temp"
INPUT_CONFIG_FILE = TEMP_DIR / "config_sources_localized.json"
OUTPUT_CONFIG_FILE = TEMP_DIR / "config_with_full_texts.json"
DOWNLOADED_TEXTS_DIR = TEMP_DIR / "downloaded_texts"

# Définition d'un MockFetchService pour simuler l'extraction Tika
class MockFetchService:
    @staticmethod
    def get_content_from_local_pdf(file_path_str: str) -> str:
        logging.info(f"[MockFetchService] Appel de get_content_from_local_pdf pour : {file_path_str}")
        # Simuler un contenu extrait basé sur le nom du fichier
        file_name = Path(file_path_str).name
        simulated_content = f"Contenu PDF simulé par MockFetchService pour {file_name}. Ce texte est généré automatiquement pour les tests."
        logging.info(f"[MockFetchService] Contenu simulé généré (longueur {len(simulated_content)}): '{simulated_content[:100]}...'")
        return simulated_content

# Tentative d'importation de FetchService (pourrait être dans un module services.fetch_service par exemple)
# Si l'import échoue, on le signale et on continue sans pour les PDF.
try:
    # Supposons que FetchService est dans project_core.services.fetch_service
    # Ajustez le chemin d'importation si nécessaire.
    # from project_core.services.fetch_service import FetchService
    # Pour cette tâche, nous allons simuler que FetchService n'est pas facilement disponible
    # et nous allons logguer un message pour les PDF.
    FetchService = None # Garder à None pour forcer l'utilisation du Mock
    if FetchService:
        logging.info("FetchService importé avec succès.")
    else:
        logging.warning("FetchService (réel) n'est pas disponible ou n'a pas été importé. MockFetchService sera utilisé pour les PDF.")
except ImportError:
    FetchService = None # Assurer que FetchService est None en cas d'échec d'import
    logging.warning("FetchService (réel) n'a pas pu être importé. MockFetchService sera utilisé pour les PDF.")

def read_text_file(file_path: Path) -> str | None:
    """Lit le contenu d'un fichier texte simple."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            logging.info(f"Fichier texte {file_path} lu avec succès, longueur: {len(content)} caractères.")
            return content
    except Exception as e:
        logging.error(f"Erreur lors de la lecture du fichier texte {file_path.resolve()}: {e}")
        return None

def extract_pdf_content(file_path: Path) -> str | None:
    """
    Tente d'extraire le contenu d'un fichier PDF.
    Utilise FetchService si disponible, sinon MockFetchService.
    """
    logging.info(f"Début de extract_pdf_content pour: {file_path.resolve()}")
    pdf_content = None
    service_used = ""

    if FetchService:
        service_used = "FetchService (réel)"
        logging.info(f"Utilisation de {service_used} pour {file_path.name}")
        try:
            # Ceci est le chemin pour le vrai FetchService, s'il était disponible et configuré
            # pdf_content = FetchService.get_content_from_local_pdf(str(file_path))
            logging.warning(f"L'intégration réelle de {service_used} pour {file_path.name} est à implémenter. Utilisation d'un placeholder.")
            pdf_content = f"Contenu PDF placeholder via {service_used} pour {file_path.name}"
        except Exception as e:
            logging.error(f"Erreur lors de l'extraction PDF de {file_path.name} avec {service_used}: {e}")
            pdf_content = None
    else:
        service_used = "MockFetchService"
        logging.info(f"FetchService (réel) non disponible. Utilisation de {service_used} pour {file_path.name}.")
        try:
            # Log de l'entrée pour MockFetchService
            logging.info(f"Appel de {service_used}.get_content_from_local_pdf avec l'entrée : '{file_path}'")
            pdf_content = MockFetchService.get_content_from_local_pdf(str(file_path))
            # Log de la sortie de MockFetchService
            if pdf_content:
                logging.info(f"Sortie de {service_used}.get_content_from_local_pdf (longueur {len(pdf_content)}): '{pdf_content[:100]}...'")
            else:
                logging.warning(f"{service_used}.get_content_from_local_pdf a retourné None pour {file_path.name}")
        except Exception as e:
            logging.error(f"Erreur lors de l'extraction PDF de {file_path.name} avec {service_used}: {e}")
            pdf_content = None
            
    if pdf_content is None:
        logging.warning(f"Aucun contenu n'a pu être extrait pour le PDF {file_path.name} en utilisant {service_used}.")
    
    return pdf_content

def populate_full_texts():
    """
    Charge la configuration, lit les fichiers locaux pour chaque source,
    et peuple le champ 'full_text'. Sauvegarde la configuration mise à jour.
    """
    if not INPUT_CONFIG_FILE.exists():
        logging.error(f"Le fichier de configuration d'entrée {INPUT_CONFIG_FILE} n'existe pas.")
        return

    logging.info(f"Chargement de la configuration depuis {INPUT_CONFIG_FILE}")
    with open(INPUT_CONFIG_FILE, 'r', encoding='utf-8') as f:
        sources_config = json.load(f)

    updated_sources = []

    for source in sources_config:
        source_id = source.get("id", "ID_INCONNU")
        original_path_str = source.get("path")

        if not original_path_str:
            logging.warning(f"La source {source_id} n'a pas de champ 'path'. Elle est ignorée.")
            source["full_text"] = "" # Assurer que le champ existe
            updated_sources.append(source)
            continue

        # Le champ 'path' dans config_sources_localized.json est déjà relatif au projet
        # et pointe vers _temp/downloaded_texts/ ou similaire.
        # Il faut s'assurer que ce chemin est correctement interprété.
        # Si le path est déjà absolu ou correctement relatif depuis la racine du projet:
        # local_file_path = BASE_DIR / original_path_str
        # Si le path est relatif à TEMP_DIR (ce qui semble être le cas d'après la description)
        # local_file_path = TEMP_DIR / original_path_str # Non, car original_path_str est déjà _temp/...
        
        # Le path dans config_sources_localized.json est de la forme "downloaded_texts/fichier.txt"
        # et ces fichiers sont situés dans TEMP_DIR (c'est-à-dire BASE_DIR / "_temp")
        # Donc, le chemin correct est TEMP_DIR / original_path_str
        local_file_path = TEMP_DIR / Path(original_path_str)

        logging.info(f"Traitement de la source {source_id} - Chemin calculé: {local_file_path.resolve()}")

        content = None
        if not local_file_path.exists():
            logging.error(f"Le fichier {local_file_path} pour la source {source_id} n'existe pas.")
            source["full_text"] = "" # Assurer que le champ existe
            updated_sources.append(source)
            continue

        # Déterminer si c'est un PDF
        # On se base sur l'extension .pdf ou sur le source_type original si disponible
        is_pdf = local_file_path.suffix.lower() == ".pdf"
        if "source_type" in source and source["source_type"] == "tika" and not is_pdf:
            # Si le source_type original était tika mais que l'extension n'est pas .pdf,
            # cela pourrait être une erreur dans la localisation ou un fichier renommé.
            # On va quand même essayer de le traiter comme PDF si tika était mentionné.
            logging.warning(f"Source {source_id} a source_type 'tika' mais le fichier {local_file_path.name} n'a pas d'extension .pdf. Tentative de traitement PDF.")
            is_pdf = True # Forcer le traitement PDF par précaution

        if is_pdf:
            logging.info(f"La source {source_id} (fichier {local_file_path.name}) est identifiée comme PDF. Tentative d'extraction de contenu.")
            content = extract_pdf_content(local_file_path)
            if content is not None:
                logging.info(f"Contenu PDF extrait pour {local_file_path.name} (source {source_id}), longueur: {len(content)}. Assignation à full_text.")
            else:
                logging.warning(f"Aucun contenu PDF n'a été extrait pour {local_file_path.name} (source {source_id}). full_text sera vide.")
        else:
            # Ajout des logs demandés pour les fichiers .txt et autres non-PDF
            resolved_path = local_file_path.resolve()
            exists = local_file_path.exists() # Devrait être vrai car vérifié avant
            logging.info(f"La source {source_id} (fichier {local_file_path.name}) est identifiée comme NON-PDF. Tentative de lecture du fichier texte simple: {resolved_path}")
            logging.info(f"Le fichier {resolved_path} existe-t-il ? {exists}")

            if exists: # Double vérification, mais bon pour la robustesse du log
                content = read_text_file(local_file_path)
                if content is not None: # Vérifier si la lecture a réussi (read_text_file retourne None en cas d'erreur)
                    logging.info(f"Contenu texte lu pour {resolved_path} (source {source_id}), longueur: {len(content)} caractères. Assignation à full_text.")
            else:
                # Ce cas ne devrait pas être atteint si la logique précédente est correcte
                logging.error(f"Le fichier {resolved_path} (source {source_id}) n'a pas été trouvé juste avant la lecture (incohérence).")
                content = None

        # Assignation finale à full_text
        if content is not None:
            source["full_text"] = content
            # Log spécifique pour la valeur assignée à source["full_text"] après traitement PDF/Texte
            logging.info(f"Valeur finale assignée à source['full_text'] pour {source_id} (fichier {local_file_path.name}): '{str(content)[:100]}...' (longueur: {len(content)})")
        else:
            source["full_text"] = "" # Laisser vide si échec ou si le contenu est None
            logging.error(f"Échec de lecture/extraction ou contenu vide pour {local_file_path.resolve()} (source {source_id}). full_text assigné à une chaîne vide.")
        
        updated_sources.append(source)

    logging.info(f"Sauvegarde de la configuration mise à jour dans {OUTPUT_CONFIG_FILE}")
    TEMP_DIR.mkdir(parents=True, exist_ok=True) # S'assurer que le répertoire _temp existe
    with open(OUTPUT_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(updated_sources, f, ensure_ascii=False, indent=2)

    logging.info("Script terminé.")

if __name__ == "__main__":
    populate_full_texts()