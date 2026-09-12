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
    """
    out: dict[str, tuple[str, bool]] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        commented = line.lstrip().startswith("#")
        if commented and not keep_commented:
            continue
        m = ASSIGN.match(line)
        if m:
            out.setdefault(m.group(1), (unquote(m.group(2)), commented))
    return out


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]


def audit(
    env_path: Path, canon_path: Path
) -> tuple[list[str], list[str], int, list[str]]:
    """Rend (ecarts bloquants, notes optionnelles, taille inventaire, inventaire)."""
    canon = parse(canon_path, keep_commented=True)
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
            findings.append(f"VIDE      {key}")
        elif value == canon_value and SPECIMEN.search(value):
            findings.append(f"SPECIMEN  {key}  (len={len(value)})")

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

    # Un canon qui ne declare aucune cle requise rend "complet" sans avoir rien
    # compare : vide, tronque par une redirection cassee, ou toutes entrees
    # commentees donnent le meme vert vacuous. Mesure a l'origine de ce garde :
    # un `git show` mange par MSYS a cree un canon vide, et l'outil a valide un
    # siege incomplet. L'absence d'exigence n'est pas une conformite.
    required = [
        k
        for k, (_, commented) in parse(args.canon, keep_commented=True).items()
        if not commented
    ]
    if not required:
        print(
            f"canon inutilisable: {args.canon} ne declare aucune cle requise "
            "(vide, tronque, ou toutes les entrees commentees) — un « complet » "
            "ici ne mesurerait rien",
            file=sys.stderr,
        )
        return 2

    findings, optional, count, inventory = audit(args.env, args.canon)

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
