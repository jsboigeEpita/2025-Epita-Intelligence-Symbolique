"""
Utilitaires pour la génération et la sauvegarde d'embeddings de texte.

Ce module fournit des fonctions pour :
    1.  `get_embeddings_for_chunks`: Générer des embeddings pour une liste de
        morceaux de texte en utilisant soit les modèles d'OpenAI (par exemple,
        "text-embedding-3-small"), soit des modèles de la bibliothèque
        Sentence Transformers (par exemple, "all-MiniLM-L6-v2").
    2.  `save_embeddings_data`: Sauvegarder les données d'embeddings obtenues
        (incluant potentiellement les textes originaux et d'autres métadonnées)
        dans un fichier au format JSON.

Il gère les importations conditionnelles pour OpenAI et Sentence Transformers,
permettant une utilisation flexible même si l'une des bibliothèques n'est pas
installée (bien que cela lèvera une `ImportError` si le modèle correspondant
est sollicité).
"""
import json
from pathlib import Path
from typing import Dict, Any
from typing import List
import logging

# Importation conditionnelle ou gestion d'erreur si openai n'est pas installé.
# Pour l'instant, on suppose qu'il est disponible.
try:
    from openai import OpenAI, APIError
except ImportError:
    # Gérer le cas où la bibliothèque openai n'est pas installée.
    # Pour cette tâche, nous allons supposer qu'elle le sera.
    # Dans un cas réel, on pourrait logger un avertissement ou lever une exception.
    OpenAI = None
    APIError = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

logger = logging.getLogger(__name__)

def get_embeddings_for_chunks(text_chunks: List[str], embedding_model_name: str) -> List[List[float]]:
    """
    Génère les embeddings pour une liste de morceaux de texte en utilisant un modèle spécifié.

    Cette fonction prend une liste de chaînes de caractères (morceaux de texte) et le nom
    d'un modèle d'embedding, puis retourne une liste d'embeddings (chaque embedding
    étant une liste de flottants).

    Supporte les modèles d'embedding OpenAI (par exemple, "text-embedding-3-small")
    et les modèles Sentence Transformers (par exemple, "all-MiniLM-L6-v2").

    :param text_chunks: Une liste de chaînes de caractères, où chaque chaîne est un morceau
                        de texte pour lequel un embedding doit être généré.
    :type text_chunks: List[str]
    :param embedding_model_name: Le nom du modèle d'embedding à utiliser.
                                 Peut être un modèle OpenAI (commençant par "text-embedding-")
                                 ou un modèle Sentence Transformer (par exemple, "all-MiniLM-L6-v2").
    :type embedding_model_name: str

    :return: Une liste d'embeddings, où chaque embedding est une liste de flottants.
             L'ordre des embeddings correspond à l'ordre des morceaux de texte en entrée.
    :rtype: List[List[float]]

    :raises ImportError: Si la bibliothèque requise (OpenAI ou Sentence Transformers)
                         n'est pas installée lors de la tentative d'utilisation du modèle correspondant.
    :raises NotImplementedError: Si le `embedding_model_name` ne correspond pas à un type de modèle supporté
                                 (bien que la logique actuelle tente de traiter tout ce qui n'est pas OpenAI
                                 comme un Sentence Transformer, ce qui pourrait être affiné).
    :raises openai.APIError: Si une erreur se produit lors de l'appel à l'API OpenAI.
    :raises ValueError: Si le modèle Sentence Transformer ne peut pas être chargé ou si une
                        erreur survient pendant la génération des embeddings avec Sentence Transformers.
    :raises RuntimeError: Pour des erreurs d'exécution inattendues avec Sentence Transformers.
    :raises Exception: Pour d'autres erreurs inattendues non explicitement gérées.
    """
    # Choix de la méthode de génération d'embeddings en fonction du nom du modèle
    if embedding_model_name.startswith("text-embedding-"):
        # Utilisation des modèles OpenAI
        if OpenAI is None or APIError is None:
            # Commentaire : Vérification critique pour s'assurer que la dépendance OpenAI est disponible.
            # Si elle ne l'est pas, une ImportError est levée pour informer l'utilisateur.
            raise ImportError(
                "La bibliothèque OpenAI est requise pour les modèles 'text-embedding-*' mais n'a pas pu être importée. "
                "Veuillez l'installer pour utiliser les modèles d'embedding OpenAI."
            )
        try:
            client = OpenAI() # Initialisation du client OpenAI
            response = client.embeddings.create(
                input=text_chunks,
                model=embedding_model_name
            )
            # Extraction des embeddings de la réponse de l'API
            embeddings = [item.embedding for item in response.data]
            return embeddings
        except APIError as e:
            logger.error(f"Erreur de l'API OpenAI lors de la génération des embeddings avec le modèle {embedding_model_name}: {e}")
            # Relance l'exception APIError pour que l'appelant puisse la gérer spécifiquement.
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la génération des embeddings OpenAI avec le modèle {embedding_model_name}: {e}")
            # Relance une exception générique pour les autres erreurs.
            raise
    else:
        # Supposition : les autres modèles sont des Sentence Transformers.
        # Ce bloc gère la génération d'embeddings en utilisant la bibliothèque sentence-transformers.
        if SentenceTransformer is None:
            # Commentaire : Vérification similaire à celle d'OpenAI pour sentence-transformers.
            raise ImportError(
                f"La bibliothèque 'sentence-transformers' est requise pour le modèle '{embedding_model_name}' "
                "mais n'a pas pu être importée. Veuillez l'installer."
            )
        try:
            logger.info(f"Chargement du modèle Sentence Transformer: {embedding_model_name}")
            model = SentenceTransformer(embedding_model_name) # Chargement du modèle
            logger.info(f"Génération des embeddings avec {embedding_model_name} pour {len(text_chunks)} morceaux.")
            embeddings_np = model.encode(text_chunks) # Génération des embeddings (typiquement un ndarray NumPy)
            
            # Conversion en liste de listes de flottants Python standard
            # Commentaire : Assure un format de sortie cohérent, quel que soit le type de retour de model.encode().
            if hasattr(embeddings_np, 'tolist'):
                embeddings = embeddings_np.tolist() # Méthode standard pour les arrays NumPy
            else:
                # Cas de repli si embeddings_np n'est pas un array NumPy (par exemple, déjà une liste de listes)
                embeddings = [list(map(float, emb)) for emb in embeddings_np]
            logger.info("Embeddings générés avec succès.")
            return embeddings
        except OSError as e:
            # Commentaire : OSError peut survenir si le modèle n'est pas trouvé localement
            # et que le téléchargement échoue (problème de réseau, nom de modèle incorrect).
            logger.error(f"Erreur lors du chargement du modèle Sentence Transformer '{embedding_model_name}': {e}")
            raise ValueError(f"Impossible de charger le modèle Sentence Transformer '{embedding_model_name}'. Vérifiez le nom du modèle et votre connexion internet. Erreur: {e}")
        except RuntimeError as e:
            logger.error(f"Erreur d'exécution lors de la génération des embeddings avec Sentence Transformer '{embedding_model_name}': {e}")
            raise RuntimeError(f"Erreur d'exécution avec Sentence Transformer '{embedding_model_name}': {e}")
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la génération des embeddings avec Sentence Transformer '{embedding_model_name}': {e}")
            # Encapsule l'exception originale dans un ValueError pour plus de contexte.
            raise ValueError(f"Erreur inattendue avec Sentence Transformer '{embedding_model_name}': {e}")
