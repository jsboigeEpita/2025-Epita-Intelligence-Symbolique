#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mock pour matplotlib pour les tests.
Ce mock permet d'exécuter les tests sans avoir besoin d'installer matplotlib.
"""

import logging
from typing import Any, Dict, List, Optional, Union, Callable, Tuple

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("MatplotlibMock")

# Version
__version__ = "3.7.1"

# Classes de base
class Figure:
    """Mock pour matplotlib.figure.Figure."""
    
    def __init__(self, figsize=None, dpi=None, **kwargs):
        self.figsize = figsize
        self.dpi = dpi
        self.axes_list = []
    
    def add_subplot(self, *args, **kwargs):
        """Ajoute un subplot à la figure."""
        ax = Axes()
        self.axes_list.append(ax)
        return ax
    
    def savefig(self, fname, **kwargs):
        """Sauvegarde la figure."""
        logger.info(f"Sauvegarde de la figure dans {fname}")
    
    def clf(self):
        """Efface la figure."""
        self.axes_list = []
    
    def close(self):
        """Ferme la figure."""
        pass

class Axes:
    """Mock pour matplotlib.axes.Axes."""
    
    def __init__(self):
        self.lines = []
        self.patches = []
        self.texts = []
        self.title = None
        self.xlabel = None
        self.ylabel = None
        self.xlim = (0, 1)
        self.ylim = (0, 1)
    
    def plot(self, *args, **kwargs):
        """Trace une ligne."""
        line = Line2D()
        self.lines.append(line)
        return [line]
    
    def scatter(self, x, y, **kwargs):
        """Trace un nuage de points."""
        scatter = Line2D()
        self.lines.append(scatter)
        return scatter
    
    def bar(self, x, height, **kwargs):
        """Trace un diagramme à barres."""
        bars = []
        for i in range(len(x) if hasattr(x, '__len__') else 1):
            bar = Rectangle()
            self.patches.append(bar)
            bars.append(bar)
        return bars
    
    def hist(self, x, **kwargs):
        """Trace un histogramme."""
        n, bins, patches = [], [], []
        for i in range(10):  # 10 bins par défaut
            patch = Rectangle()
            self.patches.append(patch)
            patches.append(patch)
        return n, bins, patches
    
    def set_title(self, title, **kwargs):
        """Définit le titre."""
        self.title = title
    
    def set_xlabel(self, xlabel, **kwargs):
        """Définit le label de l'axe x."""
        self.xlabel = xlabel
    
    def set_ylabel(self, ylabel, **kwargs):
        """Définit le label de l'axe y."""
        self.ylabel = ylabel
    
    def set_xlim(self, left=None, right=None, **kwargs):
        """Définit les limites de l'axe x."""
        if left is not None and right is not None:
            self.xlim = (left, right)
        elif left is not None and isinstance(left, (list, tuple)):
            self.xlim = tuple(left)
    
    def set_ylim(self, bottom=None, top=None, **kwargs):
        """Définit les limites de l'axe y."""
        if bottom is not None and top is not None:
            self.ylim = (bottom, top)
        elif bottom is not None and isinstance(bottom, (list, tuple)):
            self.ylim = tuple(bottom)
    
    def legend(self, *args, **kwargs):
        """Ajoute une légende."""
        return Legend()
    
    def grid(self, b=None, **kwargs):
        """Active ou désactive la grille."""
        pass
    
    def text(self, x, y, s, **kwargs):
        """Ajoute du texte."""
        text = Text(x, y, s)
        self.texts.append(text)
        return text

class Line2D:
    """Mock pour matplotlib.lines.Line2D."""
    
    def __init__(self, xdata=None, ydata=None, **kwargs):
        self.xdata = xdata
        self.ydata = ydata
        self.marker = None
        self.linestyle = '-'
        self.color = 'b'
        self.label = None
    
    def set_data(self, xdata, ydata):
        """Définit les données."""
        self.xdata = xdata
        self.ydata = ydata

