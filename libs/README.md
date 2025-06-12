# Bibliothèques Externes

Ce répertoire contient toutes les bibliothèques externes nécessaires au projet d'intelligence symbolique.

## 📁 Structure

```
libs/
├── tweety/              # Bibliothèques TweetyProject complètes
│   ├── native/          # Bibliothèques natives SAT (.dll/.so)
│   └── *.jar            # JARs TweetyProject v1.28 avec dépendances
├── native/              # Bibliothèques natives partagées
├── portable_jdk/        # JDK 17 portable
├── portable_octave/     # GNU Octave 10.1.0 portable
└── README.md            # Cette documentation
```

## 🎯 Bibliothèques Principales

### TweetyProject (libs/tweety/)
- **Version**: 1.28
- **Contenu**: Toutes les bibliothèques pour logique argumentative, propositionnelle, FOL, modale
- **Taille**: ~500+ MB avec dépendances
- **Usage**: Raisonnement logique et analyse argumentative

### Bibliothèques Natives (libs/native/)
- **lingeling.dll/so**: Solveur SAT
- **minisat.dll/so**: Solveur SAT MiniSat
- **picosat.dll/so**: Solveur SAT PicoSAT
- **Usage**: Résolution de problèmes de satisfiabilité

### JDK Portable (libs/portable_jdk/)
- **Version**: OpenJDK 17.0.11+9
- **Usage**: Exécution des bibliothèques Java TweetyProject
- **Avantage**: Autonomie sans installation système

### Octave Portable (libs/portable_octave/)
- **Version**: GNU Octave 10.1.0
- **Usage**: Calculs scientifiques et notebooks
- **Avantage**: Environnement MATLAB-like autonome

## 🔧 Notes Techniques

### Changements Récents
- ✅ **Suppression doublons** : Économie de 437 MB (JAR dupliqués)
- ✅ **Nettoyage temporaires** : Économie de 762 MB 
- ✅ **Réorganisation** : web_api déplacé vers services/
- ✅ **Total libéré** : ~1.2 GB d'espace disque

### Maintenance
- Les bibliothèques Tweety sont maintenues uniquement dans `libs/tweety/`
- Les fichiers de téléchargement temporaires sont automatiquement nettoyés
- Les versions sont figées pour garantir la reproductibilité

### Utilisation
Voir les exemples dans `examples/` et la documentation dans `docs/guides/` pour l'usage des différentes bibliothèques.
