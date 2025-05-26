# Documentation : Logique des Définitions par Défaut

## Vue d'ensemble

La fonction `load_extract_definitions()` dans `argumentation_analysis/ui/file_operations.py` implémente une logique de fallback robuste qui garantit que l'application dispose toujours de définitions d'extraction valides, même en cas d'erreur.

## Principe de Conception

**Philosophie** : L'application doit toujours pouvoir fonctionner, même si les fichiers de configuration sont corrompus, manquants, ou inaccessibles.

**Approche** : Retourner systématiquement des définitions par défaut plutôt que `None` en cas d'erreur.

## Cas de Fallback

La fonction retourne des définitions par défaut dans les cas suivants :

### 1. Fichier de Configuration Inexistant
```python
if not config_file.exists():
    file_ops_logger.info(f"Fichier config chiffré '{config_file}' non trouvé. Utilisation définitions par défaut.")
    return [item.copy() for item in fallback_definitions]
```

### 2. Clé de Chiffrement Manquante
```python
if not key:
    file_ops_logger.warning("Clé chiffrement absente. Chargement config impossible. Utilisation définitions par défaut.")
    return [item.copy() for item in fallback_definitions]
```

### 3. Échec du Déchiffrement
```python
if not decrypted_compressed_data:
    file_ops_logger.warning("Échec déchiffrement. Utilisation définitions par défaut.")
    return [item.copy() for item in fallback_definitions]
```

### 4. Format de Données Invalide
```python
if not isinstance(definitions, list) or not all(...):
    file_ops_logger.warning("⚠️ Format définitions invalide après chargement. Utilisation définitions par défaut.")
    return [item.copy() for item in fallback_definitions]
```

### 5. Erreurs d'Exception (JSON malformé, corruption, etc.)
```python
except Exception as e:
    file_ops_logger.error(f"❌ Erreur chargement/traitement '{config_file}': {e}. Utilisation définitions par défaut.", exc_info=True)
    return [item.copy() for item in fallback_definitions]
```

## Définitions par Défaut

Les définitions par défaut sont définies dans `argumentation_analysis/ui/config.py` :

```python
fallback_definitions = ui_config_module.EXTRACT_SOURCES if ui_config_module.EXTRACT_SOURCES else ui_config_module.DEFAULT_EXTRACT_SOURCES
```

Structure type :
```python
[{
    'source_name': 'Exemple Vide (Config manquante)',
    'source_type': 'jina',
    'schema': 'https:',
    'host_parts': ['example', 'com'],
    'path': '/',
    'extracts': []
}]
```

## Avantages de cette Approche

### 1. **Robustesse**
- L'application ne plante jamais à cause de fichiers de configuration corrompus
- Dégradation gracieuse en cas d'erreur

### 2. **Expérience Utilisateur**
- L'utilisateur peut toujours utiliser l'application
- Messages d'erreur informatifs dans les logs
- Possibilité de reconfigurer sans redémarrage

### 3. **Maintenance**
- Comportement prévisible et cohérent
- Tests plus simples à écrire et maintenir
- Debugging facilité par les logs détaillés

## Tests Associés

Les tests dans `tests/test_load_extract_definitions.py` valident cette logique :

- `test_load_definitions_no_file` : Fichier inexistant → définitions par défaut
- `test_load_definitions_encrypted_no_key` : Clé manquante → définitions par défaut  
- `test_load_definitions_encrypted_wrong_key` : Mauvaise clé → définitions par défaut
- `test_load_default_if_path_none` : Path invalide → définitions par défaut
- `test_load_malformed_json` : JSON corrompu → définitions par défaut

## Logging et Monitoring

Chaque cas de fallback est loggé avec le niveau approprié :
- `INFO` : Situations normales (fichier manquant)
- `WARNING` : Situations problématiques mais gérables (clé manquante, déchiffrement échoué)
- `ERROR` : Erreurs inattendues (exceptions, corruption)

## Évolutions Futures

Cette logique pourrait être étendue pour :
- Sauvegarder automatiquement une configuration par défaut
- Notifier l'utilisateur des problèmes de configuration
- Proposer une interface de récupération/réparation

## Conclusion

Cette approche garantit la stabilité et la fiabilité de l'application tout en fournissant une expérience utilisateur cohérente, même en cas de problèmes de configuration.