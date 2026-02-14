#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour vérifier que les dépendances sont correctement installées et fonctionnelles.

Ce script teste les dépendances problématiques (numpy, pandas, jpype) pour s'assurer
qu'elles sont correctement installées et fonctionnelles.
"""

import argumentation_analysis.core.environment

import sys
import os
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_dependencies")


def test_numpy():
    """
    Teste l'installation de numpy.

    Returns:
        True si numpy est correctement installé et fonctionnel, False sinon
    """
    try:
        logger.info("Test de numpy...")
        import numpy as np

        # Afficher la version
        logger.info(f"numpy version: {np.__version__}")

        # Tester quelques fonctionnalités de base
        arr = np.array([1, 2, 3, 4, 5])
        mean = np.mean(arr)
        sum_val = np.sum(arr)

        logger.info(f"numpy array: {arr}")
        logger.info(f"numpy mean: {mean}")
        logger.info(f"numpy sum: {sum_val}")

        logger.info("numpy est correctement installé et fonctionnel.")
        return True
    except ImportError as e:
        logger.error(f"Erreur d'importation de numpy: {e}")
        return False
    except Exception as e:
        logger.error(f"Erreur lors du test de numpy: {e}")
        return False


def test_pandas():
    """
    Teste l'installation de pandas.

    Returns:
        True si pandas est correctement installé et fonctionnel, False sinon
    """
    try:
        logger.info("Test de pandas...")
        import pandas as pd

        # Afficher la version
        logger.info(f"pandas version: {pd.__version__}")

        # Tester quelques fonctionnalités de base
        df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        mean = df.mean()
        sum_val = df.sum()

        logger.info(f"pandas DataFrame:\n{df}")
        logger.info(f"pandas mean:\n{mean}")
        logger.info(f"pandas sum:\n{sum_val}")

        logger.info("pandas est correctement installé et fonctionnel.")
        return True
    except ImportError as e:
        logger.error(f"Erreur d'importation de pandas: {e}")
        return False
    except Exception as e:
        logger.error(f"Erreur lors du test de pandas: {e}")
        return False


def test_jpype():
    """
    Teste l'installation de jpype.

    Returns:
        True si jpype est correctement installé et fonctionnel, False sinon
    """
    try:
        logger.info("Test de jpype...")
        import jpype

        # Afficher la version
        logger.info(f"jpype version: {jpype.__version__}")

        # Tester quelques fonctionnalités de base (sans initialiser la JVM)
        logger.info(f"jpype.isJVMStarted(): {jpype.isJVMStarted()}")
        logger.info(f"jpype.getDefaultJVMPath(): {jpype.getDefaultJVMPath()}")

        logger.info("jpype est correctement installé et fonctionnel.")
        return True
    except ImportError as e:
        logger.error(f"Erreur d'importation de jpype: {e}")
        return False
    except Exception as e:
        logger.error(f"Erreur lors du test de jpype: {e}")
        return False


def test_all_dependencies():
    """
    Teste toutes les dépendances.

    Returns:
        True si toutes les dépendances sont correctement installées et fonctionnelles, False sinon
    """
    numpy_ok = test_numpy()
    pandas_ok = test_pandas()
    jpype_ok = test_jpype()

    all_ok = numpy_ok and pandas_ok and jpype_ok

    if all_ok:
        logger.info(
            "Toutes les dépendances sont correctement installées et fonctionnelles."
        )
    else:
        logger.error(
            "Certaines dépendances ne sont pas correctement installées ou fonctionnelles."
        )

    return all_ok


if __name__ == "__main__":
    logger.info("Vérification des dépendances...")

    if test_all_dependencies():
        logger.info(
            "Toutes les dépendances sont correctement installées et fonctionnelles."
        )
        sys.exit(0)
    else:
        logger.error(
            "Certaines dépendances ne sont pas correctement installées ou fonctionnelles."
        )
        sys.exit(1)
