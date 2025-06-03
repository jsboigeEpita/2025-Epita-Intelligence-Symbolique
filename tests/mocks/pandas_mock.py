"""
Mock pour le module pandas.

Ce module fournit des implémentations factices des fonctionnalités de pandas
qui sont utilisées dans le projet, permettant d'exécuter les tests sans avoir besoin
de pandas.
"""

import sys
from unittest.mock import MagicMock
import csv
import json
from collections import defaultdict

# Options globales pour get_option et set_option
_pandas_mock_options = {
    'display.max_columns': None,
    'display.width': None,
    'display.max_rows': None,
}

def get_option(key):
    """Mock pour pandas.get_option."""
    return _pandas_mock_options.get(key)

def set_option(key, value):
    """Mock pour pandas.set_option."""
    _pandas_mock_options[key] = value

# Mock pour pandas.io.formats.console
class MockPandasIOFormatsConsole:
    """Mock pour pandas.io.formats.console."""
    def get_console_size(self):
        """Retourne une taille de console par défaut."""
        # Utilise les options globales si disponibles, sinon des valeurs par défaut.
        width = get_option('display.width') or 80
        height = get_option('display.max_rows') or 24 # Ou une autre option pertinente pour la hauteur
        return (width, height)

# Mock pour pandas.io.formats
class MockPandasIOFormats:
    """Mock pour pandas.io.formats."""
    def __init__(self):
        self.console = MockPandasIOFormatsConsole()

# Mock pour pandas.io
class MockPandasIO:
    """Mock pour pandas.io."""
    def __init__(self):
        self.formats = MockPandasIOFormats()

