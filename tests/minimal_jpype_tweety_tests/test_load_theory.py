import jpype
import jpype.imports
from jpype.types import JString
import os

# Définir le chemin vers les JARs de Tweety (à adapter si nécessaire)
# Cela suppose que les JARs sont dans un sous-répertoire 'libs' du répertoire parent du projet
# ou que le CLASSPATH est déjà configuré.
# Pour cet exemple, nous allons supposer que le CLASSPATH est configuré
# ou que les JARs sont accessibles via les options JVM.

def main():
    try:
        print("Démarrage du test de chargement de théorie...")

        # Démarrer la JVM si ce n'est pas déjà fait
        if not jpype.isJVMStarted():
            # Adaptez le classpath si nécessaire.
            # Exemple: jpype.startJVM(classpath=['path/to/tweety.jar', 'path/to/other.jar'])
            # Pour cet exemple, nous supposons que le CLASSPATH est configuré
            # ou que les JARs sont dans le répertoire de travail ou un chemin connu.
            # Vous devrez peut-être spécifier le chemin vers les JARs de Tweety ici.
            # Par exemple, si les JARs sont dans un dossier 'libs' à la racine du projet:
            # project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            # tweety_libs_path = os.path.join(project_root, "libs", "*") # Chemin vers les JARs
            # jpype.startJVM(classpath=[tweety_libs_path])
            # Pour une configuration plus robuste, utilisez les chemins exacts des JARs.
            # Exemple simplifié, en supposant que les JARs sont trouvables:
            jpype.startJVM(convertStrings=False) # convertStrings=False est souvent recommandé

        # Importer les classes Java nécessaires de Tweety
        # Assurez-vous que les noms de package sont corrects pour votre version de Tweety
        from net.sf.tweety.logics.pl import PlBeliefSet
        from net.sf.tweety.logics.pl.parser import PlParser

        print("JVM démarrée et classes Tweety importées.")

        # Chemin vers le fichier de théorie
        theory_file_path = os.path.join(os.path.dirname(__file__), "sample_theory.lp")
        print(f"Chemin du fichier de théorie : {theory_file_path}")

        if not os.path.exists(theory_file_path):
            raise FileNotFoundError(f"Le fichier de théorie {theory_file_path} n'a pas été trouvé.")

        # Créer un parser et charger la théorie
        parser = PlParser()
        belief_set = PlBeliefSet() # Crée un ensemble de croyances vide

        # La méthode parseBeliefBaseFromFile de PlParser prend un java.io.File
        # Nous devons donc créer un objet File Java
        JFile = jpype.JClass("java.io.File")
        java_file = JFile(JString(theory_file_path))

        # Parse le fichier dans l'ensemble de croyances existant
        # La méthode exacte peut varier selon la version de Tweety et le type de logique.
        # Pour la logique propositionnelle (PlBeliefSet), on peut utiliser `add` après avoir parsé des formules,
        # ou une méthode de parsing direct si disponible.
        # Une approche courante est de parser et d'ajouter.
        # Alternativement, certains parsers peuvent retourner directement un BeliefSet.
        # Ici, nous allons essayer de parser le fichier et d'ajouter à belief_set.
        # PlParser.parseBeliefBaseFromFile retourne un BeliefSet, donc on peut l'assigner directement.
        
        # Tentative de chargement direct
        # Note: La signature exacte peut varier. Vérifiez la documentation de Tweety.
        # Si PlParser().parseBeliefBaseFromFile(java_file) est la bonne méthode:
        parsed_belief_set = parser.parseBeliefBaseFromFile(java_file)
        
        # Copier les formules dans notre belief_set ou utiliser directement parsed_belief_set
        # Pour cet exemple, nous allons considérer que parsed_belief_set est ce que nous voulons.
        belief_set = parsed_belief_set

        print(f"Théorie chargée avec succès. Nombre de formules : {belief_set.size()}")
        # Vous pouvez ajouter d'autres vérifications ici, par exemple, imprimer les formules
        # print("Formules chargées :")
        # for formula in belief_set:
        #     print(f"- {formula.toString()}")

        print("Test de chargement de théorie RÉUSSI.")

    except Exception as e:
        print(f"Test de chargement de théorie ÉCHOUÉ : {e}")
        import traceback
        traceback.print_exc()
        raise # Relancer l'exception pour indiquer l'échec du test

    finally:
        # Optionnel: arrêter la JVM si ce script est le seul utilisateur
        # if jpype.isJVMStarted():
        #     jpype.shutdownJVM()
        #     print("JVM arrêtée.")
        pass # Laisser la JVM active pour d'autres tests potentiels dans la même session

if __name__ == "__main__":
    main()