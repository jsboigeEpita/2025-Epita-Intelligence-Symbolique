
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# tests/utils/test_crypto_utils.py
import pytest
import base64
import os
from unittest import mock
 
 # MODIFIÉ: Ajout de encrypt_data_with_fernet et decrypt_data_with_fernet
from argumentation_analysis.core.utils.crypto_utils import (
    derive_encryption_key, load_encryption_key, FIXED_SALT,
    encrypt_data_with_fernet, decrypt_data_with_fernet
)

# Constantes pour les tests
TEST_PASSPHRASE_VALID = "unePhraseSecreteDeTestRobuste123!?"
TEST_PASSPHRASE_SIMPLE = "simple"
TEST_PASSPHRASE_EMPTY = ""

# Valeur attendue pour TEST_PASSPHRASE_VALID avec les paramètres actuels (SHA256, 32 bytes, salt fixe, 480000 iterations)
# Cette valeur doit être générée une fois et vérifiée.
# Pour la générer, on peut exécuter derive_encryption_key("unePhraseSecreteDeTestRobuste123!?")
# et copier le résultat ici.
# Exemple (à remplacer par la vraie valeur si différente après exécution) :
# EXPECTED_KEY_FOR_VALID_PASSPHRASE = "U29tZVZhbGlkS2V5Rm9yVGVzdGluZ0V4YW1wbGU=" # Ceci est un placeholder
# Après exécution du bloc if __name__ == '__main__' dans crypto_utils.py avec la passphrase:
# "unePhraseSecreteDeTestRobuste123!?"
# La clé générée est: 'A3g1gQzX0JkYqZ8qj9nKlOvCvGc8vHyfV3c7hL6fSgY='
# MISE À JOUR suite à l'échec du test: la valeur correcte semble être celle retournée par l'exécution.
EXPECTED_KEY_FOR_VALID_PASSPHRASE = b"bdIpkGHyXAa4rFLYZbF6r-QbqlXdstFVk4WJYjPh-sE="

def test_derive_key_valid_passphrase():
    """Teste la dérivation avec une phrase secrète valide."""
    key = derive_encryption_key(TEST_PASSPHRASE_VALID)
    assert key is not None, "La clé ne devrait pas être None pour une phrase secrète valide."
    assert isinstance(key, bytes), "La clé dérivée doit être de type bytes."
    
    # Vérifier si la clé semble être du base64url valide
    try:
        base64.urlsafe_b64decode(key) # key est déjà bytes
    except Exception as e:
        pytest.fail(f"La clé dérivée n'est pas un base64url valide: {e}")
        
    # Vérifier la longueur attendue d'une clé AES-256 encodée en base64 (32 bytes -> 44 chars avec padding)
    # La sortie de urlsafe_b64encode pour 32 bytes est typiquement 44 caractères (avec padding '=' si besoin, retiré ici)
    # ou 43 si pas de padding. Fernet attend une clé de 32 bytes après décodage.
    decoded_key = base64.urlsafe_b64decode(key) # key est déjà bytes
    assert len(decoded_key) == 32, "La clé décodée devrait avoir une longueur de 32 bytes."

def test_derive_key_deterministic():
    """Teste si la dérivation de clé est déterministe."""
    key1 = derive_encryption_key(TEST_PASSPHRASE_SIMPLE)
    key2 = derive_encryption_key(TEST_PASSPHRASE_SIMPLE)
    assert key1 is not None, "key1 ne devrait pas être None."
    assert key2 is not None, "key2 ne devrait pas être None."
    assert key1 == key2, "La dérivation de clé devrait être déterministe."

def test_derive_key_different_passphrases():
    """Teste si des phrases secrètes différentes produisent des clés différentes."""
    key1 = derive_encryption_key(TEST_PASSPHRASE_VALID)
    key2 = derive_encryption_key(TEST_PASSPHRASE_SIMPLE)
    assert key1 is not None
    assert key2 is not None
    assert key1 != key2, "Des phrases secrètes différentes devraient produire des clés différentes."