class Rectangle:
    """Mock pour matplotlib.patches.Rectangle."""
    
    def __init__(self, xy=(0, 0), width=1, height=1, **kwargs):
        self.xy = xy
        self.width = width
        self.height = height
        self.color = 'b'

class Text:
    """Mock pour matplotlib.text.Text."""
    
    def __init__(self, x=0, y=0, text='', **kwargs):
        self.x = x
        self.y = y
        self.text = text

class Legend:
    """Mock pour matplotlib.legend.Legend."""
    
    def __init__(self, *args, **kwargs):
        pass

# Sous-modules
class pyplot:
    """Mock pour matplotlib.pyplot."""
    
    @staticmethod
    def figure(figsize=None, dpi=None, **kwargs):
        """Crée une nouvelle figure."""
        return Figure(figsize=figsize, dpi=dpi, **kwargs)
    
    @staticmethod
    def subplot(*args, **kwargs):
        """Crée un subplot."""
        return Axes()
    
    @staticmethod
    def plot(*args, **kwargs):
        """Trace une ligne."""
        ax = pyplot.gca()
        return ax.plot(*args, **kwargs)
    
    @staticmethod
    def scatter(x, y, **kwargs):
        """Trace un nuage de points."""
        ax = pyplot.gca()
        return ax.scatter(x, y, **kwargs)
    
    @staticmethod
    def bar(x, height, **kwargs):
        """Trace un diagramme à barres."""
        ax = pyplot.gca()
        return ax.bar(x, height, **kwargs)
    
    @staticmethod
    def hist(x, **kwargs):
        """Trace un histogramme."""
        ax = pyplot.gca()
        return ax.hist(x, **kwargs)
    
    @staticmethod
    def title(s, **kwargs):
        """Définit le titre."""
        ax = pyplot.gca()
        return ax.set_title(s, **kwargs)
    
    @staticmethod
    def xlabel(s, **kwargs):
        """Définit le label de l'axe x."""
        ax = pyplot.gca()
        return ax.set_xlabel(s, **kwargs)
    
    @staticmethod
    def ylabel(s, **kwargs):
        """Définit le label de l'axe y."""
        ax = pyplot.gca()
        return ax.set_ylabel(s, **kwargs)
    
    @staticmethod
    def xlim(*args, **kwargs):
        """Définit les limites de l'axe x."""
        ax = pyplot.gca()
        return ax.set_xlim(*args, **kwargs)
    
    @staticmethod
    def ylim(*args, **kwargs):
        """Définit les limites de l'axe y."""
        ax = pyplot.gca()
        return ax.set_ylim(*args, **kwargs)
    
    @staticmethod
    def legend(*args, **kwargs):
        """Ajoute une légende."""
        ax = pyplot.gca()
        return ax.legend(*args, **kwargs)
    
    @staticmethod
    def grid(b=None, **kwargs):
        """Active ou désactive la grille."""
        ax = pyplot.gca()
        return ax.grid(b, **kwargs)
    
    @staticmethod
    def savefig(fname, **kwargs):
        """Sauvegarde la figure."""
        fig = pyplot.gcf()
        return fig.savefig(fname, **kwargs)
    
    @staticmethod
    def clf():
        """Efface la figure."""
        fig = pyplot.gcf()
        return fig.clf()
    
    @staticmethod
    def close(fig=None):
        """Ferme la figure."""
        if fig is None:
            fig = pyplot.gcf()
        return fig.close()
    
    @staticmethod
    def gca():
        """Retourne les axes courants."""
        fig = pyplot.gcf()
        if not fig.axes_list:
            ax = Axes()
            fig.axes_list.append(ax)
            return ax
        return fig.axes_list[-1]
    
    @staticmethod
    def gcf():
        """Retourne la figure courante."""
        if not hasattr(pyplot, "_current_figure") or pyplot._current_figure is None:
            pyplot._current_figure = Figure()
        return pyplot._current_figure
    
    @staticmethod
    def show():
        """Affiche la figure."""
        logger.info("Affichage de la figure (simulé)")

# Initialisation
pyplot._current_figure = None

# Log de chargement
logger.info("Module matplotlib_mock chargé")