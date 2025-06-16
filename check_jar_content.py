import zipfile
import sys

def check_class_in_jar(jar_path, class_name):
    """
    Vérifie si une classe est présente dans un fichier JAR.

    :param jar_path: Chemin vers le fichier .jar
    :param class_name: Nom complet de la classe (ex: org.tweetyproject.commons.util.Order)
    """
    class_path = class_name.replace('.', '/') + '.class'
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar_file:
            if class_path in jar_file.namelist():
                print(f"SUCCES: La classe '{class_name}' a été trouvée dans '{jar_path}'.")
                return True
            else:
                print(f"ECHEC: La classe '{class_name}' n'a pas été trouvée dans '{jar_path}'.")
                # Optionnel: lister les fichiers pour le débogage si la classe n'est pas trouvée
                # print("Contenu du JAR:")
                # for name in jar_file.namelist():
                #     if 'Order' in name:
                #          print(name)
                return False
    except FileNotFoundError:
        print(f"ERREUR: Le fichier JAR '{jar_path}' n'existe pas.")
        return False
    except Exception as e:
        print(f"ERREUR: Une erreur inattendue est survenue: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python check_jar_content.py <chemin_vers_le_jar> <nom_de_la_classe>")
        sys.exit(1)

    jar_to_check = sys.argv[1]
    class_to_find = sys.argv[2]
    check_class_in_jar(jar_to_check, class_to_find)