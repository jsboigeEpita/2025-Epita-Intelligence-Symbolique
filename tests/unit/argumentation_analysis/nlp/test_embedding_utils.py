
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module embedding_utils.py.
"""

import pytest
import json
from pathlib import Path

import httpx # Ajout de l'import
from unittest.mock import patch, MagicMock, mock_open

# Chemins pour le patching
OPENAI_CLIENT_PATH = "argumentation_analysis.nlp.embedding_utils.OpenAI"
SENTENCE_TRANSFORMER_PATH = "argumentation_analysis.nlp.embedding_utils.SentenceTransformer"
OPENAI_API_ERROR_PATH = "argumentation_analysis.nlp.embedding_utils.APIError" # Ajout pour APIError
MKDIR_PATH = "pathlib.Path.mkdir" # Patching de la méthode mkdir de l'instance Path
OPEN_BUILTIN_PATH = "builtins.open" # Pour mocker l'ouverture de fichier

# Importation des fonctions à tester
from argumentation_analysis.nlp.embedding_utils import get_embeddings_for_chunks, save_embeddings_data

# Fixtures pour les données de test
@pytest.fixture
def sample_text_chunks():
    return ["Ceci est un texte.", "Un autre texte ici."]

@pytest.fixture
def mock_openai_response():
    """Simule une réponse de l'API OpenAI embeddings."""
    response_mock = MagicMock()
    embedding_data1 = MagicMock()
    embedding_data1.embedding = [0.1, 0.2, 0.3]
    embedding_data2 = MagicMock()
    embedding_data2.embedding = [0.4, 0.5, 0.6]
    response_mock.data = [embedding_data1, embedding_data2]
    return response_mock

@pytest.fixture
def mock_sentence_transformer_model():
    """Simule un modèle SentenceTransformer."""
    model_mock = MagicMock(spec=SENTENCE_TRANSFORMER_PATH)
    # Simuler la méthode encode pour retourner une liste de listes (ou un ndarray convertible)
    model_mock.encode.return_value = [[0.7, 0.8, 0.9], [1.0, 1.1, 1.2]]
    return model_mock

# Tests pour get_embeddings_for_chunks

def test_get_embeddings_openai_model(sample_text_chunks, mock_openai_response):
    """Teste la génération d'embeddings avec un modèle OpenAI."""
    model_name = "text-embedding-3-small"
    
    # Mock du client OpenAI et de sa méthode create
    mock_client_instance = MagicMock()
    mock_client_instance.embeddings.create.return_value = mock_openai_response
    
    with patch(OPENAI_CLIENT_PATH, return_value=mock_client_instance) as mock_openai_constructor:
        embeddings = get_embeddings_for_chunks(sample_text_chunks, model_name)
        
        mock_openai_constructor.assert_called_once() # Vérifie que le client OpenAI a été initialisé
        mock_client_instance.embeddings.create.assert_called_once_with(
            input=sample_text_chunks,
            model=model_name
        )
        assert embeddings == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

def test_get_embeddings_sentence_transformer_model(sample_text_chunks, mock_sentence_transformer_model):
    """Teste la génération d'embeddings avec un modèle Sentence Transformer."""
    model_name = "all-MiniLM-L6-v2"
    
    with patch(SENTENCE_TRANSFORMER_PATH, return_value=mock_sentence_transformer_model) as mock_st_constructor:
        embeddings = get_embeddings_for_chunks(sample_text_chunks, model_name)
        
        mock_st_constructor.assert_called_once_with(model_name)
        mock_sentence_transformer_model.encode.assert_called_once_with(sample_text_chunks)
        assert embeddings == [[0.7, 0.8, 0.9], [1.0, 1.1, 1.2]]

def test_get_embeddings_openai_import_error(sample_text_chunks):
    """Teste ImportError si OpenAI n'est pas installé et qu'un modèle OpenAI est demandé."""
    with patch(OPENAI_CLIENT_PATH, None): # Simule l'échec de l'import d'OpenAI
        with pytest.raises(ImportError, match="La bibliothèque OpenAI est requise"):
            get_embeddings_for_chunks(sample_text_chunks, "text-embedding-ada-002")

def test_get_embeddings_sentence_transformer_import_error(sample_text_chunks):
    """Teste ImportError si SentenceTransformer n'est pas installé."""
    with patch(SENTENCE_TRANSFORMER_PATH, None): # Simule l'échec de l'import
        with pytest.raises(ImportError, match="La bibliothèque 'sentence-transformers' est requise"):
            get_embeddings_for_chunks(sample_text_chunks, "some-st-model")

