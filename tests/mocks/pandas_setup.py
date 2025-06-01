import sys
from unittest.mock import MagicMock
import pytest
import importlib # Ajouté pour pandas_mock si besoin d'import dynamique

# Tentative d'importation de pandas_mock.
try:
    import pandas_mock
except ImportError:
    print("ERREUR: pandas_setup.py: Impossible d'importer pandas_mock directement.")
    pandas_mock = MagicMock(name="pandas_mock_fallback_in_pandas_setup")
    pandas_mock.DataFrame = MagicMock(name="DataFrame_fallback")
    pandas_mock.Series = MagicMock(name="Series_fallback")
    pandas_mock.Index = MagicMock(name="Index_fallback")
    pandas_mock.MultiIndex = MagicMock(name="MultiIndex_fallback")
    pandas_mock.read_csv = MagicMock(name="read_csv_fallback")
    pandas_mock.read_excel = MagicMock(name="read_excel_fallback")
    pandas_mock.concat = MagicMock(name="concat_fallback")
    pandas_mock.to_datetime = MagicMock(name="to_datetime_fallback")
    pandas_mock.isna = MagicMock(name="isna_fallback")
    pandas_mock.isnull = MagicMock(name="isnull_fallback")
    pandas_mock.options = MagicMock()
    pandas_mock.options.display = MagicMock()
    pandas_mock.options.display.max_columns = None
    pandas_mock.options.display.max_rows = None
    pandas_mock.options.display.width = None
    pandas_mock.__version__ = '2.0.3.mock_fallback'


def is_module_available(module_name): # Copié depuis conftest.py, pourrait être dans un utilitaire partagé
    if module_name in sys.modules:
        if isinstance(sys.modules[module_name], MagicMock):
            return True # Si c'est déjà un mock, on considère "disponible" pour la logique de mock
    try:
        spec = importlib.util.find_spec(module_name)
        return spec is not None
    except (ImportError, ValueError):
        return False

def setup_pandas():
    # pandas_mock est importé en haut
    if (sys.version_info.major == 3 and sys.version_info.minor >= 12) or not is_module_available('pandas'):
        if not is_module_available('pandas'): print("Pandas non disponible, utilisation du mock (depuis pandas_setup.py).")
        else: print("Python 3.12+ détecté, utilisation du mock Pandas (depuis pandas_setup.py).")
        
        mock_pandas_attrs = {attr: getattr(pandas_mock, attr) for attr in dir(pandas_mock) if not attr.startswith('__')}
        mock_pandas_attrs['__version__'] = pandas_mock.__version__ if hasattr(pandas_mock, '__version__') else '2.0.3.mock'

        mock_pandas_module = type('pandas', (), mock_pandas_attrs)
        sys.modules['pandas'] = mock_pandas_module
        
        # S'assurer que les sous-modules/attributs importants sont là
        if hasattr(pandas_mock, 'DataFrame'):
            sys.modules['pandas'].DataFrame = pandas_mock.DataFrame
        if hasattr(pandas_mock, 'Series'):
            sys.modules['pandas'].Series = pandas_mock.Series
        if hasattr(pandas_mock, 'Index'):
            sys.modules['pandas'].Index = pandas_mock.Index
        # ... et ainsi de suite pour d'autres éléments clés si nécessaire

        print("INFO: pandas_setup.py: Mock Pandas configuré dynamiquement.")
        return sys.modules['pandas']
    else:
        import pandas
        print(f"Utilisation de la vraie bibliothèque Pandas (version {getattr(pandas, '__version__', 'inconnue')}) (depuis pandas_setup.py).")
        return pandas

# La fixture setup_pandas_for_tests_fixture n'est pas explicitement définie dans le conftest.py original
# pour pandas de la même manière que pour numpy. Si une fixture autouse est nécessaire pour pandas,
# elle devrait être ajoutée ici, similaire à setup_numpy_for_tests_fixture.
# Pour l'instant, on ne met que la fonction setup_pandas.

# Exemple de fixture si nécessaire :
# @pytest.fixture(scope="function", autouse=True)
# def setup_pandas_for_tests_fixture(request):
#     if request.node.get_closest_marker("real_jpype"): # ou un marqueur "real_pandas"
#         print(f"INFO: pandas_setup.py: Test {request.node.name} marqué pour réel, skip mock pandas.")
#         yield
#         return
#
#     original_pandas = sys.modules.get('pandas')
#     setup_pandas() # Appelle notre fonction de setup qui installe le mock
#
#     yield
#
#     if original_pandas:
#         sys.modules['pandas'] = original_pandas
#     elif 'pandas' in sys.modules and sys.modules['pandas'] is pandas_mock: # ou une vérification plus robuste
#         del sys.modules['pandas'] # Supprimer notre mock si rien n'était là avant