"""#2088 (DoD de l'Epic, dernière case) : les répertoires substantiels de
``argumentation_analysis/`` portent un README, et chaque lien relatif ``.md``
des README de ``argumentation_analysis/`` résout.

- **Population** : ``git ls-files`` uniquement (#2607 : aucun walk récursif),
  lecture ``utf-8-sig`` (BOM mesuré sur ``fol_logic_agent.py``, #2947).
- **Substantiel** : même définition que ``scripts/docs/readme_waves_2088.py``
  (membres suivis DIRECTS du répertoire ; ≥ 3 fichiers ou ≥ 1 ``.py`` ;
  racines vendues exclues).
- **Exclusions** : une entrée nommée avec sa raison est admise, mais une
  entrée périmée (répertoire devenu léger, ou README apparu) ROUGIT — le
  registre ne peut pas gonfler pour absorber le silence (#1842).
- **Liens** : ``[texte](chemin.md)`` relatifs uniquement (http/mailto hors
  périmètre, ancre ``#…`` ignorée) ; la cible doit exister. Un lien mort
  prétend qu'une fiche existe : c'est exactement ce que cette garde interdit.
- **Liens RENDUS** (rework #2962, revue coord) : les liens sont comptés comme
  markdown-it les REND, pas comme une regex lit le texte brut — un lien écrit
  dans un bloc de code (exemple, extrait, fence non fermée) n'est pas un lien.
  Mesuré sur la tête initiale de la PR : l'arête ``pipelines`` →
  ``orchestration`` satisfaisait la garde par regex alors que la page rendue
  ne liait rien (fence mermaid jamais fermée).
"""

import posixpath
import re
import subprocess
from collections import defaultdict
from pathlib import Path

from markdown_it import MarkdownIt

REPO = Path(__file__).resolve().parents[3]
SUBTREE = "argumentation_analysis"
_MD = MarkdownIt()

# Racines vendues sous argumentation_analysis/ (convention readme_waves_2088) :
# runtimes externes, hors périmètre documentaire.
VENDORED_ROOTS = ("libs", "portable_jdk")

# Répertoires substantiels dispensés de README, avec la raison. Une entrée
# dont le répertoire n'est plus substantiel ou a gagné un README rougit
# (test_exclusions_stay_meaningful) — la carte ne peut que rétrécir.
EXCLUDED_SUBSTANTIAL_DIRS: dict[str, str] = {}

SUBSTANTIAL_MIN_FILES = 3
_MIN_SUBSTANTIAL_DIRS = 90  # mesuré : 94 (avant data/README.md : 93 + data)
_MIN_MD_LINKS = (
    355  # mesuré : 360 liens RENDUS markdown-it (rework #2962 ; 196 en regex
    # texte brut, qui ne voyait ni les fences ni les liens par référence)
)
_MIN_ALL_TARGET_LINKS = (
    450  # mesuré 2026-10-08 : 458 liens relatifs rendus TOUT type de cible
    # (466 avant la réécriture des 5 README #2992 — les artefacts non suivis
    # y ont été dé-liés) ; extension DoD n°10 après le classement #2992
)


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "--", SUBTREE],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in out.stdout.splitlines() if line]


def _rendered_relative_targets(text: str) -> list[str]:
    """Toutes les cibles de liens RELATIVES telles que markdown-it les REND
    — tout type de cible : ``.md``, ``.py``, notebooks, répertoires.

    Un bloc de code (fence) ne produit aucun token ``link_open`` : un lien
    écrit dedans n'existe pas pour le lecteur, donc pas pour la garde
    (rework #2962). Les ancres ``#…`` et ``:NN`` (ligne) sont retirées avant
    résolution : ce ne sont pas des chemins.
    """
    targets = []
    for block in _MD.parse(text):
        if block.type != "inline":
            continue  # link_open vit dans les enfants du bloc inline
        for token in block.children or []:
            if token.type != "link_open":
                continue
            href = token.attrGet("href") or ""
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            target = re.split(r"[:#]", href)[0].strip()
            if target:
                targets.append(target)
    return targets


def _rendered_md_link_targets(text: str) -> list[str]:
    """Les cibles ``.md`` parmi les cibles relatives rendues (#2962)."""
    return [t for t in _rendered_relative_targets(text) if t.endswith(".md")]


def _substantial_dirs(files: list[str]) -> dict[str, set[str]]:
    """Répertoires substantiels → fichiers suivis directs (convention waves)."""
    members: dict[str, set[str]] = defaultdict(set)
    for f in files:
        parts = f.split("/")
        if len(parts) < 3:  # fichier directement sous argumentation_analysis/
            continue
        d = "/".join(parts[1:-1])
        if d.split("/")[0] in VENDORED_ROOTS:
            continue
        members[d].add(f)
    return {
        d: m
        for d, m in members.items()
        if len(m) >= SUBSTANTIAL_MIN_FILES or any(x.endswith(".py") for x in m)
    }


