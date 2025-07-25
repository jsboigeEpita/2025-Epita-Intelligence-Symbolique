import pytest
import logging

logger = logging.getLogger(__name__)

# Ce test est conçu pour échouer en reproduisant le crash de la JVM.
@pytest.mark.jvm_test
@pytest.mark.xfail(reason="Cet ordre d'importation est connu pour causer un crash de la JVM.")
def test_import_jpype_first():
    """
    Tente d'importer jpype AVANT torch.
    Cet ordre est connu pour causer une "access violation" sur Windows.
    Le test est marqué comme xfail (échec attendu).
    """
    logger.info("Début du test avec import de jpype en premier.")
    try:
        import jpype
        import jpype.imports
        logger.info("jpype importé avec succès.")
        import torch
        logger.info("torch importé avec succès.")
    except Exception as e:
        logger.error(f"Une exception est survenue lors de l'importation : {e}", exc_info=True)
        pytest.fail(f"Le test a échoué de manière inattendue avec une exception : {e}")
    logger.info("Fin du test avec import de jpype en premier.")
    assert True

# Ce test est conçu pour réussir.
@pytest.mark.jvm_test
def test_import_torch_first():
    """
    Tente d'importer torch AVANT jpype.
    C'est l'ordre correct qui prévient le crash.
    """
    logger.info("Début du test avec import de torch en premier.")
    try:
        import torch
        logger.info("torch importé avec succès.")
        import jpype
        import jpype.imports
        logger.info("jpype importé avec succès.")
    except Exception as e:
        logger.error(f"Une exception est survenue lors de l'importation : {e}", exc_info=True)
        pytest.fail(f"Le test a échoué de manière inattendue avec une exception : {e}")
    logger.info("Fin du test avec import de torch en premier.")
    assert True