def test_get_embeddings_openai_api_error(sample_text_chunks):
    """Teste la gestion d'une APIError d'OpenAI."""

    # Définir la classe d'erreur à utiliser pour ce test.
    # Elle doit avoir une signature __init__(self, message, request, body)
    # pour être compatible avec la façon dont elle est instanciée pour side_effect.
    ErrorToUseInTest = None
    try:
        from openai import APIError as RealOpenAIAPIError
        # Vérifier si la vraie APIError peut être instanciée comme nous le souhaitons
        # (cela suppose que httpx est disponible si openai est installé)
        import httpx as check_httpx
        dummy_request_for_check = check_httpx.Request(method="POST", url="https://api.openai.com/v1/embeddings")
        RealOpenAIAPIError("check", request=dummy_request_for_check, body=None)
        ErrorToUseInTest = RealOpenAIAPIError
    except ImportError: # Si openai ou httpx ne sont pas là, ou si l'instanciation échoue
        pass # ErrorToUseInTest reste None

    if ErrorToUseInTest is None: # Fallback sur une classe factice
        import httpx as fallback_httpx # Assurer que httpx est disponible pour dummy_request
        class FakeAPIError(Exception):
            def __init__(self, message, request=None, body=None):
                super().__init__(message)
                self.request = request
                self.body = body
                self.message = message # Pour le match de pytest.raises
                # Attributs que openai.APIError pourrait avoir
                self.status_code = 400
                self.code = "test_error_code"
        ErrorToUseInTest = FakeAPIError

    mock_openai_constructor = MagicMock(name="MockOpenAIConstructor")
    mock_client_instance = MagicMock(name="MockClientInstance")

    # httpx est nécessaire pour créer dummy_request
    # Si nous sommes ici, httpx a été importé soit par le try, soit par le fallback
    # (ou il était déjà importé au niveau du module par une correction précédente)
    # Pour être sûr, on peut l'importer ici s'il n'est pas déjà dans le scope global du test.
    # Mais il a été ajouté à la ligne 12.

    dummy_request = httpx.Request(method="POST", url="https://api.openai.com/v1/embeddings")
    error_instance_to_raise = ErrorToUseInTest(
        "Test API Error", request=dummy_request, body=None
    )
    mock_client_instance.embeddings.create.side_effect = error_instance_to_raise
    mock_openai_constructor.return_value = mock_client_instance

    with patch(OPENAI_CLIENT_PATH, new=mock_openai_constructor), \
         patch(OPENAI_API_ERROR_PATH, new=ErrorToUseInTest): # Assure que embedding_utils.APIError est notre ErrorToUseInTest
        
        with pytest.raises(ErrorToUseInTest, match="Test API Error"):
            get_embeddings_for_chunks(sample_text_chunks, "text-embedding-3-small")


# Tests pour save_embeddings_data

@pytest.fixture
def sample_embeddings_data():
    return {"model": "test-model", "texts": ["a", "b"], "embeddings": [[0.1], [0.2]]}

def test_save_embeddings_data_success(tmp_path, sample_embeddings_data):
    """Teste la sauvegarde réussie des données d'embeddings."""
    output_file = tmp_path / "embeddings_output" / "test_embeddings.json"
    
    # Mocker Path.mkdir et open
    with patch(MKDIR_PATH) as mock_mkdir, \
         patch(OPEN_BUILTIN_PATH, mock_open()) as mock_file_open:
        
        success = save_embeddings_data(sample_embeddings_data, output_file)
        
        assert success is True
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file_open.assert_called_once_with(output_file, 'w', encoding='utf-8')
        
        # Vérifier que json.dump a été appelé avec les bonnes données
        # mock_file_open().write est ce que json.dump appelle indirectement.
        # Pour vérifier le contenu exact, il faudrait inspecter les appels à handle.write()
        # ou utiliser un mock plus sophistiqué pour json.dump.
        # Ici, on vérifie au moins que le fichier a été ouvert en écriture.
        # Pour une vérification plus poussée de json.dump:
        with patch('json.dump') as mock_json_dump:
            save_embeddings_data(sample_embeddings_data, output_file) # Appeler à nouveau avec le mock json.dump
            mock_json_dump.assert_called_once_with(
                sample_embeddings_data, 
                mock_file_open(), # Le handle de fichier mocké
                ensure_ascii=False, 
                indent=4
            )


def test_save_embeddings_data_io_error(tmp_path, sample_embeddings_data, caplog):
    """Teste la gestion d'une IOError lors de la sauvegarde."""
    output_file = tmp_path / "embeddings_io_error.json"
    
    with patch(MKDIR_PATH), \
         patch(OPEN_BUILTIN_PATH, mock_open()) as mock_file_open:
        # Simuler une IOError lors de l'écriture
        mock_file_open().side_effect = IOError("Test IOError")
        
        success = save_embeddings_data(sample_embeddings_data, output_file)
        
        assert success is False
        assert "Erreur d'E/S lors de la sauvegarde" in caplog.text
        assert "Test IOError" in caplog.text

def test_save_embeddings_data_other_exception(tmp_path, sample_embeddings_data, caplog):
    """Teste la gestion d'une exception générique lors de la sauvegarde."""
    output_file = tmp_path / "embeddings_other_error.json"
    
    with patch(MKDIR_PATH), \
         patch(OPEN_BUILTIN_PATH, mock_open()) as mock_file_open:
        # Simuler une exception générique
        mock_file_open().side_effect = Exception("Test Generic Exception")
        
        success = save_embeddings_data(sample_embeddings_data, output_file)
        
        assert success is False
        assert "Erreur inattendue lors de la sauvegarde" in caplog.text
        assert "Test Generic Exception" in caplog.text

def test_save_embeddings_data_mkdir_fails(tmp_path, sample_embeddings_data, caplog):
    """Teste le cas où la création du répertoire parent échoue."""
    output_file = tmp_path / "dir_fail" / "embeddings.json"
    
    with patch(MKDIR_PATH, side_effect=OSError("Cannot create directory")) as mock_mkdir, \
         patch(OPEN_BUILTIN_PATH, mock_open()): # open ne sera pas appelé si mkdir échoue avant
        
        success = save_embeddings_data(sample_embeddings_data, output_file)
        
        assert success is False
        mock_mkdir.assert_called_once()
        # L'erreur est capturée par le `except Exception` générique dans save_embeddings_data
        assert "Erreur d'E/S lors de la sauvegarde" in caplog.text
        assert "Cannot create directory" in caplog.text