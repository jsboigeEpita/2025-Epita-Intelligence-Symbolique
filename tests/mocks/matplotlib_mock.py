"""
Mock pour la bibliothèque matplotlib.
"""
from unittest.mock import MagicMock

# Mock pour matplotlib.pyplot
pyplot = MagicMock()
pyplot.figure = MagicMock()
pyplot.show = MagicMock()
pyplot.savefig = MagicMock()
pyplot.title = MagicMock()
pyplot.xlabel = MagicMock()
pyplot.ylabel = MagicMock()
pyplot.plot = MagicMock()
pyplot.scatter = MagicMock()
pyplot.bar = MagicMock()
pyplot.hist = MagicMock()
pyplot.legend = MagicMock()
pyplot.gca = MagicMock(return_value=MagicMock())
pyplot.subplots = MagicMock(return_value=(MagicMock(), MagicMock()))

# Mock pour matplotlib.cm
cm = MagicMock()
cm.get_cmap = MagicMock()
cm.ScalarMappable = MagicMock()


# Mock pour matplotlib lui-même
class MatplotlibMock(MagicMock):
    pyplot = pyplot
    cm = cm  # Ajouter le mock de cm ici
    __path__ = []  # Pour le faire passer pour un package si nécessaire


# Ce qui est généralement importé est pyplot et parfois cm
# Le conftest.py s'occupera de mettre cela dans sys.modules
