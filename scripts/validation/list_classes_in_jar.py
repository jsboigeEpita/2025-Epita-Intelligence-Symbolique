import zipfile
import sys
import os


def list_classes_in_package(jar_path, package_name):
    """
    Liste toutes les classes (.class) dans un package spécifique d'un fichier JAR.

    :param jar_path: Chemin vers le fichier .jar
    :param package_name: Le nom du package à inspecter (ex: org.tweetyproject.logics.fol.reasoner)
    """
    package_path = package_name.replace(".", "/")
    found_classes = []

    try:
        with zipfile.ZipFile(jar_path, "r") as jar_file:
            for file_path in jar_file.namelist():
                if file_path.startswith(package_path + "/") and file_path.endswith(
                    ".class"
                ):
                    # Extrait le nom de la classe du chemin complet
                    class_name = file_path[len(package_path) + 1 : -6]
                    # Ignore les classes internes/anonymes pour plus de clarté
                    if "$" not in class_name:
                        found_classes.append(class_name)

        if found_classes:
            print(
                f"Classes trouvées dans le package '{package_name}' du fichier '{os.path.basename(jar_path)}':"
            )
            for c in sorted(found_classes):
                print(f"  - {c}")
        else:
            print(
                f"Aucune classe trouvée pour le package '{package_name}' dans '{os.path.basename(jar_path)}'."
            )
            print(f"(Recherche du préfixe : '{package_path}/')")

    except FileNotFoundError:
        print(f"ERREUR: Le fichier JAR '{jar_path}' n'a pas été trouvé.")
    except zipfile.BadZipFile:
        print(f"ERREUR: Le fichier JAR '{jar_path}' est corrompu ou invalide.")
    except Exception as e:
        print(f"ERREUR: Une erreur inattendue est survenue : {e}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "Usage: python list_classes_in_jar.py <chemin_vers_le_jar> <nom_du_package>"
        )
        print(
            "Exemple: python list_classes_in_jar.py libs/tweety/tweety.jar org.tweetyproject.logics.fol.reasoner"
        )
        sys.exit(1)

    jar_file_path = sys.argv[1]
    package_to_inspect = sys.argv[2]

    if not os.path.exists(jar_file_path):
        print(f"ERREUR: Le fichier spécifié '{jar_file_path}' n'existe pas.")
        sys.exit(1)

    list_classes_in_package(jar_file_path, package_to_inspect)
