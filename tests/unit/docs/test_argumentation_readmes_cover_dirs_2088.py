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

import importlib.util
import posixpath
import re
import subprocess
import sys
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


# #3004 — la règle « substantiel » a TROIS copies : ce module
# (_substantial_dirs), scripts/docs/readme_waves_2088.py (_derive_creations)
# et scripts/docs/inventory_argumentation_readmes.py (_is_substantial /
# _needs_readme). La docstring de CE module AFFIRME l'équivalence avec la
# copie « waves » sans la vérifier. Une dérive ferait VALIDER par cette garde
# un classement que le recensement ne calcule pas — motif #1842, forme
# documentaire (le dépôt porte déjà sa garde pour la variante « capacités »).
#
# Les TROIS copies sont comparées, chacune par sa propre surface : « waves »
# par _derive_creations(), « inventory » par _needs_readme() sur sa propre
# énumération (_tracked_files). La comparaison « inventory » a été JOINTE en
# rework (revue po-2023, R1135) : la déclaration d'angle mort de la première
# version (« B joignable une fois #2998 mergée ») devenait périmée à l'instant
# du merge — #2998 est mergée, _needs_readme est en ligne. Une déclaration
# d'aveuglement n'est honnête que tant que l'aveugle est irréductible ; ici il
# ne l'était plus, donc on joint au lieu de déclarer.
#
# Mesuré 2026-10-09 (main 786729fb3) : les trois s'accordent — « inventory »
# énumère 104 répertoires, 94 substantiels, 0 substantiel sans README, et son
# ensemble égale celui de ce module ; constantes identiques. Risque latent,
# pas défaut vivant.
#
# ⚠ L'égalité de l'arbre réel porte aujourd'hui sur DEUX ENSEMBLES VIDES
# (0 substantiel sans README) : seule, elle ne prouverait rien. Ce qui rend
# cette garde une mesure sont les instances de non-vacuité ci-dessous —
# mesurées, porter le seuil de la copie « waves » à 2 rend son classement NON
# vide et fait rougir SA comparaison ; et sur des FORMES PLANTÉES (population
# synthétique, indépendante de l'arbre), les deux règles sont comparées sur
# le cas même où `ou` et `et` divergent — la dérive de forme, mesurée
# invisible sur l'arbre du jour, y rougit.
# Une garde qui ne peut pas échouer ne mesure pas ; celle-ci le peut.
#
# La dimension « vendorisé » est aujourd'hui INERTE (aucun `libs/`/
# `portable_jdk` suivi sous le sous-arbre) : la muter ne déplace rien, et
# l'angle mort est exactement coextensif à l'absence d'effet. Elle est
# DÉCLARÉE par un fil-piège plutôt que tue (contrat des cartes : on déclare,
# on ne laisse pas de silence).
# Mesuré par grep de CONCEPT (2026-10-09) : la CONSTANTE ``VENDORED_ROOTS`` a
# un QUATRIÈME porteur, ``scripts/docs/link_readme_tree_2088.py``. Il ne porte
# PAS la règle « substantiel » (aucun seuil) mais la même liste vendue, pour
# ses arêtes parent/enfant : la muter chez lui déplacerait les arêtes sans que
# les comparaisons de CLASSEMENT (waves, inventory) le voient. Le test des
# constantes couvre donc les trois copies de la RÈGLE (sous-arbre + seuil) et
# les quatre porteurs de la LISTE.
_WAVES_SCRIPT = "readme_waves_2088.py"
_INVENTORY_SCRIPT = "inventory_argumentation_readmes.py"
_LINK_TREE_SCRIPT = "link_readme_tree_2088.py"


def _load_script(name: str, filename: str):
    """Importe un module de ``scripts/docs/`` par chemin (ce n'est pas un paquet)."""
    spec = importlib.util.spec_from_file_location(
        name, REPO / "scripts" / "docs" / filename
    )
    assert spec is not None and spec.loader is not None, filename
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _substantial_without_readme() -> set[str]:
    """Les répertoires substantiels de CE module qui n'ont pas de README."""
    substantial = _substantial_dirs(_tracked_files())
    return {
        d
        for d, members in substantial.items()
        if f"{SUBTREE}/{d}/README.md" not in members
    }


def _inventory_substantial_without_readme() -> set[str]:
    """Le classement de la copie « inventory », sur SA propre énumération.

    On ne devine pas son univers depuis le nôtre : on lui demande son
    ``_tracked_files()`` et on applique son ``_needs_readme``. Ses clés
    portent le préfixe du sous-arbre (``argumentation_analysis/…``) — la
    normalisation se fait ici pour rendre les deux ensembles comparables.
    """
    inventory = _load_script("inventory_argumentation_readmes", _INVENTORY_SCRIPT)
    return {
        d
        for d, files in inventory._tracked_files().items()
        if inventory._needs_readme(d, files)
    }


def _mine_with_subtree_prefix() -> set[str]:
    """Le classement de ce module, remonté au même espace de noms que B."""
    return {f"{SUBTREE}/{d}" for d in _substantial_without_readme()}