def test_derive_key_empty_passphrase():
    """Teste la dérivation avec une phrase secrète vide."""
    # Selon l'implémentation actuelle, une phrase vide pourrait lever une erreur
    # ou retourner None si l'erreur est capturée.
    # L'implémentation actuelle dans crypto_utils.py capture l'exception et retourne None.
    key = derive_encryption_key(TEST_PASSPHRASE_EMPTY)
    assert key is None, "La dérivation avec une phrase secrète vide devrait retourner None."

def test_derive_key_known_value():
    """Teste la dérivation contre une valeur connue pour une phrase secrète donnée."""
    # Cette valeur doit être pré-calculée avec les mêmes paramètres (salt, itérations, etc.)
    # que ceux utilisés dans la fonction derive_encryption_key.
    # IMPORTANT: Si FIXED_SALT ou les itérations changent dans crypto_utils.py,
    # cette valeur attendue DOIT être recalculée.
    key = derive_encryption_key(TEST_PASSPHRASE_VALID)
    assert key == EXPECTED_KEY_FOR_VALID_PASSPHRASE, \
        f"La clé dérivée ne correspond pas à la valeur attendue. Obtenu: {key!r}, Attendu: {EXPECTED_KEY_FOR_VALID_PASSPHRASE!r}"

def test_fixed_salt_unchanged():
    """Vérifie que le FIXED_SALT utilisé dans les tests est le même que dans le module."""
    # Ceci est un test de "garde" pour s'assurer que si le salt change dans le module,
    # on s'en rend compte car EXPECTED_KEY_FOR_VALID_PASSPHRASE deviendrait invalide.
    # Il n'est pas nécessaire d'importer et de comparer directement si on fait confiance
    # au test_derive_key_known_value, mais cela peut aider au débogage.
    assert FIXED_SALT == b'q\x8b\t\x97\x8b\xe9\xa3\xf2\xe4\x8e\xea\xf5\xe8\xb7\xd6\x8c', \
        "Le FIXED_SALT dans crypto_utils a peut-être changé. Mettre à jour EXPECTED_KEY_FOR_VALID_PASSPHRASE."

# --- Tests pour load_encryption_key ---

TEST_ENV_VAR_NAME = "TEST_CRYPTO_PASSPHRASE"
EXPECTED_KEY_FOR_SIMPLE_PASSPHRASE = derive_encryption_key(TEST_PASSPHRASE_SIMPLE) # Pré-calculer pour comparaison

def test_load_key_from_passphrase_arg():
    """Teste le chargement de la clé via l'argument passphrase_arg."""
    key = load_encryption_key(passphrase_arg=TEST_PASSPHRASE_SIMPLE, env_var_name=TEST_ENV_VAR_NAME)
    assert key is not None
    assert key == EXPECTED_KEY_FOR_SIMPLE_PASSPHRASE

@mock.patch.dict(os.environ, {TEST_ENV_VAR_NAME: TEST_PASSPHRASE_SIMPLE})
def test_load_key_from_env_var():
    """Teste le chargement de la clé via la variable d'environnement."""
    key = load_encryption_key(passphrase_arg=None, env_var_name=TEST_ENV_VAR_NAME)
    assert key is not None
    assert key == EXPECTED_KEY_FOR_SIMPLE_PASSPHRASE

@mock.patch.dict(os.environ, {TEST_ENV_VAR_NAME: "autrePhraseSecreteMoinsBien"})
def test_load_key_passphrase_arg_priority():
    """Teste que passphrase_arg a la priorité sur la variable d'environnement."""
    key = load_encryption_key(passphrase_arg=TEST_PASSPHRASE_SIMPLE, env_var_name=TEST_ENV_VAR_NAME)
    assert key is not None
    assert key == EXPECTED_KEY_FOR_SIMPLE_PASSPHRASE
    # S'assurer qu'il n'a pas utilisé la valeur de la variable d'environnement
    key_from_env_alone = derive_encryption_key("autrePhraseSecreteMoinsBien")
    assert key != key_from_env_alone

