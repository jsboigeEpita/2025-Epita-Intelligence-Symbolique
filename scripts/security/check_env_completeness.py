#!/usr/bin/env python
"""Compare un .env local au canon .env.example — sans jamais lire une valeur à voix haute.

Mandat flotte : chaque siège doit détenir toutes les clés. Trois défauts empêchent
cela, et un seul est visible à l'œil nu :

1. ABSENTE    — le canon déclare la clé, le .env ne la porte pas.
2. VIDE       — la clé est là, sa valeur ne l'est pas.
3. SPECIMEN   — la clé est là, sa valeur est encore celle d'exemple du canon.

Le troisième est le coûteux : un inventaire par noms le compte comme présent, et
l'échec n'apparaît qu'au premier appel réseau.

Égalité avec le canon ne suffit PAS à conclure au spécimen : beaucoup d'entrées
ont légitimement le canon pour valeur (`GLOBAL_LLM_SERVICE=OpenAI`, une base_url
publique). Le discriminant est la *forme* de la valeur, pas son égalité.

Aucune valeur n'est imprimée : noms, longueurs, empreintes SHA256 tronquées.
La sortie est faite pour être collée sur un dashboard ou un DM sans expurgation.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

# Un nom d'assignation, commenté ou non : le canon documente ses options en
# commentaire, et une clé optionnelle documentée reste une clé déclarée.
ASSIGN = re.compile(r"^\s*#?\s*([A-Z_][A-Z0-9_]*)\s*=(.*)$")

# Formes qui trahissent une valeur d'exemple jamais remplacée.
SPECIMEN = re.compile(
    r"(your[-_]|votre_|xxxx|\.\.\.|à_remplir|a_remplir|to[-_]be[-_]filled"
    r"|change[-_]?me|une_phrase_secrete)",
    re.IGNORECASE,
)


def unquote(raw: str) -> str:
    v = raw.strip().rstrip("\r")
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    return v


def parse(path: Path, keep_commented: bool) -> dict[str, tuple[str, bool]]:
    """Rend {cle: (valeur, commentee)}.

    L'etat commente n'est pas un detail de presentation : dans le canon il
    separe la ligne de base que tout siege doit porter de l'option qu'il peut
    ignorer. Les confondre fait crier l'outil sur des surcharges facultatives.

    Doubles occurrences : une occurrence non commentee ne peut pas etre
    degradee en option par une ligne de doc commentee, quel que soit l'ordre
    (.env.example re-ecrit ses cles dans un bloc de commentaire) ; a statut
    egal la derniere gagne, comme python-dotenv a la lecture.
    """
    out: dict[str, tuple[str, bool]] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        commented = line.lstrip().startswith("#")
        if commented and not keep_commented:
            continue
        m = ASSIGN.match(line)
        if m:
            entry = (unquote(m.group(2)), commented)
            prev = out.get(m.group(1))
            # prev=None -> premiere occurrence ; sinon ecraser sauf si la ligne
            # courante est commentee et l'existante ne l'est pas.
            if prev is None or not (entry[1] and not prev[1]):
                out[m.group(1)] = entry
    return out


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]


def audit(
    env_path: Path, canon_path: Path
) -> tuple[list[str], list[str], int, list[str]]:
    """Rend (ecarts bloquants, notes optionnelles, taille inventaire, inventaire)."""
    canon = parse(canon_path, keep_commented=True)
    if not any(not commented for _, commented in canon.values()):
        # Le garde vit ICI, pas dans main() : audit() est la fonction qui
        # certifie, et un importeur direct ne traverse pas le CLI. Un canon
        # vide, tronque par une redirection cassee, ou aux entrees toutes
        # commentees rendrait « aucun ecart » sans avoir rien compare --
        # l'absence d'exigence n'est pas une conformite.
        raise ValueError(
            f"canon inutilisable: {canon_path} ne declare aucune cle requise "
            "(vide, tronque, ou toutes entrees commentees) — un « complet » "
            "ici ne mesurerait rien"
        )
    env = parse(env_path, keep_commented=False)

    findings: list[str] = []
    optional: list[str] = []
    for key in sorted(canon):
        canon_value, canon_commented = canon[key]
        if key not in env:
            # Une entree commentee du canon est une option documentee, pas une
            # exigence : son absence est informative, jamais un echec.
            (optional if canon_commented else findings).append(
                f"{'OPTION  ' if canon_commented else 'ABSENTE '}  {key}"
            )
            continue
        value = env[key][0]
        if not value:
            verdict = f"VIDE      {key}"
        elif value == canon_value and SPECIMEN.search(value):
            verdict = f"SPECIMEN  {key}  (len={len(value)})"
        else:
            continue
        # Le statut optionnel vaut pour les DEUX etats d'entree, pas seulement
        # l'absence : un siege qui a copie .env.example en .env porte le
        # specimen des entrees commentees, et le declarer bloquant reclame une
        # valeur que le canon ne demande pas. Reste informatif -- une valeur
        # inerte merite d'etre vue, elle ne merite pas d'arreter le siege.
        (optional if canon_commented else findings).append(
            f"{verdict}  [option]" if canon_commented else verdict
        )

    inventory = [
        f"  {k:<34} len={len(v[0]):<4} fp={fingerprint(v[0])}"
        for k, v in sorted(env.items())
    ]
    return findings, optional, len(inventory), inventory


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--env", default=".env", type=Path)
    ap.add_argument("--canon", default=".env.example", type=Path)
    ap.add_argument(
        "--inventory",
        action="store_true",
        help="imprime aussi l'inventaire nom/longueur/empreinte (aucune valeur)",
    )
    args = ap.parse_args()

    if not args.env.exists():
        print(f"pas de {args.env} sur ce siège — rien à comparer", file=sys.stderr)
        return 2
    if not args.canon.exists():
        print(f"canon introuvable: {args.canon}", file=sys.stderr)
        return 2

    try:
        findings, optional, count, inventory = audit(args.env, args.canon)
    except ValueError as exc:
        # Le garde vit dans audit() — la couche qui certifie. Le CLI ne fait
        # que traduire son refus en code de sortie : un importeur direct de
        # audit() etait certifie par la meme fonction que le terminal.
        print(str(exc), file=sys.stderr)
        return 2

    if args.inventory:
        print(f"inventaire ({count} clés, valeurs jamais affichées):")
        print("\n".join(inventory))

    if optional:
        print(
            f"{len(optional)} option(s) documentée(s) non renseignée(s) — informatif:"
        )
        for o in optional:
            print(f"  {o}")

    if not findings:
        print("complet: aucune clé requise absente, vide ou restée au spécimen")
        return 0

    print(f"{len(findings)} écart(s) bloquant(s) au canon:")
    for f in findings:
        print(f"  {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
