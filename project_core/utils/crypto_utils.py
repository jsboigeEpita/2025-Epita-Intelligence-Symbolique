# project_core/utils/crypto_utils.py
import base64
import logging
import os # NOUVEAU: Import nécessaire
from typing import Optional # NOUVEAU: Import nécessaire
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet, InvalidToken # NOUVEAU: Pour encrypt/decrypt_data
from cryptography.exceptions import InvalidSignature # NOUVEAU: Pour decrypt_data

# Configuration du logging pour ce module
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO) # Ou un autre niveau par défaut souhaité

# Sel fixe, identique à celui utilisé précédemment.
# Pourrait être externalisé dans une configuration si partagé par d'autres modules.
FIXED_SALT = b'q\x8b\t\x97\x8b\xe9\xa3\xf2\xe4\x8e\xea\xf5\xe8\xb7\xd6\x8c'

def derive_encryption_key(passphrase: str) -> str:
    """
    Dérive une clé de chiffrement à partir d'une phrase secrète.
    
    Args:
        passphrase: La phrase secrète
        
    Returns:
        str: La clé de chiffrement dérivée et encodée en base64, ou None en cas d'erreur ou si la passphrase est vide.
    """
    if not passphrase:
        logger.warning("Tentative de dérivation de clé avec une phrase secrète vide. Retour de None.")
        return None
    try:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=FIXED_SALT,
            iterations=480000, # Assurez-vous que ce nombre d'itérations est cohérent avec l'utilisation originale
            backend=default_backend()
        )
        derived_key_raw = kdf.derive(passphrase.encode('utf-8'))
        encryption_key = base64.urlsafe_b64encode(derived_key_raw)
        
        logger.debug("Clé de chiffrement dérivée avec succès.")
        return encryption_key.decode('utf-8') # Retourner une chaîne str
    except Exception as e:
        logger.error(f"Erreur lors de la dérivation de la clé: {e}", exc_info=True)
        return None

def load_encryption_key(passphrase_arg: Optional[str] = None, env_var_name: str = "TEXT_CONFIG_PASSPHRASE") -> Optional[str]:
    """
    Charge la clé de chiffrement en essayant d'abord la phrase secrète fournie,
    puis une variable d'environnement.

    Args:
        passphrase_arg: La phrase secrète fournie en argument (optionnelle).
        env_var_name: Le nom de la variable d'environnement à vérifier pour la phrase secrète.

    Returns:
        Optional[str]: La clé de chiffrement dérivée et encodée en base64, ou None si non disponible ou en cas d'erreur.
    """
    # Essayer avec la phrase secrète fournie en argument
    if passphrase_arg:
        logger.info("Utilisation de la phrase secrète fournie en argument pour dériver la clé...")
        encryption_key = derive_encryption_key(passphrase_arg)
        if encryption_key:
            logger.info("✅ Clé de chiffrement dérivée avec succès à partir de l'argument.")
            return encryption_key
        else:
            # L'erreur est déjà loggée par derive_encryption_key
            logger.warning("Échec de la dérivation de la clé à partir de l'argument passphrase.")
            # On continue pour essayer la variable d'environnement au cas où l'argument était invalide mais la variable existe.
    
    # Essayer de charger depuis la variable d'environnement
    env_passphrase = os.getenv(env_var_name)
    if env_passphrase:
        logger.info(f"Phrase secrète trouvée dans la variable d'environnement '{env_var_name}'.")
        encryption_key = derive_encryption_key(env_passphrase)
        if encryption_key:
            logger.info("✅ Clé de chiffrement dérivée avec succès à partir de la variable d'environnement.")
            return encryption_key
        else:
            # L'erreur est déjà loggée par derive_encryption_key
            logger.error(f"Échec de la dérivation de la clé à partir de la variable d'environnement '{env_var_name}'.")
            return None # Échec définitif si la variable d'env a été trouvée mais la dérivation a échoué
            
    if not passphrase_arg and not env_passphrase:
        logger.warning("Aucune phrase secrète fournie (ni argument, ni variable d'environnement).")
        logger.warning(f"Assurez-vous que la variable d'environnement '{env_var_name}' est définie ou fournissez une phrase secrète.")

    return None # Retourne None si aucune source de passphrase n'a abouti à une clé

# --- Fonctions de chiffrement/déchiffrement Fernet ---

def encrypt_data_with_fernet(data: bytes, b64_encoded_key_str: str) -> Optional[bytes]:
    """
    Chiffre des données binaires avec une clé Fernet.
    La clé est la chaîne de caractères encodée en base64url (sortie de derive_encryption_key).

    Args:
        data: Les données binaires à chiffrer.
        b64_encoded_key_str: La clé de chiffrement Fernet, encodée en base64url (str).

    Returns:
        Optional[bytes]: Les données chiffrées, ou None en cas d'erreur.
    """
    if not b64_encoded_key_str:
        logger.error("Erreur chiffrement Fernet: Clé (str b64) manquante.")
        return None
    try:
        # Fernet attend la clé encodée en base64url, mais sous forme de bytes.
        key_bytes = b64_encoded_key_str.encode('utf-8')
        f = Fernet(key_bytes)
        return f.encrypt(data)
    except Exception as e:
        logger.error(f"Erreur chiffrement Fernet: {e}", exc_info=True)
        return None