def save_embeddings_data(embeddings_data: Dict[str, Any], output_path: Path) -> bool:
    """
    Sauvegarde les données d'embeddings dans un fichier JSON.

    Les données peuvent inclure les embeddings eux-mêmes, les morceaux de texte
    originaux, et d'autres métadonnées pertinentes.

    :param embeddings_data: Un dictionnaire contenant les données d'embeddings.
                            La structure attendue est flexible mais devrait contenir
                            au moins une clé pour les embeddings.
    :type embeddings_data: Dict[str, Any]
    :param output_path: Le chemin (objet Path) du fichier où sauvegarder les données.
                        Le répertoire parent sera créé s'il n'existe pas.
    :type output_path: Path

    :return: True si la sauvegarde a réussi, False sinon.
    :rtype: bool

    :raises IOError: Si une erreur d'entrée/sortie se produit pendant l'écriture du fichier.
                     (Note: la fonction actuelle capture IOError et retourne False,
                      mais pour la conformité PEP 257, on le mentionne ici).
    :raises Exception: Pour d'autres erreurs inattendues pendant la sauvegarde.
                       (Note: la fonction actuelle capture Exception et retourne False).
    """
    logger.info(f"Tentative de sauvegarde des données d'embeddings vers {output_path}")
    try:
        # S'assurer que le répertoire parent existe
        # Commentaire : S'assure que le répertoire de destination existe avant d'écrire le fichier.
        # L'option `parents=True` crée les répertoires parents nécessaires.
        # `exist_ok=True` évite une erreur si le répertoire existe déjà.
        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Répertoire parent {output_path.parent} pour la sauvegarde vérifié/créé.")

        with open(output_path, 'w', encoding='utf-8') as f:
            # Commentaire : Utilisation de json.dump pour sérialiser le dictionnaire en JSON.
            # `ensure_ascii=False` permet de sauvegarder correctement les caractères non-ASCII.
            # `indent=4` formate le JSON pour une meilleure lisibilité.
            json.dump(embeddings_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"✅ Données d'embeddings sauvegardées avec succès dans {output_path}")
        return True
    except IOError as e: # Gestion spécifique des erreurs d'entrée/sortie
        logger.error(f"❌ Erreur d'E/S lors de la sauvegarde des embeddings dans {output_path}: {e}", exc_info=True)
        return False
    except Exception as e: # Gestion des autres erreurs potentielles
        logger.error(f"❌ Erreur inattendue lors de la sauvegarde des embeddings dans {output_path}: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    # Exemple d'utilisation (nécessite une clé API OpenAI configurée)
    # Pour tester, décommentez et assurez-vous que votre clé OPENAI_API_KEY est définie.
    # logging.basicConfig(level=logging.INFO)
    # try:
    #     sample_chunks = [
    #         "Ceci est le premier morceau de texte.",
    #         "Voici un autre exemple de texte pour l'embedding.",
    #         "Les modèles d'intelligence artificielle transforment le monde."
    #     ]
    #     model_name = "text-embedding-3-small" # ou "text-embedding-ada-002"
    #     
    #     print(f"Génération des embeddings pour {len(sample_chunks)} morceaux avec le modèle {model_name}...")
    #     embeddings_result = get_embeddings_for_chunks(sample_chunks, model_name)
    #     
    #     print(f"Embeddings générés avec succès ({len(embeddings_result)} embeddings).")
    #     for i, emb in enumerate(embeddings_result):
    #         print(f"  Embedding {i+1} (longueur: {len(emb)}): {emb[:5]}... (premiers 5 éléments)")
    #
    # except NotImplementedError as e:
    #     logger.error(f"Erreur d'implémentation: {e}")
    # except APIError as e:
    #     logger.error(f"Erreur API OpenAI: {e}. Assurez-vous que votre clé API est correcte et que le modèle est accessible.")
    # except Exception as e:
    #     logger.error(f"Une erreur inattendue est survenue: {e}")
    pass