def _readme_files(files: list[str]) -> list[str]:
    return [
        f
        for f in files
        if f.endswith("README.md") and f.split("/")[1] not in VENDORED_ROOTS
    ]


def _md_link_targets(readme: str) -> list[str]:
    text = (REPO / readme).read_text(encoding="utf-8-sig")
    return _rendered_md_link_targets(text)


class TestSubstantialDirsCarryReadme:
    def test_every_substantial_dir_has_a_readme(self):
        files = _tracked_files()
        substantial = _substantial_dirs(files)
        assert len(substantial) >= _MIN_SUBSTANTIAL_DIRS, (
            f"population inattendue : {len(substantial)} répertoires "
            f"substantiels (plancher {_MIN_SUBSTANTIAL_DIRS}) — un changement "
            "de convention de comptage doit re-mesurer les planchers"
        )
        missing = sorted(
            d
            for d in substantial
            if d not in EXCLUDED_SUBSTANTIAL_DIRS
            and f"{SUBTREE}/{d}/README.md" not in substantial[d]
        )
        assert missing == [], (
            "#2088 : répertoires substantiels sans README (exclusion nommée "
            f"requise dans EXCLUDED_SUBSTANTIAL_DIRS, avec raison) : {missing}"
        )

    def test_exclusions_stay_meaningful(self):
        """Chaque exclusion nommée reste substantielle et sans README.

        Une exclusion périmée (README apparu, répertoire devenu léger) rend
        cette garde rouge : la carte rétrécit, elle ne gonfle jamais.
        """
        files = _tracked_files()
        substantial = _substantial_dirs(files)
        for d in EXCLUDED_SUBSTANTIAL_DIRS:
            assert (
                d in substantial
            ), f"exclusion périmée : {d!r} n'est plus un répertoire substantiel"
            assert (
                f"{SUBTREE}/{d}/README.md" not in substantial[d]
            ), f"exclusion périmée : {d!r} a maintenant un README"


class TestReadmeLinksResolve:
    def test_every_relative_md_link_resolves(self):
        files = _tracked_files()
        broken = []
        n_links = 0
        for readme in _readme_files(files):
            for target in _md_link_targets(readme):
                n_links += 1
                resolved = (REPO / readme).parent / target
                if not resolved.exists():
                    broken.append(f"{readme} -> {target}")
        assert n_links >= _MIN_MD_LINKS, (
            f"population inattendue : {n_links} liens .md relatifs "
            f"(plancher {_MIN_MD_LINKS}) — re-mesurer après un changement "
            "de convention"
        )
        assert broken == [], (
            "#2088 : liens .md relatifs morts dans les README de "
            f"argumentation_analysis/ : {broken}"
        )

    def test_every_relative_rendered_link_resolves(self):
        """#2088 DoD n°10, extension mesurée 2026-10-07 : la garde ne voyait
        que les cibles ``.md`` — les 12 liens morts recensés par
        l'instrument de classement (5 README pointant des ``.py``, des
        notebooks convertis, des répertoires inexistants) lui étaient
        invisibles. Cette instance garde TOUTES les cibles relatives rendues.

        Né-rouge mesuré sur la tête de la PR, AVANT la correction des 5
        README : les 12 cibles cassées la rendent rouge.
        """
        files = _tracked_files()
        broken = []
        n_links = 0
        for readme in _readme_files(files):
            text = (REPO / readme).read_text(encoding="utf-8-sig")
            for target in _rendered_relative_targets(text):
                n_links += 1
                resolved = (REPO / readme).parent / target
                if not resolved.exists():
                    broken.append(f"{readme} -> {target}")
        assert n_links >= _MIN_ALL_TARGET_LINKS, (
            f"population inattendue : {n_links} liens relatifs rendus, tout "
            f"type de cible (plancher {_MIN_ALL_TARGET_LINKS}) — re-mesurer "
            "après un changement de convention"
        )
        assert broken == [], (
            "#2088 : liens relatifs morts (TOUT type de cible) dans les "
            f"README de argumentation_analysis/ : {broken}"
        )


