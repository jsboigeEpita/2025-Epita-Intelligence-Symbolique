"""
Ce module fournit des utilitaires pour configurer le logging de l'application.

Il permet d'initialiser le système de logging avec un niveau et un format
standards, et de contrôler la verbosité des bibliothèques tierces.
"""
import logging
import sys

def setup_logging(log_level_str: str = "INFO") -> None:
    """
    Initialise et configure le module logging de Python.

    Cette fonction configure un formateur standard pour les messages de log,
    ajoute un StreamHandler pour afficher les logs dans la console (sys.stdout),
    et définit le niveau de log global basé sur le paramètre log_level_str.
    Elle permet également de réduire la verbosité de certaines bibliothèques
    tierces courantes.

    :param log_level_str: Le niveau de log souhaité.
                          Les valeurs possibles sont "DEBUG", "INFO", "WARNING",
                          "ERROR", "CRITICAL".
    :type log_level_str: str
    :default log_level_str: "INFO"
    :return: None
    :rtype: None
    """
    # Convertir la chaîne de caractères du niveau de log en sa valeur numérique.
    # `getattr` est utilisé pour obtenir l'attribut de `logging` correspondant au nom du niveau.
    # Par exemple, si log_level_str est "INFO", `getattr(logging, "INFO")` retourne `logging.INFO`.
    numeric_level = getattr(logging, log_level_str.upper(), None)
    if not isinstance(numeric_level, int):
        # Si le niveau de log fourni n'est pas valide (ex: "INFOS" au lieu de "INFO"),
        # un avertissement est émis et le niveau INFO est utilisé par défaut.
        logging.warning(f"Niveau de log invalide: {log_level_str}. Utilisation du niveau INFO par défaut.")
        numeric_level = logging.INFO

    # La suppression manuelle des handlers existants n'est plus nécessaire
    # si `force=True` est utilisé dans `basicConfig`.
    # root_logger = logging.getLogger()
    # if root_logger.hasHandlers():
    #     for handler in root_logger.handlers[:]: # Itérer sur une copie de la liste des handlers
    #         root_logger.removeHandler(handler)
            
    # Configuration de base du logging.
    # - `level`: Définit le seuil de criticité pour les messages qui seront traités.
    # - `format`: Spécifie le format des messages de log.
    # - `datefmt`: Définit le format de la date/heure dans les messages de log.
    # - `handlers`: Liste des handlers à ajouter au logger racine. Ici, un StreamHandler
    #   est utilisé pour envoyer les logs vers la sortie standard (console).
    # - `force=True` (depuis Python 3.8): Supprime et ferme tous les handlers existants
    #   attachés au logger racine avant d'effectuer la configuration.
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)], # Dirige les logs vers stdout
        force=True # Assure que les handlers existants sont retirés et la config appliquée.
    )
    
    # Réduction de la verbosité de certaines bibliothèques tierces.
    # Ces bibliothèques peuvent générer un grand nombre de logs aux niveaux INFO ou DEBUG,
    # ce qui peut polluer la sortie. Leur niveau est donc fixé à WARNING.
    libraries_to_quiet = ["httpx", "openai", "requests", "urllib3", "semantic_kernel.connectors.ai"]
    for lib_name in libraries_to_quiet:
        logging.getLogger(lib_name).setLevel(logging.WARNING)
    
    # Configuration des loggers spécifiques au projet.
    # Par défaut, les loggers enfants héritent du niveau de leur parent (le logger racine ici).
    # Si `numeric_level` est DEBUG, ces loggers seront aussi à DEBUG.
    # Si `numeric_level` est INFO, ils seront à INFO, etc.
    # Aucune action spécifique n'est nécessaire ici si l'on souhaite qu'ils héritent
    # simplement du niveau configuré via `basicConfig`.
    # Si un comportement différent était souhaité (par exemple, forcer "Orchestration"
    # à être toujours en DEBUG), on le configurerait ici.
    project_specific_loggers = ["Orchestration", "semantic_kernel.agents"]
    for logger_name in project_specific_loggers:
        logging.getLogger(logger_name).setLevel(numeric_level)

    logging.info(f"Logging configuré avec le niveau {log_level_str.upper()}.")