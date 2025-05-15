# 🔄 Réparation des Bornes d'Extraits (`utils/extract_repair/`)

Ce module fournit des outils pour la réparation automatique des bornes défectueuses dans les extraits de texte utilisés pour l'analyse rhétorique.

[Retour au README Utils](../README.md) | [Retour au README Principal](../../README.md)

## Point d'entrée pour instance VSCode dédiée

Ce README sert de point d'entrée pour une instance VSCode dédiée au développement et à la maintenance de l'outil de réparation des bornes d'extraits. Cette approche multi-instance permet de travailler spécifiquement sur cet outil sans avoir à gérer l'ensemble du projet.

## Objectif 🎯

L'outil de réparation des bornes d'extraits permet de:
1. Détecter les bornes défectueuses dans les extraits de texte
2. Proposer des corrections automatiques pour ces bornes
3. Appliquer les corrections et sauvegarder les extraits réparés
4. Générer des rapports détaillés sur les réparations effectuées

Cet outil est essentiel pour maintenir la qualité des extraits utilisés dans l'analyse rhétorique, en s'assurant que les bornes sont correctement définies et correspondent au texte source.

## Contenu 📁

### Scripts de réparation
* **[`repair_extract_markers.py`](./repair_extract_markers.py)** : Script principal pour la réparation automatique des bornes.
* **[`repair_extract_markers.ipynb`](./repair_extract_markers.ipynb)** : Notebook interactif pour la réparation des bornes.
* **[`fix_missing_first_letter.py`](./fix_missing_first_letter.py)** : Script spécifique pour corriger le problème de première lettre manquante dans les extraits.

### Scripts de vérification
* **[`verify_extracts.py`](./verify_extracts.py)** : Script pour vérifier la validité des extraits de texte.
* **[`verify_extracts_with_llm.py`](./verify_extracts_with_llm.py)** : Utilise un LLM pour vérifier la pertinence des extraits.

### Documentation et rapports
* **[`__init__.py`](./__init__.py)** : Marque le dossier comme un package Python.
* **[`docs/`](./docs/)** : Documentation et rapports générés:
  * **[`repair_extract_markers_report.md`](./docs/repair_extract_markers_report.md)** : Documentation détaillée sur la réparation des bornes.
  * **[`repair_report.html`](./docs/repair_report.html)** : Rapport HTML généré par le script de réparation.
  * **[`verify_extracts_report.html`](./docs/verify_extracts_report.html)** : Rapport HTML généré par le script de vérification.
  * **[`extract_sources_updated.json`](./docs/extract_sources_updated.json)** : Version mise à jour des sources d'extraits après réparation.

## Utilisation 🚀

### Via le script de lancement

Le moyen le plus simple d'utiliser l'outil de réparation est d'exécuter le script à la racine du projet:

```bash
python ../../run_extract_repair.py
```

### Options du script de lancement

Le script de réparation accepte plusieurs options en ligne de commande:

```bash
python ../../run_extract_repair.py --output rapport.html --save --hitler-only
```

Options disponibles:
- `--output` ou `-o`: Spécifie le fichier de sortie pour le rapport HTML
- `--save` ou `-s`: Sauvegarde les modifications apportées aux extraits
- `--hitler-only`: Traite uniquement le corpus de discours d'Hitler

### Via le notebook

Vous pouvez également ouvrir directement le notebook interactif:

```bash
jupyter notebook repair_extract_markers.ipynb
```

### Intégration dans d'autres modules

Le module peut être importé et utilisé dans d'autres parties du projet:

```python
import asyncio
from utils.extract_repair.repair_extract_markers import repair_extract_markers

async def run_repair():
    # Charger les définitions d'extraits
    from ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON
    from ui.extract_utils import load_extract_definitions_safely
    from core.llm_service import create_llm_service
    
    extract_definitions, _ = load_extract_definitions_safely(CONFIG_FILE, ENCRYPTION_KEY, CONFIG_FILE_JSON)
    llm_service = create_llm_service()
    
    # Réparer les bornes défectueuses
    updated_definitions, results = await repair_extract_markers(extract_definitions, llm_service)
    
    return updated_definitions, results

# Exécuter la réparation
asyncio.run(run_repair())
```

## Développement de l'outil de réparation

### Création d'un script de test indépendant

Pour tester l'outil de réparation de manière indépendante, vous pouvez créer un script de test dans ce répertoire :

