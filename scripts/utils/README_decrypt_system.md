<<<<<<< MAIN
# Système de Déchiffrement et Listage Sécurisé d'Extraits

## Vue d'ensemble

Ce système permet l'extraction programmatique sécurisée des métadonnées d'extraits du corpus chiffré, sans compromettre la sécurité du contenu. Il a été développé pour permettre une sélection spécifique d'extraits pour analyse tout en respectant les contraintes de confidentialité.

## Composants du Système

### 1. `list_encrypted_extracts.py` - Lister Sécurisé
**Objectif** : Extraire programmatiquement les identifiants et métadonnées des extraits sans accéder au contenu textuel.

**Fonctionnalités** :
- Déchiffrement temporaire du corpus
- Extraction SEULEMENT des métadonnées (identifiants, noms, marqueurs, longueurs)
- Affichage formaté pour sélection
- Sauvegarde JSON optionnelle
- Nettoyage automatique après extraction

**Usage** :
```bash
# Liste basique
python scripts/utils/list_encrypted_extracts.py

# Liste détaillée
python scripts/utils/list_encrypted_extracts.py --detailed

# Sauvegarde JSON
python scripts/utils/list_encrypted_extracts.py --json-output metadata.json
```

### 2. `decrypt_specific_extract.py` - Déchiffrement Ciblé
**Objectif** : Déchiffrer et analyser un extrait spécifique identifié.

**Fonctionnalités** :
- Sélection par ID (`0_1`) ou nom d'extrait
- Affichage des métadonnées complètes
- Accès contrôlé au contenu textuel
- Option pour masquer le contenu (métadonnées seulement)
- Sauvegarde JSON des informations

**Usage** :
```bash
# Par ID (métadonnées seulement)
python scripts/utils/decrypt_specific_extract.py --extract-id "0_1" --no-content

# Par nom (avec contenu)
python scripts/utils/decrypt_specific_extract.py --extract-name "Rhétorique de l'urgence climatique"
```

### 3. `create_test_encrypted_extracts.py` - Création de Corpus de Test
**Objectif** : Générer un corpus chiffré de test pour validation du système.

**Fonctionnalités** :
- Génération d'extraits d'exemple réalistes mais non sensibles
- Chiffrement selon les mêmes méthodes que le système de production
- Sauvegarde automatique de l'ancien fichier
- Structure conforme au format attendu

**Usage** :
```bash
python scripts/utils/create_test_encrypted_extracts.py --passphrase "Propaganda"
```

### 4. `cleanup_decrypt_traces.py` - Nettoyage Sécurisé
**Objectif** : Nettoyer automatiquement les traces des opérations de déchiffrement.

**Fonctionnalités** :
- Suppression des fichiers temporaires
- Nettoyage sécurisé de la mémoire
- Logging des opérations de nettoyage

## Structure du Corpus de Test

Le corpus de test généré contient :

### Sources (3 au total) :
1. **Débat présidentiel - Climat** (`political_debate`)
   - `0_0` : Argumentation sur la transition énergétique
   - `0_1` : Rhétorique de l'urgence climatique

2. **Discours économique - Inflation** (`political_speech`)
   - `1_0` : Analyse des causes de l'inflation
   - `1_1` : Accusation contre l'opposition

3. **Débat santé publique** (`parliamentary_debate`)
   - `2_0` : Réforme du système de santé
   - `2_1` : Attaque ad hominem sur la santé

### Métadonnées disponibles :
- **Source** : index, nom, type, schéma, chemin
- **Extrait** : ID, nom, marqueurs début/fin, longueur
- **Métadonnées additionnelles** : orateur, sujet, date, durée

## Sécurité et Confidentialité

### Mesures de Sécurité Implémentées :
1. **Accès aux métadonnées seulement** par défaut
2. **Déchiffrement temporaire** avec nettoyage immédiat
3. **Anonymisation des logs** sensibles
4. **Passphrase requise** pour toute opération
5. **Nettoyage automatique** des traces

### Bonnes Pratiques :
- Utiliser `--no-content` pour éviter l'exposition du contenu textuel
- Nettoyer régulièrement avec `cleanup_decrypt_traces.py`
- Limiter l'accès aux passphrases
- Éviter la sauvegarde non chiffrée des contenus textuels

## Tests de Validation