class TestLinksAreReadAsRendered:
    """Rework #2962 (revue coord) : la garde compte les liens RENDUS.

    Né-rouge mesuré sur la tête initiale de la PR : le lien de l'arête
    ``pipelines`` → ``orchestration`` était écrit après une fence mermaid
    jamais fermée — la regex le comptait, la page rendue ne liait rien.
    """

    def test_fenced_link_is_not_a_link(self):
        text = (
            "# Fiche\n\n"
            "```mermaid\n"
            "A --> B[`child/`](./child/README.md);\n"
            "```\n"
        )
        assert _rendered_md_link_targets(text) == []

    def test_unclosed_fence_swallows_the_whole_tail(self):
        """La forme mesurée : fence jamais fermée, la section « Enfants
        documentés » rend DANS le bloc — aucun lien n'en sort."""
        text = (
            "# Fiche\n\n"
            "```mermaid\n"
            "graph TD\n"
            "    D --> E[Artefact];\n"
            "\n"
            "## Enfants documentés\n"
            "\n"
            "- [`child/`](./child/README.md)\n"
        )
        assert _rendered_md_link_targets(text) == []

    def test_same_link_outside_the_fence_counts(self):
        text = "# Fiche\n\n```\nexemple\n```\n\n- [`child/`](./child/README.md)\n"
        assert _rendered_md_link_targets(text) == ["./child/README.md"]

    def test_inline_code_link_is_not_a_link(self):
        text = "# Fiche\n\n`[pas un lien](./child/README.md)`\n"
        assert _rendered_md_link_targets(text) == []


class TestRootReadmeCitesEveryChild:
    """Le README racine cite chaque enfant de premier niveau qui a un README.

    La garde voisine tient « substantiel ⇒ README » ; celle-ci tient la
    réciproque côté racine — un enfant documenté mais absent de la fiche
    racine est invisible depuis le point d'entrée du paquet. Propriété
    d'ENSEMBLE, jamais un compte écrit à la main : un répertoire neuf avec
    README rougit ici au lieu de périmer silencieusement un « 25 ».
    """

    def test_every_depth1_readme_is_cited_from_the_root(self):
        files = _tracked_files()
        root = f"{SUBTREE}/README.md"
        children = {
            f"{SUBTREE}/{f.split('/')[1]}/README.md"
            for f in files
            if f.count("/") == 2
            and f.endswith("/README.md")
            and f.split("/")[1] not in VENDORED_ROOTS
        }
        assert children, "population vide : le README racine n'a aucun enfant"

        cited = {
            posixpath.normpath(f"{SUBTREE}/{target}")
            for target in _md_link_targets(root)
        }
        missing = sorted(children - cited)
        assert missing == [], (
            "#2088 : enfants de premier niveau portant un README et NON cités "
            f"depuis {root} : {missing}"
        )


# #2088 item 5 (dispatch R1070) : liens parent↔enfant dans les DEUX sens,
# arbre entier. TestReadmeLinksResolve tient que les liens EXISTANTS
# résolent ; retirer un lien ne rougissait nulle part (mutation mesurée :
# supprimer le back-link « Parent : » de hierarchical/strategic laissait la
# suite à 34 passed). Ces gardes tiennent que les liens EXISTENT :
# chaque README qui a un parent/enfant documenté immédiat le lie —
# parent→enfant ET enfant→parent.
#
# Exclusions nommées avec raison (même contrat que
# EXCLUDED_SUBSTANTIAL_DIRS) : une entrée périmée (lien apparu, ou README
# disparu d'un côté) ROUGIT — les cartes ne gonflent jamais.
PARENT_OMITS_CHILD: dict[str, str] = {}
CHILD_OMITS_PARENT: dict[str, str] = {}

_MIN_PARENT_CHILD_PAIRS = (
    80  # mesuré sur main 25299812e — re-mesurer après changement de convention
)


def _readme_tree(files: list[str]) -> set[str]:
    """Dirs sous SUBTREE (relatifs, hors racine) portant un README suivi."""
    return {
        f[len(SUBTREE) + 1 : -len("/README.md")]
        for f in _readme_files(files)
        if f != f"{SUBTREE}/README.md"
    }