# Mock pour pandas.DataFrame
class DataFrame:
    """Mock pour pandas.DataFrame."""
    
    def __init__(self, data=None, columns=None, index=None):
        """
        Initialise un DataFrame mock.
        
        Args:
            data: Données du DataFrame (liste de dictionnaires, dictionnaire de listes, etc.)
            columns: Noms des colonnes
            index: Index des lignes
        """
        self.columns = columns or []
        self._data = {}
        
        if data is None:
            data = {}
        
        # Convertir les données en dictionnaire de colonnes
        if isinstance(data, list):
            # Liste de dictionnaires
            if data and isinstance(data[0], dict):
                for d in data:
                    for k, v in d.items():
                        if k not in self._data:
                            self._data[k] = []
                        self._data[k].append(v)
                if not self.columns:
                    self.columns = list(self._data.keys())
            # Liste de listes
            elif data and isinstance(data[0], (list, tuple)):
                if not self.columns:
                    self.columns = [f"col_{i}" for i in range(len(data[0]))]
                for i, col in enumerate(self.columns):
                    self._data[col] = [row[i] for row in data]
        elif isinstance(data, dict):
            self._data = {k: list(v) for k, v in data.items()}
            if not self.columns:
                self.columns = list(self._data.keys())
        
        self.index = index or list(range(len(self._data[self.columns[0]]) if self.columns and self._data else 0))
        self.shape = (len(self.index), len(self.columns))
    
    def __len__(self):
        """Retourne le nombre de lignes du DataFrame."""
        return len(self.index)
    
    def __getitem__(self, key):
        """Accès aux colonnes ou lignes du DataFrame."""
        if isinstance(key, str):
            # Accès à une colonne
            return self._data.get(key, [])
        elif isinstance(key, list):
            # Accès à plusieurs colonnes
            return DataFrame({k: self._data.get(k, []) for k in key}, columns=key, index=self.index)
        elif isinstance(key, tuple):
            # Accès à une cellule spécifique
            row, col = key
            if isinstance(col, str):
                return self._data.get(col, [])[row]
            else:
                return [self._data.get(c, [])[row] for c in col]
        return None
    
    def __setitem__(self, key, value):
        """Définit une colonne du DataFrame."""
        if isinstance(key, str):
            if key not in self.columns:
                self.columns.append(key)
            self._data[key] = value
            self.shape = (len(self.index), len(self.columns))
    
    def head(self, n=5):
        """Retourne les n premières lignes du DataFrame."""
        return DataFrame(
            {k: v[:n] for k, v in self._data.items()},
            columns=self.columns,
            index=self.index[:n]
        )
    
    def tail(self, n=5):
        """Retourne les n dernières lignes du DataFrame."""
        return DataFrame(
            {k: v[-n:] for k, v in self._data.items()},
            columns=self.columns,
            index=self.index[-n:]
        )
    
    def to_dict(self, orient='records'):
        """Convertit le DataFrame en dictionnaire."""
        if orient == 'records':
            return [{col: self._data[col][i] for col in self.columns} for i in range(len(self.index))]
        elif orient == 'list':
            return {k: v for k, v in self._data.items()}
        elif orient == 'dict':
            return {i: {col: self._data[col][idx] for col in self.columns} for idx, i in enumerate(self.index)}
        return self._data
    
    def to_csv(self, path_or_buf=None, index=True, **kwargs):
        """Écrit le DataFrame dans un fichier CSV."""
        if path_or_buf is None:
            return ""
        
        with open(path_or_buf, 'w', newline='') as f:
            writer = csv.writer(f)
            # Écrire l'en-tête
            header = self.columns
            if index:
                header = [''] + header
            writer.writerow(header)
            
            # Écrire les données
            for i, idx in enumerate(self.index):
                row = [self._data[col][i] for col in self.columns]
                if index:
                    row = [idx] + row
                writer.writerow(row)
    
    def to_json(self, path_or_buf=None, orient='records', **kwargs):
        """Convertit le DataFrame en JSON."""
        data = self.to_dict(orient=orient)
        if path_or_buf is None:
            return json.dumps(data)
        
        with open(path_or_buf, 'w') as f:
            json.dump(data, f)
    
    def groupby(self, by):
        """Groupe le DataFrame par une ou plusieurs colonnes."""
        result = defaultdict(list)
        for i in range(len(self.index)):
            key = self._data[by][i] if isinstance(by, str) else tuple(self._data[col][i] for col in by)
            for col in self.columns:
                if col not in result:
                    result[col] = defaultdict(list)
                result[col][key].append(self._data[col][i])
        
        # Créer un objet GroupBy mock
        return GroupBy(result, by)
    
    def set_index(self, keys, inplace=False, drop=True):
        """Définit l'index du DataFrame."""
        if isinstance(keys, str):
            keys = [keys]
        
        # Créer un nouvel index basé sur les colonnes spécifiées
        new_index = []
        for i in range(len(self.index)):
            if len(keys) == 1:
                new_index.append(self._data[keys[0]][i])
            else:
                new_index.append(tuple(self._data[k][i] for k in keys))
        
        if inplace:
            self.index = new_index
            
            # Supprimer les colonnes utilisées comme index si drop=True
            if drop:
                for key in keys:
                    if key in self.columns:
                        self.columns.remove(key)
                        del self._data[key]
            return None
        else:
            # Créer un nouveau DataFrame avec le nouvel index
            new_df = DataFrame(self._data, columns=self.columns, index=new_index)
            
            # Supprimer les colonnes utilisées comme index si drop=True
            if drop:
                for key in keys:
                    if key in new_df.columns:
                        new_df.columns.remove(key)
                        del new_df._data[key]
            
            return new_df
    
    def reset_index(self, drop=False):
        """Réinitialise l'index du DataFrame."""
        new_df = DataFrame(self._data, columns=self.columns)
        if not drop:
            new_df['index'] = self.index
        return new_df
    
    def copy(self):
        """Crée une copie du DataFrame."""
        return DataFrame(self._data.copy(), columns=self.columns.copy(), index=self.index.copy())
    
    def fillna(self, value=None, method=None, inplace=False):
        """Remplace les valeurs NaN."""
        if inplace:
            for col in self.columns:
                self._data[col] = [value if x is None else x for x in self._data[col]]
            return None
        else:
            new_data = {}
            for col in self.columns:
                new_data[col] = [value if x is None else x for x in self._data[col]]
            return DataFrame(new_data, columns=self.columns, index=self.index)