### Tests Réalisés et Validés :
✅ **Déchiffrement fonctionnel** avec passphrase "Propaganda"  
✅ **Extraction des métadonnées** (3 sources, 6 extraits)  
✅ **Listage sécurisé** sans exposition du contenu  
✅ **Sélection ciblée** par ID et nom  
✅ **Affichage formaté** pour sélection utilisateur  
✅ **Sauvegarde JSON** des métadonnées  
✅ **Nettoyage automatique** des traces temporaires  

### Exemple de Sortie de Listage :
```
LISTE DES EXTRAITS DISPONIBLES DANS LE CORPUS CHIFFRÉ
================================================================================

RÉSUMÉ:
- Sources totales: 3
- Extraits totaux: 6

SOURCES ET EXTRAITS:
------------------------------------------------------------

[SOURCE 0] Débat présidentiel - Climat
   Type: text, Schema: political_debate
   Extraits: 2
   IDs: 0_0, 0_1

[SOURCE 1] Discours économique - Inflation
   Type: text, Schema: political_speech
   Extraits: 2
   IDs: 1_0, 1_1

[SOURCE 2] Débat santé publique
   Type: text, Schema: parliamentary_debate
   Extraits: 2
   IDs: 2_0, 2_1

INSTRUCTIONS POUR SÉLECTION SPÉCIFIQUE:
- Utilisez l'ID d'extrait (ex: '0_1') pour sélectionner un extrait spécifique
- Ou utilisez le nom de l'extrait pour une sélection par nom
```

## Intégration avec le Système Existant

### Compatibilité :
- **Compatible** avec `SourceManager` existant
- **Utilise** les mêmes utilitaires de chiffrement (`crypto_utils`)
- **Respecte** la structure de données d'`ExtractDefinitions`
- **Suit** les chemins définis dans `argumentation_analysis.paths`

### Variables d'Environnement :
- `TEXT_CONFIG_PASSPHRASE` : Phrase secrète pour le déchiffrement

## Conclusion

Le système de déchiffrement et listage sécurisé d'extraits est opérationnel et permet :

1. **L'extraction programmatique** des identifiants d'extraits sans compromettre la sécurité
2. **La sélection spécifique** d'extraits pour analyse ciblée
3. **Le respect de la confidentialité** avec accès contrôlé au contenu
4. **La validation complète** du système de déchiffrement

Le système est prêt pour utilisation avec un corpus réel, en respectant toutes les contraintes de sécurité énoncées.

=======
# Système de Déchiffrement et Listage Sécurisé d'Extraits

## Vue d'ensemble

Ce système permet l'extraction programmatique sécurisée des métadonnées d'extraits du corpus chiffré, sans compromettre la sécurité du contenu. Il a été développé pour permettre une sélection spécifique d'extraits pour analyse tout en respectant les contraintes de confidentialité.

## Composants du Système

### 1. `list_encrypted_extracts.py` - Lister Sécurisé
**Objectif** : Extraire programmatiquement les identifiants et métadonnées des extraits sans accéder au contenu textuel.

**Fonctionnalités** :
- Déchiffrement temporaire du corpus
- Extraction SEULEMENT des métadonnées (identifiants, noms, marqueurs, longueurs)
- Affichage formaté pour sélection
- Sauvegarde JSON optionnelle
- Nettoyage automatique après extraction

**Usage** :
```bash
# Liste basique
python scripts/utils/list_encrypted_extracts.py

# Liste détaillée
python scripts/utils/list_encrypted_extracts.py --detailed

# Sauvegarde JSON
python scripts/utils/list_encrypted_extracts.py --json-output metadata.json
```

### 2. `decrypt_specific_extract.py` - Déchiffrement Ciblé
**Objectif** : Déchiffrer et analyser un extrait spécifique identifié.

**Fonctionnalités** :
- Sélection par ID (`0_1`) ou nom d'extrait
- Affichage des métadonnées complètes
- Accès contrôlé au contenu textuel
- Option pour masquer le contenu (métadonnées seulement)
- Sauvegarde JSON des informations

**Usage** :
```bash
# Par ID (métadonnées seulement)
python scripts/utils/decrypt_specific_extract.py --extract-id "0_1" --no-content

# Par nom (avec contenu)
python scripts/utils/decrypt_specific_extract.py --extract-name "Rhétorique de l'urgence climatique"
```

### 3. `create_test_encrypted_extracts.py` - Création de Corpus de Test
**Objectif** : Générer un corpus chiffré de test pour validation du système.

**Fonctionnalités** :
- Génération d'extraits d'exemple réalistes mais non sensibles
- Chiffrement selon les mêmes méthodes que le système de production
- Sauvegarde automatique de l'ancien fichier
- Structure conforme au format attendu

