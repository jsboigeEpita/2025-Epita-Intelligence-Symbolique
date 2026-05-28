# Analyse argumentative — `corpus_A`

> Bundle terminal Epic #717 — clôture du livrable « Présentable d'abord ».
> Re-run capstone PR #726 sur main `1b2021a3`, chemin `dag_spectacular`.
> Hand-curé pour respect de la discipline « privacy / opaque IDs only ».

---

## 1. Identifiant et contexte

| Champ | Valeur |
|-------|--------|
| Opaque ID | `corpus_A` |
| Registre | discours institutionnel d'une autorité nationale devant une assemblée plurinationale |
| Thèse centrale | légitimation d'une politique de fermeture (souveraineté, frontières, énergie traditionnelle) contre un ordre supranational présenté comme défaillant |
| Époque | XXIᵉ siècle, période contemporaine |
| Longueur | 58 052 caractères / ~8 350 mots |
| Langue d'origine | EN (analyses produites en EN et FR) |

---

## 2. Synthèse qualitative

Le texte déploie une stratégie rhétorique **contrastive et polarisante** : un état passé idéalisé (« paix forgée sur deux continents », économie « la plus forte de toutes les nations ») est opposé à un présent menacé par des forces internes (administration précédente, immigration, énergies « renouvelables ») et à une institution supranationale présentée comme inefficace. Cette mise en scène fonctionne par **enchaînement d'appels affectifs** (fierté nationale, panique morale, nostalgie d'un âge d'or) plutôt que par démonstration probante.

Les **contre-arguments mordent là où la stratégie est la plus exposée** : la sélection probante. Le contre-argument le plus fort (score 0,58, stratégie *counter-example*) cible l'inférence « performance boursière record ⇒ succès économique global », et propose un contre-exemple historique précis où les marchés ont battu des records pendant que les salaires médians stagnaient — exactement la faille que la sélection d'indicateurs cherche à masquer. Les autres contre-arguments à forte note (0,53-0,56) ciblent l'attribution causale unilatérale (réussite/échec ⇒ une seule administration) et la rhétorique des superlatifs (« âge d'or ») par *reductio ad absurdum*.

Le **diagnostic informel et le diagnostic formel convergent** sur les arguments les plus faibles. Sur les **10 arguments signalés par au moins deux méthodes indépendantes**, l'argument d'ouverture cumule **4 verdicts concordants** : score qualité 0/10, contre-argument solide opposé, croyance **retractée par le JTMS**, et **rejet par la sémantique Dung *grounded*** sur un cadre de 10 arguments et 13 attaques. Six croyances au total sont retractées par la maintenance de vérité — un signal que les chaînes inférentielles construites s'effondrent une fois confrontées à leurs contradictions internes.

Le diagnostic des sophismes répartit les 13 occurrences confirmées sur **5 familles** issues du CSV taxonomique : *Relevance* (appels à la fierté, à la panique morale), *Insuffisance* (sophisme affectif, tromperie implicite, surinterprétation), *Erreur de raisonnement* (acte de foi, enthymème invalide), *Erreur mathématique* (statistiques manipulées) et *other* (cueillette de cerises, auxèse, argument d'accomplissement). La famille *Insuffisance* domine les passages économiques, *Relevance* domine l'ouverture et les passages migratoires.

---

## 3. Conclusion

Le texte construit une **légitimation de la fermeture souveraine** en s'appuyant sur la **sélection probante et l'appel affectif polarisant**, **au prix de l'imputation causale unilatérale et de la rétraction de six chaînes inférentielles** par la maintenance de vérité.

---

## 4. Détail quantitatif

| Axe | Valeur |
|-----|--------|
| Arguments identifiés | 136 |
| Sophismes confirmés (5 familles CSV) | 13 |
| — dont *Relevance* | 2 |
| — dont *Insuffisance* | 3 |
| — dont *Erreur de raisonnement* | 2 |
| — dont *Erreur mathématique* | 1 |
| — dont *other* (taxonomies périphériques) | 5 |
| Contre-arguments générés | 23 |
| Score CA le plus haut | 0,58 (*counter-example*) |
| Formules PL Tweety-vérifiées | 39 |
| Formules FOL Tweety-vérifiées | 42 |
| Arguments convergents (≥ 2 méthodes) | 10 |
| Profondeur de convergence maximale | 4 méthodes sur un même argument |
| Croyances retractées par JTMS | 6 |
| Cadre Dung — arguments | 10 |
| Cadre Dung — attaques | 13 |

**Comparaison vs 0-shot LLM (mêmes corpus, même modèle)** :

| Axe | DAG (multi-agents) | 0-shot | Verdict |
|-----|-------------------:|-------:|:-------:|
| Contre-arguments | **23** | 15 | DAG Win |
| Formules PL vérifiées | **39** | 14 | DAG Win |
| Formules FOL vérifiées | **42** | 8 | DAG Win |

---

## 5. Extraits citationnels (5 max, généralisés)

> *Citations courtes paraphrasées et anonymisées — la formulation originale a été lissée pour effacer les marqueurs d'identification individuelle tout en préservant la structure argumentative.*

**E1 — Nostalgie d'un état idéal** (cadre rhétorique d'ouverture)
> « Une époque de calme et de prospérité a été rompue ; il faut revenir à ce qui fut. »
> *— argumentation par contraste temporel ; trace : *Sophisme affectif* (depth 3).*