```python
# test_repair.py
import sys
import os
import asyncio
from pathlib import Path

# Ajouter les répertoires parents au chemin de recherche des modules
current_dir = Path(__file__).parent
utils_dir = current_dir.parent
project_dir = utils_dir.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

from dotenv import load_dotenv
load_dotenv(override=True)

# Import des modules nécessaires
from ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON
from ui.extract_utils import load_extract_definitions_safely, save_extract_definitions_safely
from core.llm_service import create_llm_service
from utils.extract_repair.repair_extract_markers import repair_extract_markers, generate_report

async def test_repair():
    """Fonction de test pour l'outil de réparation des bornes"""
    print("Chargement des définitions d'extraits...")
    extract_definitions, error_message = load_extract_definitions_safely(CONFIG_FILE, ENCRYPTION_KEY, CONFIG_FILE_JSON)
    if error_message:
        print(f"Erreur lors du chargement des définitions: {error_message}")
        return
    
    print(f"{len(extract_definitions)} sources chargées.")
    
    # Filtrer pour un test plus rapide (optionnel)
    test_definitions = extract_definitions[:2]  # Prendre seulement les 2 premières sources
    
    # Créer le service LLM
    print("Création du service LLM...")
    llm_service = create_llm_service()
    
    # Réparer les bornes défectueuses
    print("Réparation des bornes défectueuses...")
    updated_definitions, results = await repair_extract_markers(test_definitions, llm_service)
    
    # Générer un rapport
    print("Génération du rapport...")
    generate_report(results, "test_repair_report.html")
    
    print("Test terminé. Rapport généré dans 'test_repair_report.html'")

if __name__ == "__main__":
    asyncio.run(test_repair())
```

Exécutez le test avec :
```bash
python utils/extract_repair/test_repair.py
```

### Développement de nouvelles fonctionnalités

Pour ajouter de nouvelles fonctionnalités à l'outil de réparation, suivez ces étapes :

1. Identifiez clairement la fonctionnalité à ajouter
2. Modifiez le fichier `repair_extract_markers.py` pour implémenter la fonctionnalité
3. Testez la fonctionnalité avec le script de test indépendant
4. Mettez à jour le notebook `repair_extract_markers.ipynb` si nécessaire
5. Documentez la nouvelle fonctionnalité dans ce README et dans le dossier `docs/`

## Développement avec l'approche multi-instance

1. Ouvrez ce répertoire (`utils/extract_repair/`) comme dossier racine dans une instance VSCode dédiée
2. Travaillez sur l'outil de réparation sans être distrait par les autres parties du projet
3. Testez vos modifications avec le script de test indépendant
4. Une fois les modifications validées, intégrez-les dans le projet principal

## Fonctionnalités 🛠️

### Réparation des bornes
- Détection automatique des bornes défectueuses
- Algorithmes de correction intelligents basés sur la correspondance de texte
- Utilisation d'agents IA pour proposer des corrections
- Validation des corrections proposées
- Génération de rapports détaillés sur les réparations effectuées
- Interface utilisateur interactive via notebook Jupyter
- Sauvegarde automatique des extraits réparés
- Traitement spécifique pour le corpus de discours d'Hitler

### Vérification des extraits
- Vérification de la validité syntaxique des extraits
- Vérification de la pertinence sémantique des extraits via LLM
- Détection des extraits incomplets ou tronqués
- Identification des extraits ne correspondant pas à leur dénomination
- Génération de rapports de vérification détaillés
- Suggestions d'amélioration pour les extraits problématiques

### Correction de problèmes spécifiques
- Correction du problème de première lettre manquante
- Détection et correction des problèmes d'encodage
- Ajustement des bornes pour inclure des paragraphes complets
- Normalisation des marqueurs de début et de fin

## Documentation 📚

La documentation détaillée sur le fonctionnement de l'outil de réparation est disponible dans le dossier `docs/`:

- [Documentation sur la réparation des bornes](./docs/repair_extract_markers_report.md)
- [Exemple de rapport de réparation](./docs/repair_report.html)

## Dépendances 📦

- semantic-kernel (pour les agents IA)
- pandas (pour la manipulation des données)
- difflib (pour la comparaison de texte)
- jinja2 (pour la génération de rapports HTML)
- asyncio (pour les opérations asynchrones)
- requests (pour le téléchargement de contenu)
- beautifulsoup4 (pour le parsing HTML, utilisé dans certaines vérifications)
- cryptography (pour le chiffrement/déchiffrement des configurations)

## Bonnes pratiques

- Documentez clairement les algorithmes de réparation
- Testez l'outil avec différents types d'extraits et de bornes
- Générez des rapports détaillés pour chaque réparation
- Utilisez des noms explicites pour les fonctions et les variables
- Gérez correctement les erreurs et les cas limites
- Maintenez une séparation claire entre la logique de réparation et la génération de rapports