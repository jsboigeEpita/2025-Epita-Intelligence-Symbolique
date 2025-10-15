import pandas as pd
from typing import Dict, Any, Optional


class Taxonomy:
    """
    Classe pour charger et interroger la taxonomie des sophismes à partir d'un fichier CSV.
    """

    def __init__(self, file_path: str):
        """
        Initialise la taxonomie en chargeant le fichier CSV.

        Args:
            file_path (str): Le chemin vers le fichier CSV de la taxonomie.
        """
        self.df = pd.read_csv(file_path)
        # Normalise les noms de colonnes pour un accès simplifié (ex: "Fallacy Name" -> "fallacy_name")
        self.df.columns = [
            col.lower().replace(" ", "_").replace("-", "_") for col in self.df.columns
        ]

    def get_branch(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une branche (ligne) de la taxonomie par son ID (PK).

        Args:
            node_id (str): L'ID du nœud à récupérer.

        Returns:
            Optional[Dict[str, Any]]: Un dictionnaire représentant la ligne, ou None si non trouvé.
        """
        try:
            # La clé primaire dans le CSV est 'PK'
            row = self.df[self.df["pk"] == int(node_id)]
            if not row.empty:
                return row.to_dict("records")[0]
        except (ValueError, KeyError):
            # Ignore les erreurs si node_id n'est pas un entier valide ou si la colonne 'pk' n'existe pas
            pass
        return None

    def find_node_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Recherche un nœud par son nom de manière robuste (insensible à la casse, aux espaces et aux underscores).

        Args:
            name (str): Le nom du sophisme à rechercher.

        Returns:
            Optional[Dict[str, Any]]: Un dictionnaire représentant le nœud, ou None si non trouvé.
        """
        try:
            # Normalisation simple et robuste : minuscule et suppression des espaces avant/après
            search_name = name.lower().strip()

            # Appliquer la même normalisation à la colonne du dataframe
            row = self.df[self.df["name"].str.lower().str.strip() == search_name]
            if not row.empty:
                return row.to_dict("records")[0]
        except KeyError:
            # La colonne 'name' n'existe peut-être pas
            pass
        return None

    def count(self) -> int:
        """
        Retourne le nombre total d'entrées dans la taxonomie.

        Returns:
            int: Le nombre de lignes dans le DataFrame.
        """
        return len(self.df)
