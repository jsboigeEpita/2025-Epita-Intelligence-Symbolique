# Système d'Encryption avec Sources Embarquées

Ce document explique le système d'encryption révisé qui permet d'embarquer les sources avec la configuration des extraits. L'objectif est de pouvoir archiver sur GitHub un fichier encrypté complet et supprimer les autres fichiers non nécessaires.

## Fichiers Créés

### Scripts Principaux

1. `create_complete_encrypted_config.py` - Crée un fichier encrypté complet qui embarque les sources avec la configuration des extraits.
2. `load_complete_encrypted_config.py` - Charge le fichier encrypté complet et restaure les fichiers de cache.
3. `cleanup_after_encryption.py` - Nettoie les fichiers non nécessaires après avoir créé le fichier encrypté complet.
4. `create_and_archive_encrypted_config.py` - Script principal qui orchestre l'ensemble du processus.

### Script de Déploiement

- `deploy_and_run_scripts.ps1` - Script PowerShell pour déployer et exécuter les scripts dans le répertoire parent.

## Processus

Le processus complet se déroule en plusieurs étapes:

1. **Création du fichier de cache du Kremlin** - Déjà fait par l'utilisateur avec `create_kremlin_cache.py`.
2. **Création du fichier encrypté complet** - Le script `create_complete_encrypted_config.py` charge la configuration des extraits depuis `utils/extract_repair/docs/extract_sources_updated.json`, récupère les fichiers de cache correspondants, et crée un fichier encrypté qui inclut à la fois la configuration et les sources.
3. **Vérification du fichier encrypté** - Le script `load_complete_encrypted_config.py` charge le fichier encrypté complet et restaure les fichiers de cache pour vérifier que tout fonctionne correctement.
4. **Nettoyage des fichiers non nécessaires** - Le script `cleanup_after_encryption.py` supprime les fichiers de cache et autres fichiers temporaires qui ne sont plus nécessaires.

## Utilisation

### Option 1: Utiliser le script de déploiement PowerShell

1. Ouvrez PowerShell dans le répertoire `agents`.
2. Exécutez le script `deploy_and_run_scripts.ps1`:
   ```powershell
   .\deploy_and_run_scripts.ps1
   ```
3. Suivez les instructions à l'écran.

### Option 2: Exécuter les scripts manuellement

1. Copiez les scripts du répertoire `agents` vers le répertoire parent `argumentiation_analysis`.
2. Exécutez le script principal depuis le répertoire parent:
   ```bash
   cd ..
   python create_and_archive_encrypted_config.py
   ```

## Structure du Fichier Encrypté

Le fichier encrypté complet (`data/extract_sources.json.gz.enc`) contient:

1. **Configuration des extraits** - La liste des sources et des extraits à extraire de chaque source.
2. **Contenu des sources** - Le contenu textuel de chaque source, indexé par le hash SHA-256 de l'URL.

Le fichier est compressé avec gzip et chiffré avec Fernet (cryptographie symétrique) en utilisant une clé dérivée d'une phrase secrète stockée dans la variable d'environnement `TEXT_CONFIG_PASSPHRASE`.

## Restauration

Pour restaurer les fichiers de cache à partir du fichier encrypté complet:

1. Assurez-vous que la variable d'environnement `TEXT_CONFIG_PASSPHRASE` est définie avec la bonne phrase secrète.
2. Exécutez le script `load_complete_encrypted_config.py` depuis le répertoire parent:
   ```bash
   cd ..
   python load_complete_encrypted_config.py
   ```

Cela déchiffrera le fichier encrypté, extraira la configuration et les sources, et restaurera les fichiers de cache.

## Remarques

- Assurez-vous que la variable d'environnement `TEXT_CONFIG_PASSPHRASE` est définie avant d'exécuter les scripts.
- Le fichier encrypté complet est stocké dans `data/extract_sources.json.gz.enc`.
- Les fichiers de cache sont stockés dans le répertoire `text_cache/` avec des noms de fichiers basés sur le hash SHA-256 des URLs.