def _classify_mine(files: list[str]) -> set[str]:
    """Notre classement « substantiel sans README » sur une population DONNÉE."""
    substantial = _substantial_dirs(files)
    return {
        f"{SUBTREE}/{d}"
        for d, members in substantial.items()
        if f"{SUBTREE}/{d}/README.md" not in members
    }


def _classify_inventory(population: dict[str, set[str]]) -> set[str]:
    """Le classement de « inventory » sur une population DONNÉE (d → fichiers)."""
    inventory = _load_script("inventory_argumentation_readmes", _INVENTORY_SCRIPT)
    return {d for d, files in population.items() if inventory._needs_readme(d, files)}


# Formes plantées : chaque clé est un répertoire candidat, la valeur ses
# fichiers suivis. Elles exercent la FORME de la règle — le seuil, le `ou`
# contre le `et`, le filtre vendu, la présence du README — indépendamment de
# l'arbre du jour. C'est le contrat que l'inventaire applique déjà pour
# lui-même (``_detection_control`` : « plant the shapes the inventory must
# tell apart, through its own rule »).
#
# Pourquoi planter plutôt que muter un seuil : mesuré, une dérive de FORME
# chez « inventory » (`ou` → `et`) ne déplace RIEN sur l'arbre réel
# d'aujourd'hui — aucun répertoire ne bascule — donc l'égalité de l'arbre la
# laisse passer. ``planted_thick_doc`` existe exactement pour ça : 3 fichiers
# sans `.py`, que le `ou` classe substantiel et le `et` non.
_PLANTED_SHAPES: dict[str, set[str]] = {
    # 1 fichier `.py` : substantiel par le seul volet « .py » (et par le seuil ? non)
    f"{SUBTREE}/planted_light_py": {f"{SUBTREE}/planted_light_py/a.py"},
    # 2 fichiers sans `.py` : léger pour les deux volets (sous le seuil, pas de .py)
    f"{SUBTREE}/planted_light_doc": {
        f"{SUBTREE}/planted_light_doc/a.md",
        f"{SUBTREE}/planted_light_doc/b.md",
    },
    # 3 fichiers sans `.py` : le SEUL point où `ou` et `et` divergent
    f"{SUBTREE}/planted_thick_doc": {
        f"{SUBTREE}/planted_thick_doc/a.md",
        f"{SUBTREE}/planted_thick_doc/b.md",
        f"{SUBTREE}/planted_thick_doc/c.md",
    },
    # substantiel ET documenté : ne compte pas comme « substantiel sans README »
    f"{SUBTREE}/planted_documented": {
        f"{SUBTREE}/planted_documented/a.py",
        f"{SUBTREE}/planted_documented/README.md",
    },
    # vendoré : exclu par les deux règles
    f"{SUBTREE}/libs/planted_vendored": {f"{SUBTREE}/libs/planted_vendored/a.py"},
}


