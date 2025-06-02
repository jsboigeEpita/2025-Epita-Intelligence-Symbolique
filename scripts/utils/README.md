# Scripts Utilitaires

Ce répertoire contient des scripts utilitaires pour la maintenance, la correction du code, l'analyse et l'inspection du projet.

## Liste des scripts

### analyze_directory_usage.py
Analyse l'utilisation de certains répertoires dans le code (utilise `project_core.dev_utils.code_validation`).

**Usage :**
```bash
python scripts/utils/analyze_directory_usage.py --dir <directory_to_analyze> --output <report_file.json>
```

### check_encoding.py
Vérifie l'encodage UTF-8 des fichiers Python du projet (utilise `project_core.dev_utils.encoding_utils`).
Le plan suggère une fusion/clarification future avec `fix_encoding.py`.

**Usage :**
```bash
python scripts/utils/check_encoding.py <file_path_or_directory>
```

### check_syntax.py
Script pour vérifier la syntaxe d'un fichier Python. Il utilise les modules `ast` et `tokenize` pour analyser le code et détecter les erreurs de syntaxe.

**Usage :**
```bash
python scripts/utils/check_syntax.py <file_path>
```

### fix_docstrings.py
Script pour corriger les problèmes d'apostrophes dans les docstrings des fichiers Python. Il remplace les apostrophes problématiques par des versions correctement échappées.

**Usage :**
```bash
python scripts/utils/fix_docstrings.py <file_path>
```

### fix_encoding.py
Script pour corriger l'encodage d'un fichier. Il essaie de décoder le fichier avec différents encodages (utf-8, latin-1, cp1252, iso-8859-1) et le réencode en UTF-8.

**Usage :**
```bash
python scripts/utils/fix_encoding.py <file_path>
```

### fix_indentation.py
Script pour corriger l'indentation d'un fichier Python. Il analyse la structure du code (classes, méthodes, fonctions) et applique une indentation cohérente.

**Usage :**
```bash
python scripts/utils/fix_indentation.py <file_path>
```

### inspect_specific_sources.py
Script pour inspecter des sources spécifiques, potentiellement pour vérifier leur contenu ou leur structure.

**Usage :**
```bash
python scripts/utils/inspect_specific_sources.py --source <source_identifier_ou_path>
```

### script_commits.ps1
Script PowerShell pour aider à la gestion des commits.
**Note : L'usage de ce script doit être documenté plus en détail, ou une alternative en Python pourrait être envisagée pour simplifier les workflows de développement multi-plateforme.**

**Usage :**
```powershell
.\\scripts\\utils\\script_commits.ps1
```

### test_imports_utils.py / test_imports_utils_impl.py
Scripts pour tester les utilitaires d'importation.

## Utilisation générale

Ces scripts peuvent être utilisés individuellement pour des tâches spécifiques. Ils sont particulièrement utiles lors de la maintenance du code ou de l'intégration de nouvelles fonctionnalités.

Pour exécuter un script sur un fichier spécifique :

```bash
python scripts/utils/<script_name>.py <arguments_specifiques>
```
ou pour PowerShell :
```powershell
.\\scripts\\utils\\<script_name>.ps1 <arguments_specifiques>
```

## Note

Ces scripts ont été créés pour résoudre des problèmes spécifiques rencontrés lors du développement du projet. Ils peuvent nécessiter des ajustements en fonction de l'évolution des besoins du projet.