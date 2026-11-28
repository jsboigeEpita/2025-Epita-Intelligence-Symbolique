#!/usr/bin/env python3
"""
Script de nettoyage du dépôt.

Ce script crée un fichier .env.example comme modèle et supprime les dossiers vides
qui ne devraient pas être versionnés, tout en préservant les fichiers de configuration
existants.

La racine du projet est le plus proche ancêtre portant un `.git` (#3726) : la version
précédente la calculait par profondeur (`.parent.parent.parent`) et valait `scripts/`,
si bien que le modèle était écrit dans `scripts/argumentation_analysis/.env.example` —
un chemin ignoré par git — au lieu de celui du dépôt.

`--dry-run` affiche ce qui serait fait, sans rien écrire, supprimer ni désindexer.
Pour le retrait du suivi, il montre la portée chemin par chemin (#3735).

Le retrait du suivi (#3735) lance git en liste d'arguments, depuis la racine : la
portée d'un pattern ne dépend ni du shell ni du répertoire de l'appelant. Pour les
`.jar`, ne sont retirés que les fichiers suivis que les règles d'exclusion du dépôt
ignorent déjà ; les autres restent suivis, et sont nommés.
"""

import argumentation_analysis.core.environment
import argparse
import os
import shutil
import subprocess
from pathlib import Path
import sys


class ProjectRootNotFound(RuntimeError):
    """Aucun ancêtre de ce fichier ne porte de `.git` : le dépôt est introuvable."""


def find_project_root(start: Path | None = None) -> Path:
    """Racine du dépôt : le plus proche ancêtre portant une entrée `.git`.

    `.exists()` et non `.is_dir()` : dans un worktree, `.git` est un fichier.
    Refuser bruyamment vaut mieux que retomber sur un répertoire faux — c'est
    précisément le défaut que #3726 répare.
    """
    origin = (start or Path(__file__)).resolve()
    for candidate in (origin, *origin.parents):
        if (candidate / ".git").exists():
            return candidate
    raise ProjectRootNotFound(f"aucun .git au-dessus de {origin}")


try:
    PROJECT_ROOT = find_project_root()
except ProjectRootNotFound as exc:  # script autonome : on sort proprement, code 2
    print(f"Erreur: racine du dépôt introuvable ({exc}).")
    raise SystemExit(2)


def _skip_in_dry_run(action: str, path: Path, dry_run: bool) -> bool:
    """En dry-run, annonce la mutation et dit à l'appelant de la sauter."""
    if dry_run:
        print(f"[dry-run] {action}: {path}")
        return True
    return False


def run_git_command(command):
    """Exécute une commande git et retourne le résultat."""
    try:
        result = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Erreur: {e.stderr}"


