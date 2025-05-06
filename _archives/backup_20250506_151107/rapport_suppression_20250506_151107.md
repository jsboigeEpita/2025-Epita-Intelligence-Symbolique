# Rapport de suppression des fichiers de documentation résiduels

Date: 2025-05-06 15:11:07
Mode: Exécution réelle
Répertoire d'archives: _archives\backup_20250506_151107

## Fichiers sauvegardés

| Fichier | Taille | Date de modification | Hash SHA-256 |
|---------|--------|----------------------|--------------|
| docs/rapport_analyse_comparative.md | 12996 octets | 2025-05-06T03:21:33.513783 | a7211064... |
| docs/rapport_final.md | 8617 octets | 2025-05-06T01:18:45.947590 | dda1b1df... |
| docs/rapport_refactorisation_extraits.md | 6428 octets | 2025-05-06T03:21:33.513783 | 367944b3... |
| docs/README_ENVIRONNEMENT.md | 3787 octets | 2025-05-06T01:18:45.944821 | 047a2f28... |

## Fichiers supprimés

Total: 4 fichiers

- docs/rapport_analyse_comparative.md
- docs/rapport_final.md
- docs/rapport_refactorisation_extraits.md
- docs/README_ENVIRONNEMENT.md

## Restauration

Pour restaurer ces fichiers, exécutez:

```
python scripts/cleanup/cleanup_residual_docs.py --restore
```

Ou spécifiez le répertoire d'archives:

```
python scripts/cleanup/cleanup_residual_docs.py --restore --archive-dir=_archives\backup_20250506_151107
```