class GroupBy:
    """Mock pour pandas.core.groupby.GroupBy."""
    
    def __init__(self, data, by):
        self.data = data
        self.by = by
    
    def mean(self):
        """Calcule la moyenne pour chaque groupe."""
        result = {}
        for col, groups in self.data.items():
            result[col] = {k: sum(v) / len(v) if v else 0 for k, v in groups.items()}
        
        # Convertir en DataFrame
        index = list(next(iter(self.data.values())).keys())
        columns = list(self.data.keys())
        data = {col: [result[col][idx] for idx in index] for col in columns}
        return DataFrame(data, columns=columns, index=index)
    
    def sum(self):
        """Calcule la somme pour chaque groupe."""
        result = {}
        for col, groups in self.data.items():
            result[col] = {k: sum(v) for k, v in groups.items()}
        
        # Convertir en DataFrame
        index = list(next(iter(self.data.values())).keys())
        columns = list(self.data.keys())
        data = {col: [result[col][idx] for idx in index] for col in columns}
        return DataFrame(data, columns=columns, index=index)
    
    def count(self):
        """Compte le nombre d'éléments pour chaque groupe."""
        result = {}
        for col, groups in self.data.items():
            result[col] = {k: len(v) for k, v in groups.items()}
        
        # Convertir en DataFrame
        index = list(next(iter(self.data.values())).keys())
        columns = list(self.data.keys())
        data = {col: [result[col][idx] for idx in index] for col in columns}
        return DataFrame(data, columns=columns, index=index)


# Fonctions pour lire des fichiers CSV et JSON
def read_csv(filepath_or_buffer, **kwargs):
    """Mock pour pandas.read_csv."""
    try:
        with open(filepath_or_buffer, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            data = {col: [] for col in header}
            for row in reader:
                for i, col in enumerate(header):
                    data[col].append(row[i] if i < len(row) else None)
        return DataFrame(data)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return DataFrame()


def read_json(path_or_buf, **kwargs):
    """Mock pour pandas.read_json."""
    try:
        if isinstance(path_or_buf, str):
            with open(path_or_buf, 'r') as f:
                data = json.load(f)
        else:
            data = json.load(path_or_buf)
        
        if isinstance(data, list):
            # Liste de dictionnaires
            return DataFrame(data)
        elif isinstance(data, dict):
            # Dictionnaire de listes
            return DataFrame(data)
        return DataFrame()
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return DataFrame()


# Créer un mock avec __spec__ pour la compatibilité avec transformers
class PandasMock:
    """Mock pour le module pandas avec __spec__."""
    def __init__(self):
        self.DataFrame = DataFrame
        self.read_csv = read_csv
        self.read_json = read_json
        self.Series = list
        self.NA = None
        self.NaT = None
        self.isna = lambda x: x is None
        self.notna = lambda x: x is not None
        # Assigner les fonctions globales aux attributs d'instance
        self.get_option = get_option
        self.set_option = set_option
        # Ajouter __spec__ pour la compatibilité avec transformers
        self.__spec__ = type('ModuleSpec', (), {
            'name': 'pandas',
            'origin': 'mock',
            'submodule_search_locations': None
        })()

# # Installer le mock dans sys.modules pour qu'il soit utilisé lors des importations
# # Commenté pour éviter l'auto-installation. L'installation doit être gérée par conftest.py
# _pandas_module_instance = PandasMock()
# sys.modules['pandas'] = _pandas_module_instance
# 
# # Installer les mocks pour les sous-modules io
# # Commenté également
# # sys.modules['pandas.io'] = MockPandasIO()
# # sys.modules['pandas.io.formats'] = sys.modules['pandas.io'].formats # Réutiliser l'instance
# # sys.modules['pandas.io.formats.console'] = sys.modules['pandas.io'].formats.console # Réutiliser l'instance
# 
# 
# # Assurer que get_option et set_option sont aussi accessibles comme attributs du module mocké
# # pour les imports directs comme `from pandas import get_option`
# # Commenté également
# # setattr(sys.modules['pandas'], 'get_option', get_option)
# # setattr(sys.modules['pandas'], 'set_option', set_option)