def _git(*args: str, stdin: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    """Git, en liste d'arguments, depuis la racine du dépôt — jamais via un shell (#3735).

    Le pattern est confié à git tel quel : c'est lui qui le lit (un `*` de
    pathspec traverse les `/`), et la portée ne dépend alors ni du shell ni du
    répertoire de l'appelant. Les sorties restent des octets ; les chemins de
    l'index et les messages sont décodés en UTF-8 là où on les lit.
    """
    return subprocess.run(
        ["git", *args], cwd=PROJECT_ROOT, input=stdin, capture_output=True
    )


def _text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace").strip()


def _nul(entries: list[str]) -> bytes:
    """Les entrées séparées par un caractère nul : la forme que git lit sans décodage."""
    return b"".join(entry.encode("utf-8") + b"\0" for entry in entries)


def _ignored_by_the_rules(paths: list[str]) -> set[str]:
    """Parmi ces chemins suivis, ceux que les règles d'exclusion du dépôt ignorent (#3735).

    La réponse vient des règles du dépôt seul : ses `.gitignore` et son
    `.git/info/exclude`. `core.excludesFile` est vidé pour la mesure — un fichier
    d'exclusion global appartient à une machine, pas au dépôt, et ne décide pas à
    sa place. `--no-index` : la réponse est celle des règles, pour un fichier
    suivi comme pour un autre. Git rend les chemins ignorés séparés par un
    caractère nul ; code 0 s'il y en a, 1 s'il n'y en a aucun.
    """
    result = _git(
        "-c",
        "core.excludesFile=",
        "check-ignore",
        "--no-index",
        "-z",
        "--stdin",
        stdin=_nul(paths),
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(
            f"git check-ignore a échoué (code {result.returncode}) : "
            f"{_text(result.stderr)}"
        )
    return {path for path in result.stdout.decode("utf-8").split("\0") if path}


def remove_files_from_git_tracking(
    pattern: str, dry_run: bool = False, only_ignored: bool = False
) -> bool:
    """Retire du suivi Git les fichiers que le pattern atteint, sans les toucher sur le disque (#3735).

    Git est lancé en liste d'arguments, depuis la racine du dépôt : la portée ne
    dépend plus du shell (sous cmd.exe, il ne développe pas `*.jar`) ni du
    répertoire de l'appelant. Le dry-run la montre chemin par chemin.

    `only_ignored` borne le retrait aux fichiers atteints que les règles
    d'exclusion du dépôt ignorent déjà. C'est la décision prise pour les `.jar` :
    l'index suit les règles. Un fichier suivi que ces règles n'ignorent pas reste
    suivi — le nettoyage ne le retire pas, et le nomme. La décision se lit dans
    les règles à chaque exécution ; elle ne les précède pas.
    """
    listing = _git("ls-files", "-z", "--cached", "--", pattern)
    if listing.returncode != 0:
        print(
            f"Échec de la recherche des fichiers '{pattern}' dans le suivi Git : "
            f"{_text(listing.stderr)}"
        )
        return False
    reached = [path for path in listing.stdout.decode("utf-8").split("\0") if path]
    if not reached:
        print(f"Aucun fichier suivi ne correspond à '{pattern}'.")
        return True

    to_remove = list(reached)
    kept: list[str] = []
    if only_ignored:
        try:
            ignored = _ignored_by_the_rules(reached)
        except RuntimeError as exc:
            print(f"Rien n'est retiré du suivi pour '{pattern}' : {exc}")
            return False
        kept = [path for path in reached if path not in ignored]
        to_remove = [path for path in reached if path in ignored]

    print(
        f"Le pattern '{pattern}' atteint {len(reached)} fichier(s) suivi(s) : "
        f"{len(to_remove)} à retirer, {len(kept)} à conserver."
    )
    for path in kept:
        fate = "serait conservé" if dry_run else "conservé"
        print(
            f"{'[dry-run] ' if dry_run else ''}{fate} — suivi, et aucune règle "
            f"d'exclusion du dépôt ne l'ignore : {path}"
        )
    if not to_remove:
        fate = "[dry-run] rien à retirer" if dry_run else "Rien à retirer"
        print(f"{fate} du suivi pour '{pattern}'.")
        return True

    # Chaque chemin est confié à git en littéral (`:(literal)`) : un nom qui porte
    # un crochet ne devient pas un gabarit atteignant aussi son voisin.
    removal = ["rm", "--cached"]
    if dry_run:
        removal.append("-n")
    result = _git(
        *removal,
        "--pathspec-from-file=-",
        "--pathspec-file-nul",
        stdin=_nul([f":(literal){path}" for path in to_remove]),
    )
    if result.returncode != 0:
        print(
            f"Échec du retrait des fichiers '{pattern}' du suivi Git : "
            f"{_text(result.stderr)}"
        )
        return False
    done = [
        line[len("rm '") : -1]
        for line in result.stdout.decode("utf-8").splitlines()
        if line.startswith("rm '") and line.endswith("'")
    ]
    if sorted(done) != sorted(to_remove):
        print(
            f"Le retrait s'est arrêté pour '{pattern}' : git annonce "
            f"{len(done)} chemin(s), la décision en portait {len(to_remove)}."
        )
        return False
    for path in done:
        fate = "[dry-run] serait retiré" if dry_run else "Retiré"
        print(f"{fate} du suivi : {path}")
    return True


def main(argv=None):
    """Fonction principale."""
    parser = argparse.ArgumentParser(
        description="Crée les modèles de configuration et retire les dossiers vides du suivi."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche ce qui serait fait, sans rien écrire, supprimer ni désindexer.",
    )
    args = parser.parse_args(argv)
    dry_run = args.dry_run

    # Afficher le répertoire de travail actuel pour le débogage
    current_dir = os.getcwd()
    print(f"Répertoire de travail actuel: {current_dir}")
    print(f"Racine du dépôt: {PROJECT_ROOT}")
    if dry_run:
        print("[dry-run] aucun fichier ne sera écrit, supprimé ni désindexé.")

    print("\n=== Nettoyage des fichiers du suivi Git ===")

    # Suppression des fichiers __pycache__ du suivi Git
    print("\nSuppression des dossiers __pycache__ du suivi Git...")
    remove_files_from_git_tracking("*/__pycache__", dry_run=dry_run)

    # Suppression des fichiers .pyc du suivi Git
    print("\nSuppression des fichiers .pyc du suivi Git...")
    remove_files_from_git_tracking("*.pyc", dry_run=dry_run)

    # Suppression des fichiers .jar du suivi Git. Seuls sont retirés les fichiers
    # suivis que les règles d'exclusion du dépôt ignorent déjà (#3735) : l'index
    # suit les règles, les autres restent suivis.
    print("\nSuppression des fichiers .jar du suivi Git...")
    remove_files_from_git_tracking("*.jar", dry_run=dry_run, only_ignored=True)

    print("\n=== Gestion des fichiers de configuration ===")

    # Création d'un fichier .env.example comme modèle
    arg_analysis_path = PROJECT_ROOT / "argumentation_analysis"
    env_path = arg_analysis_path / ".env"
    env_example_path = arg_analysis_path / ".env.example"

    print(f"Vérification du fichier .env à: {env_path}")

    if env_path.exists():
        print("Fichier .env trouvé.")
        if not env_example_path.exists():
            print("Création du fichier exemple .env.example...")
            if _skip_in_dry_run("créerait le modèle", env_example_path, dry_run):
                pass
            else:
                try:
                    with open(
                        env_example_path, "w", encoding="utf-8", newline="\n"
                    ) as f:
                        f.write(
                            """# Exemple de configuration pour le projet d'analyse argumentative
# Copiez ce fichier vers .env et modifiez les valeurs selon votre configuration

# Service LLM à utiliser (OpenAI, Azure, etc.)
GLOBAL_LLM_SERVICE="OpenAI"

# Clé API pour OpenAI
OPENAI_API_KEY="votre-clé-api-openai"

# Modèle de chat OpenAI à utiliser
OPENAI_CHAT_MODEL_ID="gpt-5.6-luna"

# Phrase secrète pour le chiffrement des configurations
TEXT_CONFIG_PASSPHRASE="votre-phrase-secrète"
"""
                        )
                    print("Fichier .env.example créé avec succès.")
                except Exception as e:
                    print(f"Erreur lors de la création du fichier .env.example: {e}")
    else:
        print(f"Fichier .env non trouvé à {env_path}")

    print(f"Chemin vers argumentation_analysis: {arg_analysis_path}")

    # Suppression du dossier config vide
    config_path = arg_analysis_path / "config"
    print(f"Vérification du dossier config à: {config_path}")

    if config_path.exists():
        try:
            if not any(config_path.iterdir()):
                if _skip_in_dry_run(
                    "supprimerait le dossier vide", config_path, dry_run
                ):
                    pass
                else:
                    print(f"Suppression du dossier vide {config_path}...")
                    config_path.rmdir()
                    print("Dossier config supprimé avec succès.")
            else:
                print("Le dossier config n'est pas vide, conservation.")
        except Exception as e:
            print(f"Erreur lors de la suppression du dossier config: {e}")
    else:
        print(f"Dossier config non trouvé à {config_path}")

    # Vérification du fichier .env
    print(f"Vérification du fichier .env à: {env_path}")

    if env_path.exists():
        print("Fichier .env trouvé.")

        # Vérification que .env est bien ignoré par Git en utilisant git status
        rel_path = os.path.relpath(env_path, PROJECT_ROOT)
        check_command = f'git status --porcelain "{rel_path}"'
        check_success, check_output = run_git_command(check_command)

        if check_success:
            if check_output.strip() and not check_output.strip().startswith("??"):
                print("ATTENTION: Le fichier .env est suivi par Git!")
                print(
                    "Vérifiez que la règle '.env' est bien présente dans votre fichier .gitignore."
                )
            else:
                print("Le fichier .env est correctement ignoré par Git.")
        else:
            print("Impossible de vérifier si le fichier .env est ignoré par Git.")
    else:
        print(f"Fichier .env non trouvé à {env_path}")

    print("\nNettoyage terminé.")
    if dry_run:
        print("[dry-run] rien n'a été modifié.")
        return 0
    print(
        "\nNOTE: Le fichier .env contenant des informations sensibles est toujours présent."
    )
    print(
        "Pour une sécurité optimale, assurez-vous qu'il est correctement ignoré par Git."
    )
    print(
        "Vérifiez avec 'git status' que le fichier .env n'apparaît pas dans les fichiers à commiter."
    )
    print("\nPour finaliser le nettoyage, n'oubliez pas de commiter les changements:")
    print('git commit -m "Nettoyage des fichiers sensibles et temporaires du dépôt"')
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Erreur non gérée: {e}")
        sys.exit(1)
