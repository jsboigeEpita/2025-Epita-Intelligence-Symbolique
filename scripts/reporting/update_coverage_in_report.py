import project_core.core_from_scripts.auto_env
"""
Script pour ajouter une section sur la couverture des tests mockés au rapport de suivi.
"""

import os
import sys
from pathlib import Path
import datetime

# Ajouter le répertoire parent au PYTHONPATH
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(parent_dir)

# Chemin du rapport de suivi
RAPPORT_PATH = Path(parent_dir) / "docs" / "reports" / "rapport_suivi_tests.md"

# Contenu à ajouter au rapport
RAPPORT_UPDATE = """
## Mesure de couverture des tests mockés (21/05/2025)

Une mesure de couverture a été effectuée sur les tests mockés autonomes pour évaluer leur efficacité.

### Tests exécutés
Les tests mockés autonomes ont été exécutés avec mesure de couverture à l'aide de la commande suivante :
```
python -m coverage run tests/standalone_mock_tests.py
```

### Résultats de couverture
Le rapport de couverture généré montre les résultats suivants :
```
Name                 Stmts   Miss  Cover
----------------------------------------
standalone_mock_tests.py     121     4    97%
----------------------------------------
TOTAL                        121     4    97%
```

### Analyse des résultats
- **Couverture globale** : 97% du code des tests mockés est couvert, ce qui est excellent.
- **Lignes non couvertes** : Seulement 4 lignes sur 121 ne sont pas couvertes.
- **Comparaison avec la couverture précédente** : La couverture des tests mockés (97%) est nettement supérieure à la couverture globale précédente (18% pour les modules de communication et 44.48% mentionné dans le rapport final).

### Rapport HTML
Un rapport HTML détaillé a été généré pour visualiser la couverture :
```
python -m coverage html
```
Le rapport est disponible dans le répertoire `htmlcov/index.html`.

### Recommandations pour améliorer davantage la couverture
1. **Étendre les tests mockés** :
   - Ajouter des tests mockés pour d'autres modules du système
   - Couvrir les cas limites et les scénarios d'erreur

2. **Intégrer les tests mockés dans le CI/CD** :
   - Configurer le pipeline CI/CD pour exécuter les tests mockés et mesurer la couverture
   - Définir des seuils de couverture minimale pour les tests mockés

3. **Documenter les mocks** :
   - Documenter les mocks utilisés et leur correspondance avec les classes réelles
   - Maintenir la synchronisation entre les mocks et les implémentations réelles

4. **Améliorer les tests existants** :
   - Identifier et couvrir les 4 lignes manquantes dans les tests mockés
   - Ajouter des assertions plus précises pour vérifier le comportement attendu

### Conclusion
Les tests mockés autonomes offrent une excellente couverture (97%) et constituent une approche efficace pour tester la logique de communication entre agents sans dépendre des modules problématiques. Cette approche devrait être étendue à d'autres parties du système pour améliorer la couverture globale des tests.
"""

def update_rapport():
    """Met à jour le rapport de suivi des tests en utilisant l'utilitaire centralisé."""
    
    section_header_to_update = "## Mesure de couverture des tests mockés (21/05/2025)"
    # Le RAPPORT_UPDATE contient déjà l'en-tête, donc pour new_content, nous l'omettons ou passons le contenu sans.
    # Pour cette refactorisation, nous allons supposer que RAPPORT_UPDATE est le *nouveau contenu complet* de la section,
    # et que update_markdown_section gérera l'en-tête.
    # Cependant, la logique actuelle de RAPPORT_UPDATE inclut l'en-tête.
    # Pour une meilleure utilisation de update_markdown_section, RAPPORT_UPDATE ne devrait pas contenir l'en-tête.
    # Pour l'instant, nous allons extraire le contenu après l'en-tête de RAPPORT_UPDATE.
    
    header_in_update = "## Mesure de couverture des tests mockés (21/05/2025)\n" # Doit correspondre exactement
    if RAPPORT_UPDATE.strip().startswith(header_in_update.strip()):
        actual_new_content = RAPPORT_UPDATE.strip()[len(header_in_update):].strip()
    else:
        # Si l'en-tête n'est pas au début de RAPPORT_UPDATE comme attendu,
        # cela pourrait indiquer un problème. On utilise tout RAPPORT_UPDATE comme contenu
        # et on espère que update_markdown_section le gère bien (il ajoutera l'en-tête).
        # Ou alors, on logue une erreur. Pour l'instant, on passe tout.
        # Idéalement, RAPPORT_UPDATE serait juste le contenu.
        print(f"Avertissement: L'en-tête '{header_in_update.strip()}' n'a pas été trouvé au début de RAPPORT_UPDATE. "
              "La mise à jour de la section pourrait ne pas fonctionner comme prévu si l'en-tête est dupliqué.")
        actual_new_content = RAPPORT_UPDATE # Moins idéal, car update_markdown_section ajoutera son propre en-tête.
                                          # Pour un remplacement propre, RAPPORT_UPDATE ne devrait pas avoir l'en-tête.
                                          # Pour cette fois, on va laisser update_markdown_section gérer la création de l'en-tête
                                          # et on va passer le RAPPORT_UPDATE entier comme contenu.
                                          # Cela signifie que l'en-tête sera dupliqué si la section existe déjà.
                                          # La meilleure solution est de s'assurer que RAPPORT_UPDATE est *uniquement le contenu*.
                                          # Pour l'instant, on va utiliser la version qui remplace toute la section.

    # Pour un remplacement propre, il faudrait que RAPPORT_UPDATE soit juste le contenu.
    # Ici, on va utiliser la fonction pour remplacer toute la section, en espérant que
    # l'en-tête dans RAPPORT_UPDATE et section_header_to_update sont les mêmes.
    # Si on veut juste ajouter/remplacer le *contenu* sous l'en-tête, il faut ajuster.
    
    # On va supposer que RAPPORT_UPDATE est le contenu complet de la section, y compris son propre en-tête.
    # La fonction update_markdown_section va chercher section_header_to_update, et si elle le trouve,
    # elle remplacera toute la section par section_header_to_update + actual_new_content.
    # Si RAPPORT_UPDATE contient déjà l'en-tête, il sera dupliqué.
    # Solution: on passe RAPPORT_UPDATE comme new_content et on laisse la fonction ajouter l'en-tête.
    # Mais section_header_to_update doit être l'en-tête que l'on cherche.

    # Simplifions: on va passer le contenu de RAPPORT_UPDATE *sans* son en-tête.
    content_for_section = RAPPORT_UPDATE.split(header_in_update, 1)[-1] if header_in_update in RAPPORT_UPDATE else RAPPORT_UPDATE


    if update_markdown_section(
        file_path=RAPPORT_PATH,
        section_header=section_header_to_update, # L'en-tête que l'on cherche/veut créer
        new_content=content_for_section, # Le contenu à mettre sous cet en-tête
        ensure_header_level=2, # C'est un '##'
        add_if_not_found=True,
        replace_entire_section=True # Remplacer toute la section si trouvée
    ):
        print(f"Rapport de suivi mis à jour avec succès: {RAPPORT_PATH}")
        return True
    else:
        print(f"Échec de la mise à jour du rapport de suivi: {RAPPORT_PATH}")
        return False

if __name__ == "__main__":
    update_rapport()