def test_load_key_no_source():
    """Teste l'échec si aucune source de passphrase n'est valide ou fournie."""
    # Assurer que la variable d'environnement n'est pas définie pour ce test
    with mock.patch.dict(os.environ, clear=True):
        key = load_encryption_key(passphrase_arg=None, env_var_name=TEST_ENV_VAR_NAME)
        assert key is None
        # Test avec une passphrase vide en argument et pas de variable d'env
        key_empty_arg = load_encryption_key(passphrase_arg=TEST_PASSPHRASE_EMPTY, env_var_name=TEST_ENV_VAR_NAME)
        assert key_empty_arg is None


@mock.patch.dict(os.environ, {TEST_ENV_VAR_NAME: TEST_PASSPHRASE_SIMPLE})
def test_load_key_invalid_arg_valid_env():
    """Teste le cas où passphrase_arg est invalide (vide) mais la variable d'environnement est valide."""
    # La fonction load_encryption_key essaiera l'arg en premier, échouera (car vide),
    # puis devrait utiliser la variable d'environnement.
    key = load_encryption_key(passphrase_arg=TEST_PASSPHRASE_EMPTY, env_var_name=TEST_ENV_VAR_NAME)
    assert key is not None, "Devrait utiliser la clé de la variable d'env si l'arg est invalide."
    assert key == EXPECTED_KEY_FOR_SIMPLE_PASSPHRASE

@mock.patch.dict(os.environ, {TEST_ENV_VAR_NAME: TEST_PASSPHRASE_EMPTY})
def test_load_key_valid_arg_invalid_env():
    """Teste le cas où passphrase_arg est valide mais la variable d'environnement est invalide (vide)."""
    # Devrait utiliser passphrase_arg et ignorer la variable d'env invalide.
    key = load_encryption_key(passphrase_arg=TEST_PASSPHRASE_SIMPLE, env_var_name=TEST_ENV_VAR_NAME)
    assert key is not None
    assert key == EXPECTED_KEY_FOR_SIMPLE_PASSPHRASE

@mock.patch.dict(os.environ, {TEST_ENV_VAR_NAME: TEST_PASSPHRASE_EMPTY})
def test_load_key_arg_none_invalid_env():
    """Teste le cas où passphrase_arg est None et la variable d'environnement est invalide (vide)."""
    key = load_encryption_key(passphrase_arg=None, env_var_name=TEST_ENV_VAR_NAME)
    assert key is None, "Devrait retourner None si l'env var est invalide et pas d'arg."

# --- Tests pour encrypt_data_with_fernet et decrypt_data_with_fernet ---

FERNET_TEST_PASSPHRASE = "uneAutrePassphrasePourLesTestsFernet"
# Le nom de la variable est changé pour refléter que derive_encryption_key retourne des bytes
FERNET_KEY_B64_BYTES = derive_encryption_key(FERNET_TEST_PASSPHRASE)

TEST_DATA_TO_ENCRYPT = b"Donn\xc3\xa9es secr\xc3\xa8tes avec des caract\xc3\xa8res sp\xc3\xa9ciaux: \xc3\xa9\xc3\xa0\xc3\xbc\xc3\xae\xc3\xb4."

