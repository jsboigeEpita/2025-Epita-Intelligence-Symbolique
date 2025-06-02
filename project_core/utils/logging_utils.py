import logging
import sys

def setup_logging(log_level_str: str = "INFO"):
    """
    Initialise et configure le module logging de Python.

    Cette fonction configure un formateur standard pour les messages de log,
    ajoute un StreamHandler pour afficher les logs dans la console (sys.stdout),
    et définit le niveau de log global basé sur le paramètre log_level_str.
    Elle permet également de réduire la verbosité de certaines bibliothèques
    tierces courantes.

    Args:
        log_level_str (str, optional): Le niveau de log souhaité sous forme de chaîne de caractères.
                                       Par défaut "INFO". Les valeurs possibles sont "DEBUG",
                                       "INFO", "WARNING", "ERROR", "CRITICAL".
    """
    # Convertir la chaîne de caractères du niveau de log en sa valeur numérique correspondante
    numeric_level = getattr(logging, log_level_str.upper(), None)
    if not isinstance(numeric_level, int):
        logging.warning(f"Niveau de log invalide: {log_level_str}. Utilisation du niveau INFO par défaut.")
        numeric_level = logging.INFO

    # Supprimer les handlers existants pour éviter la duplication si la fonction est appelée plusieurs fois
    # Ceci est particulièrement utile dans les environnements de notebook ou de tests.
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)] # Utilisation explicite de sys.stdout
    )
    
    # Réduire la verbosité de certaines bibliothèques spécifiques
    # Ces bibliothèques peuvent être très verbeuses au niveau INFO ou DEBUG
    libraries_to_quiet = ["httpx", "openai", "requests", "urllib3", "semantic_kernel.connectors.ai"]
    for lib_name in libraries_to_quiet:
        logging.getLogger(lib_name).setLevel(logging.WARNING)
    
    # S'assurer que les loggers spécifiques au projet respectent au moins le niveau INFO,
    # sauf si le niveau global est plus restrictif (ex: WARNING).
    # Ou, si le niveau global est plus permissif (ex: DEBUG), ils utiliseront ce niveau.
    project_specific_loggers = ["Orchestration", "semantic_kernel.agents"]
    for logger_name in project_specific_loggers:
        # Le niveau effectif sera le plus permissif entre le niveau du logger et le niveau racine.
        # Cependant, nous voulons souvent que nos loggers principaux soient au moins à INFO.
        # Si numeric_level est DEBUG, ils seront DEBUG. Si numeric_level est WARNING, ils seront WARNING.
        # Si numeric_level est INFO, ils seront INFO.
        # La logique de basicConfig a déjà défini le niveau du root logger.
        # Les loggers enfants hériteront de ce niveau sauf si un niveau spécifique est défini ici.
        # Pour s'assurer qu'ils ne sont pas moins verbeux que le root logger,
        # on peut simplement les laisser hériter ou définir leur niveau explicitement si nécessaire.
        # Dans ce cas, on les laisse hériter du niveau `numeric_level` défini par `basicConfig`.
        pass # Ils hériteront du niveau `numeric_level`

    logging.info(f"Logging configuré avec le niveau {log_level_str.upper()}.")