class TestParentChildReadmeLinksBothWays:
    """Chaque arête documentée immédiate est liée des deux côtés.

    Une arête = (parent dir, child dir) où les DEUX portent un README suivi
    et l'enfant est IMMÉDIAT (pas petit-enfant). Le lien attendu : le parent
    cite ``child/README.md``, l'enfant cite ``../README.md`` (résolu, la
    garde de résolution s'en charge).
    """

    def _edges(self) -> list[tuple[str, str]]:
        """Arêtes (parent, child) où les DEUX portent un README.

        parent == "" désigne le README racine du sous-arbre
        (``argumentation_analysis/README.md``), parent documenté par
        construction (population non vide tenue par la garde racine).
        """
        files = _tracked_files()
        tree = _readme_tree(files)
        edges = []
        for child in sorted(tree):
            parent = child.rsplit("/", 1)[0] if "/" in child else ""
            if parent == "" or parent in tree:
                edges.append((parent, child))
        return edges

    def test_population_floor(self):
        edges = self._edges()
        assert len(edges) >= _MIN_PARENT_CHILD_PAIRS, (
            f"population inattendue : {len(edges)} arêtes parent/enfant "
            f"documentées (plancher {_MIN_PARENT_CHILD_PAIRS}) — re-mesurer "
            "les planchers après un changement de convention"
        )

    def test_parent_links_every_documented_immediate_child(self):
        broken = []
        for parent, child in self._edges():
            readme = (
                f"{SUBTREE}/{parent}/README.md" if parent else f"{SUBTREE}/README.md"
            )
            expected = f"{child.rsplit('/', 1)[-1]}/README.md"
            if (parent, child) in PARENT_OMITS_CHILD:
                continue
            targets = {
                posixpath.normpath(
                    (f"{SUBTREE}/{parent}/" if parent else f"{SUBTREE}/") + t
                )
                for t in _md_link_targets(readme)
            }
            if f"{SUBTREE}/{child}/README.md" not in targets:
                broken.append(f"{readme} ne cite pas {expected}")
        assert broken == [], (
            "#2088 item 5 : parents ne citant pas leur enfant documenté "
            f"immédiat (exclusion nommée requise dans PARENT_OMITS_CHILD) : "
            f"{broken}"
        )

    def test_child_links_its_documented_parent(self):
        broken = []
        for parent, child in self._edges():
            readme = f"{SUBTREE}/{child}/README.md"
            if child in CHILD_OMITS_PARENT:
                continue
            targets = {
                posixpath.normpath(f"{SUBTREE}/{child}/" + t)
                for t in _md_link_targets(readme)
            }
            parent_readme = (
                f"{SUBTREE}/{parent}/README.md" if parent else f"{SUBTREE}/README.md"
            )
            if parent_readme not in targets:
                broken.append(f"{readme} ne back-linke pas {parent_readme}")
        assert broken == [], (
            "#2088 item 5 : enfants sans back-link vers leur parent documenté "
            f"(exclusion nommée requise dans CHILD_OMITS_PARENT) : {broken}"
        )

    def test_named_exclusions_stay_stale_sensitive(self):
        """Une exclusion périmée (lien apparu ou README disparu) rougit.

        Les cartes ne gonflent jamais : chaque entrée nommée doit rester une
        violation réelle de la propriété, sinon elle masque du silence.
        """
        files = _tracked_files()
        tree = _readme_tree(files)
        edges = {(p, c) for p, c in self._edges()}
        for parent, child in PARENT_OMITS_CHILD:
            assert (parent, child) in edges, (
                f"exclusion PARENT_OMITS_CHILD périmée : l'arête "
                f"({parent}, {child}) n'existe plus (README disparu)"
            )
            readme = (
                f"{SUBTREE}/{parent}/README.md" if parent else f"{SUBTREE}/README.md"
            )
            targets = {
                posixpath.normpath(
                    (f"{SUBTREE}/{parent}/" if parent else f"{SUBTREE}/") + t
                )
                for t in _md_link_targets(readme)
            }
            assert f"{SUBTREE}/{child}/README.md" not in targets, (
                f"exclusion PARENT_OMITS_CHILD périmée : {readme} cite "
                f"maintenant {child}/README.md — retirer l'entrée"
            )
        for child in CHILD_OMITS_PARENT:
            parent = child.rsplit("/", 1)[0] if "/" in child else ""
            assert (parent, child) in edges, (
                f"exclusion CHILD_OMITS_PARENT périmée : {child} n'a plus de "
                "parent documenté"
            )
            targets = {
                posixpath.normpath(f"{SUBTREE}/{child}/" + t)
                for t in _md_link_targets(f"{SUBTREE}/{child}/README.md")
            }
            parent_readme = (
                f"{SUBTREE}/{parent}/README.md" if parent else f"{SUBTREE}/README.md"
            )
            assert parent_readme not in targets, (
                f"exclusion CHILD_OMITS_PARENT périmée : {child}/README.md "
                "back-linke maintenant son parent — retirer l'entrée"
            )
        # Les exclusions ne couvrent que des arêtes réelles (déjà tenu par
        # les asserts ci-dessus : une entrée hors arête rouge).
        assert all(
            c in tree for c in CHILD_OMITS_PARENT
        ), "exclusion CHILD_OMITS_PARENT périmée : le README enfant a disparu"
