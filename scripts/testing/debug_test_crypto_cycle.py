import argumentation_analysis.core.environment

# scripts/debug_test_crypto_cycle.py
import base64
import sys
import os

try:
    from argumentation_analysis.ui.config import ENCRYPTION_KEY
    from argumentation_analysis.ui.utils import encrypt_data, decrypt_data
except ImportError as e:
    print(f"Erreur d'importation initiale: {e}")
    print("Tentative d'ajustement du PYTHONPATH...")
    # Détermine la racine du projet en supposant que ce script est dans 'scripts/'
    # et que 'argumentation_analysis/' est au même niveau que 'scripts/' (c'est-à-dire dans le parent de 'scripts/')
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root_assumed = os.path.abspath(
        os.path.join(current_script_dir, "..", "..")
    )  # MODIFIÉ: Remonter de deux niveaux

    if project_root_assumed not in sys.path:
        sys.path.insert(0, project_root_assumed)
        print(f"Ajout de '{project_root_assumed}' au PYTHONPATH.")
        # Retenter l'import
        try:
            from argumentation_analysis.ui.config import ENCRYPTION_KEY
            from argumentation_analysis.ui.utils import encrypt_data, decrypt_data

            print("Imports réussis après ajustement du PYTHONPATH.")
        except ImportError as e2:
            print(f"Erreur d'importation même après ajustement: {e2}")
            print(f"PYTHONPATH actuel: {sys.path}")
            sys.exit(1)
    else:
        print(
            "Le chemin racine présumé du projet est déjà dans PYTHONPATH, mais l'import a échoué."
        )
        print(f"PYTHONPATH actuel: {sys.path}")
        sys.exit(1)


def test_encryption_decryption_cycle():
    test_string = "Ceci est un test de chiffrement."
    print(f"Chaîne originale: '{test_string}'")

    # Encodage
    test_data_bytes = test_string.encode("utf-8")
    print(f"Données originales (bytes): {test_data_bytes!r}")

    # Chiffrement
    encrypted_bytes_val = None
    try:
        encrypted_bytes_val = encrypt_data(test_data_bytes, ENCRYPTION_KEY)
        print(f"Données chiffrées (bytes): {encrypted_bytes_val!r}")
        print(
            f"Données chiffrées (base64): {base64.b64encode(encrypted_bytes_val).decode('utf-8')}"
        )
    except Exception as e:
        print(f"Erreur pendant le chiffrement: {e}")
        import traceback

        traceback.print_exc()
        return False, test_string, None, None

    # Déchiffrement
    decrypted_bytes_val = None
    try:
        decrypted_bytes_val = decrypt_data(encrypted_bytes_val, ENCRYPTION_KEY)
        print(f"Données déchiffrées (bytes): {decrypted_bytes_val!r}")
    except Exception as e:
        print(f"Erreur pendant le déchiffrement: {e}")
        import traceback

        traceback.print_exc()
        return False, test_string, encrypted_bytes_val, None

    # Décodage
    decrypted_string_val = None
    try:
        decrypted_string_val = decrypted_bytes_val.decode("utf-8")
        print(f"Chaîne déchiffrée: '{decrypted_string_val}'")
    except Exception as e:
        print(f"Erreur pendant le décodage: {e}")
        import traceback

        traceback.print_exc()
        return False, test_string, encrypted_bytes_val, decrypted_bytes_val

    # Comparaison
    if test_string == decrypted_string_val:
        print("Succès: La chaîne originale et la chaîne déchiffrée sont identiques.")
        return True, test_string, encrypted_bytes_val, decrypted_string_val
    else:
        print("Échec: La chaîne originale et la chaîne déchiffrée sont différentes.")
        return False, test_string, encrypted_bytes_val, decrypted_string_val


if __name__ == "__main__":
    success, original, encrypted, decrypted_result = test_encryption_decryption_cycle()

    final_decrypted_str = "N/A"
    if decrypted_result is not None:
        if isinstance(decrypted_result, str):
            final_decrypted_str = decrypted_result
        elif isinstance(decrypted_result, bytes):
            try:
                final_decrypted_str = decrypted_result.decode("utf-8")
            except UnicodeDecodeError:
                final_decrypted_str = (
                    f"Impossible de décoder les bytes: {decrypted_result!r}"
                )
    elif not success:  # Si decrypted_result est None et que le test a échoué
        if encrypted is None:  # Erreur de chiffrement
            final_decrypted_str = "N/A (erreur de chiffrement)"
        else:  # Erreur de déchiffrement (encrypted n'est pas None)
            final_decrypted_str = "N/A (erreur de déchiffrement)"

    print(f"\n--- Résumé du Test ---")
    print(f"Chaîne originale        : {original}")
    if encrypted:
        print(
            f"Données chiffrées (b64) : {base64.b64encode(encrypted).decode('utf-8') if isinstance(encrypted, bytes) else 'N/A (non byte)'}"
        )
    else:
        print(f"Données chiffrées (b64) : N/A (erreur de chiffrement ou non byte)")
    print(f"Chaîne déchiffrée       : {final_decrypted_str}")
    print(f"Statut du cycle         : {'Succès' if success else 'Échec'}")
