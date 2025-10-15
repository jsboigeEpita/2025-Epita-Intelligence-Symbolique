import zipfile
import sys


def find_string_in_jar_names(jar_path, search_string, case_sensitive=False):
    """
    Recherche une chaîne de caractères dans les noms de fichiers d'un JAR.

    :param jar_path: Chemin vers le fichier .jar
    :param search_string: La chaîne à rechercher
    :param case_sensitive: Si la recherche doit être sensible à la casse
    """
    found_files = []
    try:
        with zipfile.ZipFile(jar_path, "r") as jar_file:
            for file_path in jar_file.namelist():
                haystack = file_path if case_sensitive else file_path.lower()
                needle = search_string if case_sensitive else search_string.lower()
                if needle in haystack:
                    found_files.append(file_path)

        if found_files:
            print(
                f"Correspondances pour '{search_string}' trouvées dans '{os.path.basename(jar_path)}':"
            )
            for f in sorted(found_files):
                print(f"  - {f}")
            return True
        return False
    except FileNotFoundError:
        print(f"ERREUR: Le fichier JAR '{jar_path}' n'existe pas.")
        return False
    except zipfile.BadZipFile:
        # Fichier .jar corrompu ou invalide, on l'ignore poliment
        return False
    except Exception as e:
        print(
            f"ERREUR: Une erreur inattendue est survenue en traitant '{os.path.basename(jar_path)}': {e}"
        )
        return False


import os

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "Usage: python check_jar_content.py <repertoire_des_jars> <chaine_a_chercher> [--case-sensitive]"
        )
        sys.exit(1)

    jars_dir = sys.argv[1]
    string_to_find = sys.argv[2]
    case_sensitive = len(sys.argv) > 3 and sys.argv[3] == "--case-sensitive"

    if not os.path.isdir(jars_dir):
        print(f"ERREUR: Le répertoire '{jars_dir}' n'existe pas.")
        sys.exit(1)

    total_found = 0
    for filename in sorted(os.listdir(jars_dir)):
        if filename.endswith(".jar"):
            jar_path = os.path.join(jars_dir, filename)
            if find_string_in_jar_names(jar_path, string_to_find, case_sensitive):
                total_found += 1

    if total_found == 0:
        print(
            f"\nCONCLUSION: La chaîne '{string_to_find}' n'a été trouvée dans aucun nom de fichier des .jar du répertoire '{jars_dir}'."
        )
    else:
        print(
            f"\nCONCLUSION: Recherche terminée. {total_found} fichier(s) JAR contenaient la chaîne '{string_to_find}'."
        )
