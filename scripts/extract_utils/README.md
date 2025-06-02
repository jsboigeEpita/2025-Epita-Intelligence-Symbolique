# Scripts Utilitaires pour la Gestion des Extraits

Ce répertoire contient des scripts pour manipuler, chiffrer, déchiffrer, inspecter, et gérer les fichiers d'extraits de sources (par exemple, `extract_sources.json.gz.enc`).

## Scripts

- `debug_inspect_extract_sources.py`: Déchiffre le fichier principal d'extraits en utilisant la clé de configuration de l'interface utilisateur et permet d'inspecter son contenu, y compris des sources spécifiques. Utile pour le débogage.
- `decrypt_extracts.py`: Déchiffre le fichier principal d'extraits en utilisant une clé (provenant de l'environnement ou d'une passphrase) et peut sauvegarder le contenu déchiffré. Fournit un résumé des extraits.
- `embed_all_sources.py`: Script pour embarquer le contenu textuel complet des sources directement dans le fichier de définitions d'extraits.
- `finalize_and_encrypt_sources.py`: Script pour finaliser les fichiers sources (potentiellement après l'embarquement) et les chiffrer.
- `identify_missing_segments.py`: Analyse les extraits pour identifier les segments de texte qui pourraient manquer ou être incomplets.
- `prepare_manual_correction.py`: Prépare les données d'extraits pour un processus de correction manuelle, potentiellement en les exportant dans un format éditable.
- `regenerate_encrypted_definitions.py`: Permet de régénérer le fichier chiffré des définitions d'extraits, par exemple après une modification des sources ou de la structure.