**E2 — Énumération comme preuve** (cadre de légitimation par force)
> « Économie, frontières, armée, alliances, esprit : nous sommes les premiers sur chacun. »
> *— appel à la fierté ; superlatifs en parallélisme ; relevance fallacy.*

**E3 — Indicateur unique ⇒ conclusion globale** (cadre économique)
> « Les records boursiers répétés démontrent à eux seuls la santé économique. »
> *— surinterprétation + statistiques manipulées + enthymème invalide ; cible du CA le plus fort (0,58).*

**E4 — Imputation causale binaire** (cadre de désignation)
> « L'administration précédente est responsable de quatre années de désordre. »
> *— personnalisation ; CA *concession+pivot* (0,54) opposé.*

**E5 — Panique morale géopolitique** (cadre migratoire / énergétique)
> « Si vous ne fermez pas vos frontières et n'abandonnez pas cette politique énergétique, votre pays va mourir. »
> *— appel à la panique morale ; CA *distinction* opposé.*

---

## 6. Métadonnées run (reproductibilité)

| Champ | Valeur |
|-------|--------|
| Branche | `main` @ `1b2021a3` (PR #726 mergée) |
| Chemin évalué | `dag_spectacular` (sequential DAG via WorkflowExecutor) |
| Script | `scripts/measure_both_paths_vs_zeroshot.py --corpus A --with-deep-synthesis` |
| Wrapper | `scripts/run_ff_showcase.sh` |
| LLM | `gpt-5-mini` (via OpenRouter, toggle #675) |
| Taxonomie sophismes | CSV `Famille` (7 familles, propagation #714) |
| Synthèse finale | DeepSynthesisAgent 6 sections (briefing politique, WW #725) |
| Traces specialists | `state.analysis_trace` (10 entrées / 8 specialists, UU #724) |
| Date du run | 2026-05-27 |
| Sections du rapport peuplées | 8 / 9 |
| State fields consommés par la synthèse | 482 |

---

## Annexe — Lecture du livrable

Ce bundle est volontairement **agrégé**. Il démontre que la stack produit :
- une **synthèse qualitative narrative** avant les tables de chiffres (mandat 2026-05-26),
- une **convergence inter-méthodes** absente d'une passe LLM monolithique (10 arguments concordants, profondeur 4),
- un **diagnostic anchored** dans la taxonomie CSV (5 familles, *Famille* propagée de bout en bout depuis #714),
- une **conclusion politique** en une phrase qui restitue les enjeux, les ressorts et le coût argumentatif (mandat R241).

Les comparaisons multi-corpus (`B`, `C`) et les variantes `conversational` sont disponibles dans le run capstone PR #726 ; ce bundle n'en retient qu'un échantillon représentatif pour la clôture lisible de l'Epic #717.