class TestTheSubstantialRuleHasOneDefinition:
    """#3004 : trois copies, aucune ne vérifie les autres — cette garde le fait.

    Elle ne remplace pas les copies par un import unique (trois consommateurs
    distincts, chacune est courte) : elle tient qu'elles CLASSENT pareil, et
    elle nomme pour chacune la surface par laquelle elle la compare.
    """

    def test_the_waves_script_classifies_as_this_module_does(self):
        waves = _load_script("readme_waves_2088", _WAVES_SCRIPT)
        assert waves._derive_creations() == _substantial_without_readme(), (
            "#3004 : readme_waves_2088.py et ce module ne désignent plus les "
            "mêmes répertoires substantiels sans README — la règle a dérivé, "
            "et le recensement valide alors un classement que la garde ne "
            "calcule pas"
        )

    def test_the_inventory_script_classifies_as_this_module_does(self):
        """La 2ᵉ copie est comparée par sa PROPRE surface, pas par ses constantes.

        Comparer seulement les constantes laisserait passer une dérive de
        forme (un `or` devenu `and`, un filtre vendorisé déplacé) : c'est le
        CLASSEMENT qui doit concorder, pas seulement ses ingrédients.
        """
        assert _inventory_substantial_without_readme() == _mine_with_subtree_prefix(), (
            "#3004 : inventory_argumentation_readmes._needs_readme et ce module "
            "ne classent plus pareil — l'inventaire publié désigne des "
            "répertoires que la garde ne voit pas (ou l'inverse)"
        )

    def test_the_three_copies_share_their_constants(self):
        waves = _load_script("readme_waves_2088", _WAVES_SCRIPT)
        inventory = _load_script("inventory_argumentation_readmes", _INVENTORY_SCRIPT)
        expected = (SUBTREE, VENDORED_ROOTS, SUBSTANTIAL_MIN_FILES)
        for name, module in ((_WAVES_SCRIPT, waves), (_INVENTORY_SCRIPT, inventory)):
            got = (module.SUBTREE, module.VENDORED_ROOTS, module.SUBSTANTIAL_MIN_FILES)
            assert (
                got == expected
            ), f"#3004 : {name} porte des constantes différentes ({got} != {expected})"

    def test_the_comparison_detects_a_drifted_threshold(self, monkeypatch):
        """Non-vacuité : la comparaison ci-dessus doit pouvoir ÉCHOUER.

        Mesuré : porter le seuil de la copie « waves » à 2 fait diverger les
        deux classements. Sans cette instance, une garde verte ne dirait pas
        si elle mesure ou si elle ne compare rien.
        """
        waves = _load_script("readme_waves_2088", _WAVES_SCRIPT)
        monkeypatch.setattr(waves, "SUBSTANTIAL_MIN_FILES", 2)
        assert (
            waves._derive_creations() != _substantial_without_readme()
        ), "#3004 : même à seuil divergent les deux classements s'accordent"

    def test_the_two_rules_classify_the_same_planted_shapes(self):
        """La non-vacuité de la comparaison « inventory », sans dépendre de l'arbre.

        Une mutation de seuil sur l'arbre réel prouve qu'un CHIFFRE voyage ;
        elle ne prouve pas que la FORME est comparée. Mesuré : passer le `ou`
        de « inventory » à `et` ne déplace rien sur l'arbre d'aujourd'hui —
        l'égalité de l'arbre reste verte. Les formes plantées, elles, portent
        le cas qui bascule (``planted_thick_doc``), donc la comparaison peut
        ÉCHOUER, et l'assertion de discrimination ci-dessous interdit que la
        population devienne silencieusement inoffensive.
        """
        population = {d: set(files) for d, files in _PLANTED_SHAPES.items()}
        flat = sorted({f for files in population.values() for f in files})

        mine = _classify_mine(flat)
        inventory = _classify_inventory(population)

        assert mine == inventory, (
            "#3004 : sur les formes plantées, les deux règles ne classent plus "
            f"pareil — ce module {sorted(mine)}, « inventory » {sorted(inventory)}"
        )

        # La population doit DISCRIMINER : si elle classait tout ou rien, son
        # égalité serait vacante et le test ne mesurerait rien.
        assert mine, (
            "#3004 : aucune forme plantée n'est classée « substantiel sans "
            "README » — la population ne prouve plus rien, réparer les formes"
        )
        assert len(mine) < len(population), (
            "#3004 : toutes les formes plantées sont classées pareil — plus "
            "aucun contraste, la comparaison ne discrimine plus"
        )
        assert f"{SUBTREE}/planted_thick_doc" in mine, (
            "#3004 : le cas où `ou` et `et` divergent a disparu de la "
            "population plantée — c'est lui qui rend la comparaison sensible "
            "à la forme, pas seulement aux constantes"
        )
        assert (
            f"{SUBTREE}/libs/planted_vendored" not in mine
        ), "#3004 : la forme vendorée n'est plus exclue par ce module"

    def test_the_vendored_list_agrees_across_all_its_holders(self):
        """La liste vendue a QUATRE porteurs (mesuré par grep de concept).

        Les trois copies de la règle, plus ``link_readme_tree_2088.py`` — qui
        n'en porte pas le seuil mais la même liste, pour ses arêtes
        parent/enfant. Une dérive là-bas ne serait vue par aucune autre garde.
        """
        other_holders = (
            (_WAVES_SCRIPT, _load_script("readme_waves_2088", _WAVES_SCRIPT)),
            (
                _INVENTORY_SCRIPT,
                _load_script("inventory_argumentation_readmes", _INVENTORY_SCRIPT),
            ),
            (
                _LINK_TREE_SCRIPT,
                _load_script("link_readme_tree_2088", _LINK_TREE_SCRIPT),
            ),
        )
        for name, module in other_holders:
            assert module.VENDORED_ROOTS == VENDORED_ROOTS, (
                f"#3004 : {name} porte une liste vendue différente "
                f"({module.VENDORED_ROOTS} != {VENDORED_ROOTS})"
            )

    def test_the_vendored_dimension_stays_declared_inert_while_it_is(self):
        """L'angle mort est déclaré, pas silencieux (contrat des cartes).

        Aucun répertoire vendoré suivi sous le sous-arbre aujourd'hui : muter
        ``VENDORED_ROOTS`` ne déplace aucun classement, donc la comparaison
        est aveugle à cette dimension. Ce fil-piège rougit le jour où un tel
        répertoire apparaît — à ce moment l'angle mort devient vivant et la
        comparaison devient sensible sans qu'on ait à y penser.
        """
        files = _tracked_files()
        vendored = sorted(
            {
                f.split("/")[1]
                for f in files
                if f.count("/") >= 2 and f.split("/")[1] in VENDORED_ROOTS
            }
        )
        assert vendored == [], (
            f"#3004 : un répertoire vendoré est maintenant suivi sous "
            f"{SUBTREE}/ ({vendored}) — la dimension vendorisée n'est plus "
            "inerte : vérifier que la comparaison la couvre, puis retirer "
            "ce fil-piège"
        )
