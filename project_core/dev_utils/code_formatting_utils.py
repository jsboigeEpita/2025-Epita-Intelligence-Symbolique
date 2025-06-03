# project_core/dev_utils/code_formatting_utils.py
import logging
import subprocess
import os
import sys

# Configuration du logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def format_python_file_with_autopep8(file_path: str, autopep8_args: list = None) -> bool:
    """
    Formate un fichier Python en utilisant l'outil externe autopep8.

    Args:
        file_path: Chemin du fichier Python à formater.
        autopep8_args: Liste optionnelle d'arguments supplémentaires à passer à autopep8.
                       Par défaut, utilise ['--in-place', '--aggressive', '--aggressive'].

    Returns:
        True si le formatage a réussi (ou si autopep8 n'a rien changé), False en cas d'erreur.
    """
    if not os.path.isfile(file_path):
        logger.error(f"Fichier non trouvé : {file_path}")
        return False

    final_autopep8_args = []
    if autopep8_args is None:
        # Arguments par défaut si aucun n'est fourni
        final_autopep8_args = ['--in-place', '--aggressive', '--aggressive']
    else:
        # Si des arguments sont fournis par l'utilisateur, ce sont les seuls utilisés.
        # L'utilisateur est responsable d'inclure '--in-place' s'il le souhaite pour modifier le fichier.
        # Si la liste d'arguments est vide (ex: passée explicitement comme []),
        # autopep8 sera appelé sans arguments spécifiques autres que le fichier.
        final_autopep8_args = autopep8_args

    command = ['autopep8'] + final_autopep8_args + [file_path]
    
    logger.info(f"Exécution de autopep8 sur {file_path} avec la commande: {' '.join(command)}")
    
    try:
        # Vérifier si autopep8 est installé/accessible
        try:
            subprocess.run(['autopep8', '--version'], check=True, capture_output=True, text=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"autopep8 ne semble pas être installé ou accessible dans le PATH. Erreur: {e}")
            logger.error("Veuillez installer autopep8: pip install autopep8")
            return False

        process = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        
        if process.stdout:
            logger.info(f"Sortie de autopep8 pour {file_path}:\n{process.stdout}")
        if process.stderr:
            # autopep8 peut écrire des informations non critiques sur stderr,
            # par exemple s'il n'a rien à changer.
            logger.info(f"Sortie d'erreur (potentiellement informative) de autopep8 pour {file_path}:\n{process.stderr}")
        
        logger.info(f"Formatage de {file_path} terminé avec succès.")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'exécution de autopep8 sur {file_path}.")
        logger.error(f"Commande: {' '.join(e.cmd)}")
        logger.error(f"Code de retour: {e.returncode}")
        if e.stdout:
            logger.error(f"Sortie standard:\n{e.stdout}")
        if e.stderr:
            logger.error(f"Sortie d'erreur:\n{e.stderr}")
        return False
    except FileNotFoundError:
        logger.error("La commande autopep8 n'a pas été trouvée. Assurez-vous qu'elle est installée et dans votre PATH.")
        logger.error("Installation: pip install autopep8")
        return False
    except Exception as e:
        logger.error(f"Une erreur inattendue est survenue lors du formatage de {file_path}: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    # Section de test simple
    logger.setLevel(logging.DEBUG)
    
    # Créer un fichier de test avec une mauvaise indentation
    test_file_content_bad = """
def  bad_function( a, b ):
  if a > b:
    print('a is greater')
  else:
      print('b is greater or equal')
    return b+a

class   BadClass :
  def __init__( self,param1 ):
    self.param1=param1
    
  def  another_method( self, x,y, z ):
        print(x,y,z)
"""
    temp_test_file = "temp_autopep8_test_file.py"
    with open(temp_test_file, "w", encoding="utf-8") as f:
        f.write(test_file_content_bad)

    logger.info(f"\n--- Test de format_python_file_with_autopep8 sur {temp_test_file} ---")
    
    # Contenu attendu (approximatif, autopep8 peut faire plus)
    expected_content_good = """
def bad_function(a, b):
    if a > b:
        print('a is greater')
    else:
        print('b is greater or equal')
    return b + a


class BadClass:
    def __init__(self, param1):
        self.param1 = param1

    def another_method(self, x, y, z):
        print(x, y, z)
"""
    
    success = format_python_file_with_autopep8(temp_test_file)
    
    if success:
        logger.info(f"Formatage terminé. Contenu du fichier {temp_test_file}:")
        with open(temp_test_file, "r", encoding="utf-8") as f:
            formatted_content = f.read()
            print(formatted_content)
            # Note: Une comparaison exacte avec expected_content_good peut être difficile
            # car autopep8 peut appliquer d'autres corrections.
            # Pour un vrai test, on vérifierait des aspects spécifiques ou l'idempotence.
            if "def bad_function(a, b):" in formatted_content and "    if a > b:" in formatted_content:
                 logger.info("Quelques vérifications basiques du formatage semblent OK.")
            else:
                logger.warning("Le formatage semble avoir produit un résultat inattendu.")
    else:
        logger.error(f"Échec du formatage pour {temp_test_file}.")

    # Nettoyage
    if os.path.exists(temp_test_file):
        os.remove(temp_test_file)
        logger.info(f"Fichier de test {temp_test_file} supprimé.")