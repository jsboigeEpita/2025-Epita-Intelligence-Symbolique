# Scripts Utilitaires

Ce répertoire contient des scripts utilitaires pour la maintenance et la correction du code du projet.

## Liste des scripts

### check_syntax.py
Script pour vérifier la syntaxe d'un fichier Python. Il utilise les modules `ast` et `tokenize` pour analyser le code et détecter les erreurs de syntaxe.

**Usage :** 
```bash
python check_syntax.py <file_path>
```

### fix_docstrings.py
Script pour corriger les problèmes d'apostrophes dans les docstrings des fichiers Python. Il remplace les apostrophes problématiques par des versions correctement échappées.

**Usage :**
```bash
python fix_docstrings.py <file_path>
```

### fix_encoding.py
Script pour corriger l'encodage d'un fichier. Il essaie de décoder le fichier avec différents encodages (utf-8, latin-1, cp1252, iso-8859-1) et le réencode en UTF-8.

**Usage :**
```bash
python fix_encoding.py <file_path>
```

### fix_indentation.py
Script pour corriger l'indentation d'un fichier Python. Il analyse la structure du code (classes, méthodes, fonctions) et applique une indentation cohérente.

**Usage :**
```bash
python fix_indentation.py <file_path>
```

## Utilisation générale

Ces scripts peuvent être utilisés individuellement pour corriger des problèmes spécifiques dans les fichiers du projet. Ils sont particulièrement utiles lors de la maintenance du code ou de l'intégration de nouvelles fonctionnalités.

Pour exécuter un script sur un fichier spécifique :

```bash
python scripts/utils/<script_name>.py <file_path>
```

## Note

Ces scripts ont été créés pour résoudre des problèmes spécifiques rencontrés lors du développement du projet. Ils peuvent nécessiter des ajustements en fonction de l'évolution des besoins du projet.