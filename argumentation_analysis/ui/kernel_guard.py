"""Garde de noyau Jupyter pour les interfaces ipywidgets (#2787).

``configure_analysis_task`` attend les clics de ses widgets via
``jupyter_ui_poll.ui_events``, qui lit le noyau du shell IPython courant. Hors
d'un noyau, ``get_ipython()`` rend ``None`` et l'attente mourait sur
``'NoneType' object has no attribute 'kernel'``, après avoir chargé les
définitions et construit toute l'interface. La garde refuse avant tout travail,
avec un message qui nomme l'exigence.

Module léger à dessein : ``run_orchestration --ui`` l'appelle avant
d'initialiser l'environnement, sans importer ``ui.app`` ni ``ipywidgets``.
"""


def require_jupyter_kernel(feature: str) -> None:
    """Lève ``RuntimeError`` si aucun noyau Jupyter ne fait tourner ce processus.

    Args:
        feature: ce qui exige le noyau, repris dans le message d'erreur.
    """
    try:
        from IPython import get_ipython
    except ImportError:
        shell = None
    else:
        shell = get_ipython()
    if getattr(shell, "kernel", None) is None:
        raise RuntimeError(
            f"{feature} exige un noyau Jupyter : ses widgets attendent les clics "
            "via jupyter_ui_poll, qui n'existe que dans un notebook. Lancez-le "
            "depuis un notebook, ou passez le texte par --file/--text."
        )