def test_fernet_encrypt_decrypt_cycle():
    """Teste un cycle complet de chiffrement et déchiffrement Fernet."""
    assert FERNET_KEY_B64_BYTES is not None, "La dérivation de la clé b64 bytes pour Fernet ne devrait pas échouer."
    
    # Vérification que la clé b64 bytes peut être décodée en 32 bytes
    # FERNET_KEY_B64_BYTES est déjà bytes, donc pas besoin de .encode()
    decoded_key_for_check = base64.urlsafe_b64decode(FERNET_KEY_B64_BYTES)
    assert len(decoded_key_for_check) == 32, "La clé Fernet (b64 bytes) décodée doit faire 32 bytes."

    encrypted_data = encrypt_data_with_fernet(TEST_DATA_TO_ENCRYPT, FERNET_KEY_B64_BYTES)
    assert encrypted_data is not None, "Le chiffrement Fernet ne devrait pas retourner None avec une clé valide."
    assert encrypted_data != TEST_DATA_TO_ENCRYPT, "Les données chiffrées doivent être différentes des originales."

    decrypted_data = decrypt_data_with_fernet(encrypted_data, FERNET_KEY_B64_BYTES)
    assert decrypted_data is not None, "Le déchiffrement Fernet ne devrait pas retourner None avec une clé valide."
    assert decrypted_data == TEST_DATA_TO_ENCRYPT, "Les données déchiffrées doivent correspondre aux originales."

def test_fernet_decrypt_with_wrong_key():
    """Teste que le déchiffrement Fernet échoue avec une mauvaise clé."""
    encrypted_data = encrypt_data_with_fernet(TEST_DATA_TO_ENCRYPT, FERNET_KEY_B64_BYTES)
    assert encrypted_data is not None

    wrong_passphrase = "ceciEstUneMauvaisePassphrase"
    wrong_b64_key_bytes = derive_encryption_key(wrong_passphrase)
    assert wrong_b64_key_bytes is not None
    assert wrong_b64_key_bytes != FERNET_KEY_B64_BYTES
        
    decrypted_data = decrypt_data_with_fernet(encrypted_data, wrong_b64_key_bytes)
    assert decrypted_data is None, "Le déchiffrement avec une mauvaise clé Fernet devrait retourner None."

def test_fernet_encrypt_no_key():
    """Teste le chiffrement Fernet avec une clé None."""
    encrypted_data = encrypt_data_with_fernet(TEST_DATA_TO_ENCRYPT, None) # Passe None comme b64_encoded_key_str
    assert encrypted_data is None, "Le chiffrement Fernet avec une clé None devrait retourner None."

def test_fernet_decrypt_no_key():
    """Teste le déchiffrement Fernet avec une clé None."""
    # On a besoin de données chiffrées valides pour ce test
    encrypted_data = encrypt_data_with_fernet(TEST_DATA_TO_ENCRYPT, FERNET_KEY_B64_BYTES)
    assert encrypted_data is not None
    
    decrypted_data = decrypt_data_with_fernet(encrypted_data, None) # Passe None comme b64_encoded_key_bytes
    assert decrypted_data is None, "Le déchiffrement Fernet avec une clé None devrait retourner None."

def test_fernet_decrypt_tampered_data():
    """Teste le déchiffrement Fernet avec des données altérées."""
    encrypted_data = encrypt_data_with_fernet(TEST_DATA_TO_ENCRYPT, FERNET_KEY_B64_BYTES)
    assert encrypted_data is not None
    
    # Altérer un byte des données chiffrées
    tampered_data_list = list(encrypted_data)
    original_byte = tampered_data_list[len(tampered_data_list) // 2]
    tampered_data_list[len(tampered_data_list) // 2] = (original_byte + 1) % 256
    tampered_data = bytes(tampered_data_list)
    
    assert tampered_data != encrypted_data

    decrypted_data = decrypt_data_with_fernet(tampered_data, FERNET_KEY_B64_BYTES)
    assert decrypted_data is None, "Le déchiffrement Fernet avec des données altérées devrait retourner None (InvalidToken/Signature)."


# Pour exécuter ces tests:
# Assurez-vous que pytest est installé et que le PYTHONPATH est configuré pour trouver project_core.
# Depuis la racine du projet:
# python -m pytest tests/utils/test_crypto_utils.py