**Usage** :
```bash
python scripts/utils/create_test_encrypted_extracts.py --passphrase "Propaganda"
```

### 4. `cleanup_decrypt_traces.py` - Nettoyage Sécurisé
**Objectif** : Nettoyer automatiquement les traces des opérations de déchiffrement.

**Fonctionnalités** :
- Suppression des fichiers temporaires
- Nettoyage sécurisé de la mémoire
- Logging des opérations de nettoyage

## Structure du Corpus de Test

Le corpus de test généré contient :

### Sources (3 au total) :
1. **Débat présidentiel - Climat** (`political_debate`)
   - `0_0` : Argumentation sur la transition énergétique
   - `0_1` : Rhétorique de l'urgence climatique

2. **Discours économique - Inflation** (`political_speech`)
   - `1_0` : Analyse des causes de l'inflation
   - `1_1` : Accusation contre l'opposition

3. **Débat santé publique** (`parliamentary_debate`)
   - `2_0` : Réforme du système de santé
   - `2_1` : Attaque ad hominem sur la santé

### Métadonnées disponibles :
- **Source** : index, nom, type, schéma, chemin
- **Extrait** : ID, nom, marqueurs début/fin, longueur
- **Métadonnées additionnelles** : orateur, sujet, date, durée

## Sécurité et Confidentialité

### Mesures de Sécurité Implémentées :
1. **Accès aux métadonnées seulement** par défaut
2. **Déchiffrement temporaire** avec nettoyage immédiat
3. **Anonymisation des logs** sensibles
4. **Passphrase requise** pour toute opération
5. **Nettoyage automatique** des traces

### Bonnes Pratiques :
- Utiliser `--no-content` pour éviter l'exposition du contenu textuel
- Nettoyer régulièrement avec `cleanup_decrypt_traces.py`
- Limiter l'accès aux passphrases
- Éviter la sauvegarde non chiffrée des contenus textuels

## Tests de Validation

### Tests Réalisés et Validés :
✅ **Déchiffrement fonctionnel** avec passphrase "Propaganda"  
✅ **Extraction des métadonnées** (3 sources, 6 extraits)  
✅ **Listage sécurisé** sans exposition du contenu  
✅ **Sélection ciblée** par ID et nom  
✅ **Affichage formaté** pour sélection utilisateur  
✅ **Sauvegarde JSON** des métadonnées  
✅ **Nettoyage automatique** des traces temporaires  

### Exemple de Sortie de Listage :
```
LISTE DES EXTRAITS DISPONIBLES DANS LE CORPUS CHIFFRÉ
================================================================================

RÉSUMÉ:
- Sources totales: 3
- Extraits totaux: 6

SOURCES ET EXTRAITS:
------------------------------------------------------------

[SOURCE 0] Débat présidentiel - Climat
   Type: text, Schema: political_debate
   Extraits: 2
   IDs: 0_0, 0_1

[SOURCE 1] Discours économique - Inflation
   Type: text, Schema: political_speech
   Extraits: 2
   IDs: 1_0, 1_1

[SOURCE 2] Débat santé publique
   Type: text, Schema: parliamentary_debate
   Extraits: 2
   IDs: 2_0, 2_1

INSTRUCTIONS POUR SÉLECTION SPÉCIFIQUE:
- Utilisez l'ID d'extrait (ex: '0_1') pour sélectionner un extrait spécifique
- Ou utilisez le nom de l'extrait pour une sélection par nom
```

## Intégration avec le Système Existant

### Compatibilité :
- **Compatible** avec `SourceManager` existant
- **Utilise** les mêmes utilitaires de chiffrement (`crypto_utils`)
- **Respecte** la structure de données d'`ExtractDefinitions`
- **Suit** les chemins définis dans `argumentation_analysis.paths`

### Variables d'Environnement :
- `TEXT_CONFIG_PASSPHRASE` : Phrase secrète pour le déchiffrement

## Conclusion

Le système de déchiffrement et listage sécurisé d'extraits est opérationnel et permet :

1. **L'extraction programmatique** des identifiants d'extraits sans compromettre la sécurité
2. **La sélection spécifique** d'extraits pour analyse ciblée
3. **Le respect de la confidentialité** avec accès contrôlé au contenu
4. **La validation complète** du système de déchiffrement

Le système est prêt pour utilisation avec un corpus réel, en respectant toutes les contraintes de sécurité énoncées.
>>>>>>> BACKUP
