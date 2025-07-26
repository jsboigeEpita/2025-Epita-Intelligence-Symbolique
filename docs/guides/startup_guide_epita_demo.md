# Guide de Démarrage : Démo EPITA

Ce guide fournit les instructions précises pour exécuter la démonstration pédagogique "Démo EPITA", après sa stabilisation et sa validation.

## 1. Pré-requis : Configuration de l'environnement

Pour fonctionner en mode "authentique" (avec de vrais appels aux modèles de langage), le script nécessite une clé API OpenAI.

1.  Créez un fichier `.env` à la racine du projet.
2.  Ajoutez la ligne suivante dans ce fichier en remplaçant `VOTRE_CLE_API` par votre clé personnelle :
    ```
    OPENAI_API_KEY="VOTRE_CLE_API"
    ```

## 2. Commande d'Exécution Standard (Mode Authentique)

Pour lancer la démonstration, il est impératif d'utiliser le script wrapper `activate_project_env.ps1`. Ce script garantit que l'environnement Conda `projet-is` est activé et que les modules du projet sont correctement chargés.

Exécutez la commande suivante depuis la racine du projet :

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\activate_project_env.ps1 -CommandToRun "python -m scripts.apps.demos.validation_point3_demo_epita_dynamique"
```

### Explication :
- Cette commande utilise le mode "authentique" par défaut, en se connectant à l'API OpenAI via la clé fournie dans le fichier `.env`.
- L'option `python -m` est cruciale car elle exécute le script en tant que module, ce qui résout les problèmes d'importation.

## 3. Alternative : Exécution en Mode Mock

Si vous n'avez pas de clé API ou si vous souhaitez effectuer un test rapide sans utiliser de services externes, vous pouvez utiliser le mode mock.

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\activate_project_env.ps1 -CommandToRun "python -m scripts.apps.demos.validation_point3_demo_epita_dynamique --mock"
```

### Explication :
- L'argument `--mock` active des services LLM simulés, ce qui permet au script de s'exécuter sans nécessiter de connexion internet ou de clé API.

## 4. Fichiers de Sortie

L'exécution du script génère plusieurs fichiers dans les répertoires suivants :
- **`logs/`** : Contient les logs détaillés de l'exécution et la session complète au format JSON.
- **`scripts/reports/`** : Contient le rapport de validation au format Markdown (`validation_point3_demo_epita.md`), qui résume les résultats de la session.