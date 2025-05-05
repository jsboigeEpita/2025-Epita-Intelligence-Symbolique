# Rapport de suppression des fichiers obsolètes

Date: 2025-05-01 09:14:40
Mode: Exécution réelle
Répertoire d'archives: _archives\backup_20250501_091439

## Fichiers sauvegardés

| Fichier | Taille | Date de modification | Hash SHA-256 |
|---------|--------|----------------------|--------------|
| argumentiation_analysis/utils/extract_repair/repair_extract_markers.py | 48332 octets | 2025-04-30T09:02:00.903597 | c1ea8399... |
| argumentiation_analysis/utils/extract_repair/verify_extracts.py | 25387 octets | 2025-04-30T09:02:00.903597 | c3fe6461... |
| argumentiation_analysis/utils/extract_repair/fix_missing_first_letter.py | 6266 octets | 2025-04-30T09:02:00.902323 | 6a2f8b06... |
| argumentiation_analysis/utils/extract_repair/verify_extracts_with_llm.py | 33726 octets | 2025-04-30T09:02:00.906088 | ceba118b... |
| argumentiation_analysis/utils/extract_repair/repair_extract_markers.ipynb | 41290 octets | 2025-04-29T22:04:35.053124 | 195070bd... |
| argumentiation_analysis/ui/extract_utils.py | 16422 octets | 2025-04-29T20:51:09.884136 | 7558c55c... |

## Fichiers supprimés

Total: 6 fichiers

- argumentiation_analysis/utils/extract_repair/repair_extract_markers.py
- argumentiation_analysis/utils/extract_repair/verify_extracts.py
- argumentiation_analysis/utils/extract_repair/fix_missing_first_letter.py
- argumentiation_analysis/utils/extract_repair/verify_extracts_with_llm.py
- argumentiation_analysis/utils/extract_repair/repair_extract_markers.ipynb
- argumentiation_analysis/ui/extract_utils.py

## Restauration

Pour restaurer ces fichiers, exécutez:

```
python cleanup_obsolete_files.py --restore
```

Ou spécifiez le répertoire d'archives:

```
python cleanup_obsolete_files.py --restore --archive-dir=_archives\backup_20250501_091439
```
