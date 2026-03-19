#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de réparation pour ajouter les diffs manquants aux fichiers d'audit de commits.

Ce script parcourt les fichiers JSON générés par git_archeology_analyzer.py,
lit le SHA du commit et enrichit la liste 'files_changed' avec le diff de
chaque fichier.
"""

import subprocess
import json
from pathlib import Path
import argparse
import sys

def run_git_command(command: list[str]) -> str:
    """Exécute une commande Git et retourne sa sortie."""
    try:
        result = subprocess.run(
            ['git'] + command,
            capture_output=True,
            check=False
        )
        if result.returncode != 0:
            stderr_output = result.stderr.decode('utf-8', errors='replace').strip()
            print(f"Erreur Git: {stderr_output}", file=sys.stderr)
            return ""
        return result.stdout.decode('utf-8', errors='replace').strip()
    except FileNotFoundError:
        print("Erreur : git n'est pas installé ou n'est pas dans le PATH.", file=sys.stderr)
        return ""

def get_commit_file_statuses(sha: str) -> dict[str, str]:
    """Récupère les statuts de tous les fichiers pour un commit donné."""
    statuses = {}
    command = ['show', '--pretty=format:', '--name-status', sha]
    output = run_git_command(command)
    if not output:
        return {}
    
    for line in output.split('\n'):
        if not line:
            continue
        try:
            status, filepath = line.split('\t', 1)
            statuses[filepath] = status.strip()
        except ValueError:
            # Gère les cas de renommage comme "R100\told_path\tnew_path"
            parts = line.split('\t')
            if len(parts) == 3 and parts[0].startswith('R'):
                status, old_path, new_path = parts
                statuses[new_path] = status.strip()
    return statuses

def get_file_diff(sha: str, filepath: str) -> str:
    """Récupère le diff pour un fichier spécifique dans un commit."""
    command = ['show', '--pretty=format:', '--unified=0', sha, '--', filepath]
    return run_git_command(command)

def fix_commit_audit_file(json_file: Path, file_statuses: dict[str, str]):
    """Met à jour un fichier d'audit JSON avec les diffs manquants."""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Erreur de lecture du fichier {json_file}: {e}", file=sys.stderr)
        return

    sha = data.get("sha")
    if not sha:
        print(f"SHA manquant dans {json_file}", file=sys.stderr)
        return

    files_changed = data.get("files_changed", [])
    new_files_changed = []
    needs_update = False

    for file_entry in files_changed:
        if isinstance(file_entry, dict) and "diff" in file_entry:
            # L'entrée est déjà un objet avec un diff, on la garde telle quelle.
            new_files_changed.append(file_entry)
            continue

        if isinstance(file_entry, str):
            filepath = file_entry
            needs_update = True
            
            print(f"  -> Traitement de {filepath} pour le commit {sha[:7]}...")
            diff_content = get_file_diff(sha, filepath)
            status = file_statuses.get(filepath, "M_UNKNOWN") # "M" par défaut si inconnu

            new_files_changed.append({
                "filename": filepath,
                "status": status,
                "diff": diff_content
            })
        else:
            # Gérer d'autres formats inattendus si nécessaire
            new_files_changed.append(file_entry)

    if needs_update:
        data["files_changed"] = new_files_changed
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ Fichier mis à jour : {json_file.name}")
        except IOError as e:
            print(f"Erreur d'écriture dans {json_file}: {e}", file=sys.stderr)

def main():
    """Point d'entrée principal du script."""
    parser = argparse.ArgumentParser(description="Corrige les fichiers d'audit de commit en ajoutant les diffs manquants.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limite le nombre de fichiers à traiter pour le test."
    )
    args = parser.parse_args()

    audit_dir = Path("docs/commits_audit")
    if not audit_dir.exists():
        print(f"Le répertoire d'audit '{audit_dir}' n'existe pas.", file=sys.stderr)
        sys.exit(1)

    json_files = sorted(list(audit_dir.glob("*.json")))
    
    if args.limit:
        print(f"⚠️ Limite de {args.limit} fichier(s) activée.")
        json_files = json_files[:args.limit]

    print(f"🚀 Démarrage de la correction pour {len(json_files)} fichier(s)...")

    for json_file in json_files:
        print(f"\nTraitement du fichier : {json_file.name}")
        # Lire le SHA sans charger tout le fichier en premier
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                temp_data = json.load(f)
                sha = temp_data.get("sha")
        except (json.JSONDecodeError, KeyError):
            print(f"  Impossible de lire le SHA de {json_file.name}, passage au suivant.")
            continue
            
        print(f"  Commit SHA: {sha}")
        file_statuses = get_commit_file_statuses(sha)
        fix_commit_audit_file(json_file, file_statuses)

    print("\n🎉 Correction terminée.")

if __name__ == "__main__":
    main()