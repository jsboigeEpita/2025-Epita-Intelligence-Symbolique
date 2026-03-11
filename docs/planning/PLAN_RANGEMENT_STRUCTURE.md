# Plan de Rangement et Amélioration de la Structure

## 🎯 Problèmes Identifiés

### 1. Doublons Massifs de Bibliothèques Tweety
- **32 fichiers JAR dupliqués** entre `libs/` et `libs/tweety/`
- **~600+ MB d'espace disque gaspillé**
- Fichiers identiques (même nom et taille)

### 2. Fichiers Temporaires Non Nettoyés
- `libs/_temp_octave_download/octave-10.1.0-w64.zip` (762 MB)
- `libs/_temp_jdk_download/` (vide mais inutile)
- Répertoires de téléchargement temporaires oubliés

### 3. Structure libs/ Incohérente
- Mélange de fichiers JAR en racine et sous-répertoires organisés
- Duplication des bibliothèques natives entre `libs/native/` et `libs/tweety/native/`
- Structure web_api mal placée dans libs/

### 4. Archives et Migration Non Rangées
- `archives/` contient des scripts PowerShell hérités
- `migration_output/` contient des fichiers de remplacement Python
- Fichiers de sauvegarde temporaires

### 5. Documentation Trop Dispersée
- 79 fichiers dans `docs/` avec structure profonde
- Certains rapports en double ou obsolètes
- Guides utilisateur éparpillés

## 🔧 Actions de Rangement Prioritaires

### Phase 1: Nettoyage des Doublons (CRITIQUE)
1. **Consolidation Tweety**
   - Garder seulement `libs/tweety/` pour les JAR
   - Supprimer doublons de `libs/` racine
   - Économie: ~600 MB

2. **Nettoyage Temporaires**
   - Supprimer `libs/_temp_*_download/`
   - Vider fichiers de téléchargement obsolètes
   - Économie: ~762 MB

### Phase 2: Restructuration libs/
1. **Organisation par Type**
   ```
   libs/
   ├── tweety/           # Bibliothèques Tweety complètes
   ├── native/           # Bibliothèques natives (.dll/.so)
   ├── portable_jdk/     # JDK portable (OK)
   ├── portable_octave/  # Octave portable (OK)
   └── README.md         # Documentation libs
   ```

2. **Déplacement web_api**
   - Déplacer `libs/web_api/` vers `services/web_api/`
   - Rationaliser l'organisation des services

### Phase 3: Archives et Documentation
1. **Archives**
   - Créer `archives/legacy_scripts/` pour PowerShell
   - Garder seulement fichiers historiques nécessaires

2. **Documentation**
   - Consolider guides utilisateur
   - Nettoyer rapports redondants
   - Structurer par audience (dev/utilisateur/admin)

### Phase 4: Structure Globale Améliorée
```
📁 2025-Epita-Intelligence-Symbolique-4/
├── 📁 project_core/     # Code principal
├── 📁 libs/             # Bibliothèques externes (nettoyées)
├── 📁 services/         # Services web et APIs
├── 📁 examples/         # Exemples et démos
├── 📁 docs/             # Documentation (rationalisée)
├── 📁 tests/            # Tests organisés
├── 📁 scripts/          # Scripts utilitaires
├── 📁 config/           # Configurations
├── 📁 archives/         # Archives historiques
└── 📁 demos/            # Démonstrations
```

## 📊 Impact Estimé
- **Économie d'espace**: ~1.4 GB
- **Réduction fichiers**: ~50+ fichiers dupliqués supprimés
- **Amélioration navigation**: Structure plus claire
- **Maintenance facilitée**: Moins de redondance

## 🚀 Prochaines Étapes
1. Validation du plan avec utilisateur
2. Exécution Phase 1 (doublons critiques)
3. Tests de fonctionnalité
4. Phases 2-4 selon priorités
5. Commit et documentation des changements