def decrypt_data_with_fernet(encrypted_data: bytes, b64_encoded_key_str: str) -> Optional[bytes]:
    """
    Déchiffre des données binaires avec une clé Fernet.
    La clé est la chaîne de caractères encodée en base64url (sortie de derive_encryption_key).

    Args:
        encrypted_data: Les données chiffrées.
        b64_encoded_key_str: La clé de chiffrement Fernet, encodée en base64url (str).

    Returns:
        Optional[bytes]: Les données déchiffrées, ou None en cas d'erreur ou de token invalide.
    """
    if not b64_encoded_key_str:
        logger.error("Erreur déchiffrement Fernet: Clé (str b64) manquante.")
        return None
    try:
        # Fernet attend la clé encodée en base64url, mais sous forme de bytes.
        key_bytes = b64_encoded_key_str.encode('utf-8')
        f = Fernet(key_bytes)
        return f.decrypt(encrypted_data)
    except (InvalidToken, InvalidSignature) as e:
        logger.error(f"Erreur déchiffrement Fernet (InvalidToken/Signature): {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur déchiffrement Fernet (Autre): {e}", exc_info=True)
        return None

if __name__ == '__main__':
    # Section de test simple pour la dérivation de clé
    logger.setLevel(logging.DEBUG)
    test_passphrase = "ma_super_phrase_secrete_de_test"
    logger.info(f"Test de dérivation de clé pour la phrase secrète: '{test_passphrase}'")
    
    key = derive_encryption_key(test_passphrase)
    if key:
        logger.info(f"Clé dérivée (encodée en base64): {key}")
        # Test de re-dérivation pour s'assurer de la consistance
        key2 = derive_encryption_key(test_passphrase)
        if key == key2:
            logger.info("✅ La re-dérivation produit la même clé.")
        else:
            logger.error("❌ ERREUR: La re-dérivation ne produit PAS la même clé.")
    else:
        logger.error("❌ Échec de la dérivation de la clé.")

    # Test avec une phrase vide (devrait échouer ou retourner None)
    logger.info("Test de dérivation avec une phrase secrète vide...")
    empty_key = derive_encryption_key("")
    if empty_key:
        logger.warning(f"Clé dérivée pour phrase vide: {empty_key} (ceci peut être inattendu)")
    else:
        logger.info("✅ La dérivation avec phrase vide a retourné None, comme attendu.")

    # Tests pour encrypt_data_with_fernet et decrypt_data_with_fernet
    logger.info("\n--- Tests Fernet ---")
    test_data = b"Donn\xc3\xa9es secr\xc3\xa8tes \xc3\xa0 chiffrer!"
    logger.info(f"Données originales: {test_data.decode('utf-8', 'ignore')}")

    # Utiliser une clé dérivée valide pour les tests Fernet
    fernet_test_passphrase = "uneAutrePhrasePourFernet"
    derived_b64_key = derive_encryption_key(fernet_test_passphrase)

    if derived_b64_key:
        logger.info(f"Clé dérivée (b64) pour tests Fernet: {derived_b64_key}")
        try:
            # La clé Fernet doit être les bytes décodés de la clé b64
            actual_fernet_key = base64.urlsafe_b64decode(derived_b64_key.encode('utf-8'))
            logger.info(f"Clé Fernet actuelle (bytes) pour tests: {actual_fernet_key}")

            encrypted = encrypt_data_with_fernet(test_data, actual_fernet_key)
            if encrypted:
                logger.info(f"Données chiffrées: {encrypted}")
                decrypted = decrypt_data_with_fernet(encrypted, actual_fernet_key)
                if decrypted:
                    logger.info(f"Données déchiffrées: {decrypted.decode('utf-8', 'ignore')}")
                    if decrypted == test_data:
                        logger.info("✅ Chiffrement et déchiffrement Fernet réussis!")
                    else:
                        logger.error("❌ ERREUR: Les données déchiffrées ne correspondent pas aux originales.")
                else:
                    logger.error("❌ ERREUR: Échec du déchiffrement Fernet.")
            else:
                logger.error("❌ ERREUR: Échec du chiffrement Fernet.")
        except Exception as e_fernet_test:
            logger.error(f"❌ ERREUR lors du test Fernet: {e_fernet_test}", exc_info=True)
    else:
        logger.error("❌ Impossible de tester Fernet, la dérivation de clé a échoué.")
    
    logger.info("\n--- Test déchiffrement Fernet avec mauvaise clé ---")
    if derived_b64_key:
        try:
            actual_fernet_key = base64.urlsafe_b64decode(derived_b64_key.encode('utf-8'))
            encrypted = encrypt_data_with_fernet(test_data, actual_fernet_key) # Chiffrer avec la bonne clé
            
            # Créer une mauvaise clé Fernet (différente de l'originale)
            bad_b64_key = derive_encryption_key("mauvaisePhraseSecrete")
            if bad_b64_key and bad_b64_key != derived_b64_key:
                bad_fernet_key = base64.urlsafe_b64decode(bad_b64_key.encode('utf-8'))
                logger.info("Tentative de déchiffrement avec une mauvaise clé Fernet...")
                decrypted_with_bad_key = decrypt_data_with_fernet(encrypted, bad_fernet_key)
                if decrypted_with_bad_key is None:
                    logger.info("✅ Échec du déchiffrement avec mauvaise clé, comme attendu (InvalidToken/Signature).")
                else:
                    logger.error(f"❌ ERREUR: Le déchiffrement avec une mauvaise clé aurait dû échouer, mais a retourné: {decrypted_with_bad_key}")
            else:
                logger.warning("Impossible de générer une mauvaise clé distincte pour le test.")
        except Exception as e_bad_key_test:
            logger.error(f"❌ ERREUR lors du test de mauvaise clé Fernet: {e_bad_key_test}", exc_info=True)