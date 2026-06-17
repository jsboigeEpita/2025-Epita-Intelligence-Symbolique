# AUDIT #1151 — Contrats lecteur↔writer des actes de restitution

**Epic #1134 (Restitution)** — Audit read-only track #1151. Worker
`myia-po-2023`, dispatch coordinateur R431. Extension naturelle du diagnostic
#1149 (Finding A : bug de schéma silencieux `scores` vs `scores_par_vertu`).

**Lane file-disjoint des actes** (po-2025 owns les 5 fichiers infra + les
plugins d'acte pour R4/R6). **Zéro edit** dans ce track — audit pur, correctifs
proposés localisés (sérialisés dans la lane actes).

**Privacy HARD** : IDs opaques uniquement (`arg_N`, `corpus_A`). Aucun nom de
source, aucun `raw_text`. Reproduction déterministe (0 LLM, 0 JVM, 0 dataset) —
l'audit porte sur le *shape* du state, pas son contenu.

---

## TL;DR

**3 mismatches prouvés (tous silencieux, type Finding A) + 5 contrats sains.**
L'audit confirme que Finding A n'était **pas unique** : le même anti-pattern
(clé writer ≠ clé reader, dégradation sans fail-loud) frappe l'axe **PL
formel** (perte totale des verdicts PL tissés) et, plus mineurement, l'étiquette
**sémantique Dung**. Deux contrats (fallacy, counter_argument, FOL, stakes) sont
sains. Le gate `quality_axis_available = bool(dict)` (leçon #1150) ne détecte
**aucun** de ces 3 bugs car ils portent sur le *contenu*, pas la *présence*.

| # | Contrat | Writer (clé/fichier:ligne) | Reader (clé/fichier:ligne) | Impact | Gravité |
|---|---------|----------------------------|----------------------------|--------|---------|
| A | qualité vertus | `scores` shared_state.py:536 | `scores_par_vertu` act2:295 | vertus **toujours** `{}` | **HIGH** |
| C | verdict PL | `satisfiable` shared_state.py:801 | `consistent` act2:346 | PL findings **jamais** collectés | **HIGH** |
| D | sémantique Dung | (non stocké) shared_state.py:566 | `semantics` act2:167 | rejet détecté mais **mal étiqueté** `grounded` | LOW |
| — | fallacy | `type/family/justification/target_argument_id/taxonomy_path` shared_state.py:120-131 | idem act2:224-238 | ✅ sain | — |
| — | counter_argument | `target_arg_id/strategy/counter_content` shared_state.py:504-512 | idem act2:246-253 | ✅ sain | — |
| — | verdict FOL | `consistent` shared_state.py:779 | `consistent` act2:372 | ✅ sain | — |
| — | stakes | écriture directe `_invoke_stakes_extractor:6788` | `stakes/stakeholders/rhetorical_register/discursive_arena` act1:305-313 | ✅ sain (clés match) | — |
| — | source_metadata | (aucun writer de phase ; bootstrap dataset) | getattr act1:289 | ✅ sain (dégrade honnêtement si vide) | — |

---

## 1. Méthode

Pour chaque reader d'acte (`act1_framing_plugin.build_act1_evidence`,
`act2_narrative_plugin.build_act2_evidence` + helpers
`_collect_formal_findings`, `_dung_rejected_by_arg`) : lister les clés state
lues via `getattr`/`.get()`, puis tracer le writer correspondant
(`state_writers.py` → `shared_state.add_*` ou écriture directe dans
`invoke_callables.py`). Vérifier **deux niveaux** :

1. **Attribut** : `add_X` peuple-t-il `state.<attr>` sous le nom lu par le reader ?
2. **Sous-schéma** : la clé interne stockée matche-t-elle le `.get()` du reader ?

Reproduction déterministe : `.cache/_audit1151_contract_probe.py` isole chaque
writer→reader (0 LLM/JVM/dataset). Les 3 mismatches sont prouvés par probe
contrastif (le contrat sain adjacent — ex. FOL pour C — collecte bien son
finding, prouvant que la clé est la cause).

## 2. Les 3 mismatches prouvés

### Finding A — qualité : `scores` vs `scores_par_vertu` (HIGH, déjà #1150)

- **Writer** `add_quality_score` (`shared_state.py:535-541`) stocke
  `{"scores": scores, "overall": overall}`.
- **Reader** `build_act2_evidence` (`act2_narrative_plugin.py:295`) lit
  `qs.get("scores_par_vertu")`.
- **Repro** : `argument_quality_scores['arg_1'] = {'scores': {...}, 'overall': 1.83}`
  → reader `scores_par_vertu` → `None` → `virtues = {}`.
- **Impact** : `overall` match (correct), mais le détail per-vertu est perdu
  **silencieusement** partout. `quality_axis_available` reste `True` (dict
  non-vide) → pas de fail-loud.
- **Fix** (déjà proposé #1150, foldé dans R4) : reader lit
  `qs.get("scores") or qs.get("scores_par_vertu")`.

### Finding C — verdict PL : `satisfiable` vs `consistent` (HIGH, NOUVEAU)

- **Writer** `add_propositional_analysis_result` (`shared_state.py:798-803`)
  stocke `{"formulas": ..., "satisfiable": satisfiable, "model": ...}`.
- **Reader** `_collect_formal_findings` (`act2_narrative_plugin.py:346`) lit
  `r.get("consistent") is True` / `r.get("consistent") is False`.
- **Repro contrastif** :
  - PL (`satisfiable=True` stocké) → reader `consistent` → `None` →
    `is True` False → **0 finding collecté** (devrait être 1).
  - FOL (`consistent=False` stocké, `add_fol_analysis_result:779`) → reader
    `consistent` → `False` → **1 finding collecté** ✅.
  - Le contraste PL=0 / FOL=1 prouve que la clé est la cause exacte.
- **Impact** : l'Acte II **ne cite jamais de verdict PL comme preuve formelle**
  (DoD (c) « verdicts formels cités sont réels » — ici ils sont *absents*, pas
  faux). Silencieux : `findings=[]` n'est pas une erreur.
- **Fix localisé** (reader-side, append-only, fichier act2 — sérialiser derrière
  R4) : `_collect_formal_findings` lit la clé PL réelle :

  ```python
  # act2_narrative_plugin.py, bloc PL (~ligne 346) :
  sat = r.get("consistent")
  if sat is None:
      sat = r.get("satisfiable")   # canonical PL key
  consistent += 1 if sat is True else 0
  inconsistent += 1 if sat is False else 0
  ```

  (Bidirectionnel défensif : `consistent` legacy + `satisfiable` canonical PL.
  Préserve la sémantique booléenne stricte `is True`/`is False` pour ignorer
  le `None` non-vérifié — ne PAS utiliser `bool(sat)` qui confondrait
  inconnu/inconsistant, #1019.)

### Finding D — sémantique Dung : étiquette absente (LOW, NOUVEAU)

- **Writer** `add_dung_framework` (`shared_state.py:566-571`) stocke
  `{"name", "arguments", "attacks", "extensions"}` — **aucune clé `semantics`**
  (le writer `_write_dung_extensions_to_state` plie la sémantique dans
  `name=f"verification_{semantics}"`, state_writers.py:717).
- **Reader** `_dung_rejected_by_arg` (`act2_narrative_plugin.py:167`) lit
  `fw.get("semantics", "grounded")` → toujours `"grounded"`.
- **Repro** : framework `preferred` avec `arg_1` rejeté →
  `_dung_rejected_by_arg = {'arg_1': 'grounded'}` (au lieu de `'preferred'`).
- **Impact** : la **détection** de rejet fonctionne (clés `arguments`/`extensions`
  matchent) — seul le **label sémantique** est faux (`grounded` partout). Mineur
  (le rejet est surfacé ; l'étiquette est cosmétique), mais réel.
- **Fix localisé** (writer-side, append-only — `add_dung_framework` est un des 5
  fichiers infra verrouillés → sérialiser) : `add_dung_framework` accepte et
  stocke un `semantics` optionnel, et `_write_dung_extensions_to_state:717` le
  passe. **OU** reader-side (act2:167) parse depuis `name` :
  `semantics = fw.get("semantics") or fw.get("name","").replace("verification_","")`.
  Le reader-side est préférable (pas d'edit infra) — 1-liner act2.

## 3. Contrats sains (vérifiés, aucun mismatch)

- **Fallacy** : `add_fallacy` (`shared_state.py:120-131`) stocke
  `type/justification/family/taxonomy_path/target_argument_id` → reader act2
  (`:224-238`) lit exactement ces clés. ✅
  *Note* : un sophisme dont `target_arg_id` est `None` (résolution échouée dans
  `_write_hierarchical_fallacy_to_state:395`) n'est pas stocké avec
  `target_argument_id` → reader act2 (`:224-226`) le **skip** (n'entre dans aucun
  mouvement, y compris `soutiens`). Décision de résolution, pas un mismatch —
  mais à surveiller : un sophisme non-résolu est **silencieusement abandonné** du
  fil mouvement.
- **Counter-argument** : `add_counter_argument` (`:504-512`) stocke
  `target_arg_id/strategy/counter_content` → reader act2 (`:246-253`) match. ✅
- **Verdict FOL** : `add_fol_analysis_result` (`:776-782`) stocke `consistent`
  → reader act2 (`:372`) match. ✅ (contraste sain qui prouve Finding C.)
- **Stakes** : `_invoke_stakes_extractor` (`invoke_callables.py:6788`) écrit
  `state.stakes_and_stakeholders = result` directement (contourne le writer
  dict — `stakes_extraction` n'est PAS dans `CAPABILITY_STATE_WRITERS`). Le
  `result` expose `stakes/stakeholders/rhetorical_register/discursive_arena`
  (le callable lui-même `.get()` ces clés `:6790-6793`) → reader act1
  (`:305-313`) match. ✅
  *Note* : `_invoke_stakes_extractor:6759` fait
  `list(getattr(state, "identified_arguments", []))` sur un **dict** → récupère
  les **clés** (arg_ids), pas les descriptions. Bug d'input-quality du writer
  interne (hors contrat reader↔writer strict), à confirmer séparément.
- **source_metadata** : aucun writer de phase ; peuplé au bootstrap dataset.
  Reader act1 (`:289`) dégrade honnêtement (`"contexte non renseigné"`) si vide. ✅

## 4. Checklist de contrat réutilisable (R4 Acte III + R6 wiring)

Pour tout nouveau reader d'acte (Acte III `act3_conclusion`) ou wiring R6 :

- [ ] **Attribut match** : pour chaque `getattr(state, "<key>")` du reader,
      grep `self.<key> =` dans `shared_state.py` → confirmer l'attribut existe
      et est peuplé (par `add_*` ou écriture directe). Si l'attribut n'existe
      pas → bug.
- [ ] **Writer attaché** : si l'attribut est peuplé par une phase, confirmer sa
      capability est dans `CAPABILITY_STATE_WRITERS` (sinon le writer **n'est
      jamais appelé** — voir `stakes_extraction` qui contourne par écriture
      directe). Si ni writer ni écriture directe → attribut reste au default.
- [ ] **Sous-schéma match** : pour chaque `.get("<subkey>")` du reader, ouvrir
      l'`add_*` correspondant → confirmer la sous-clé stockée. Lister
      littéralement les clés du dict stocké vs les `.get()` du reader.
- [ ] **Gate contenu** : le `*_available`/`*_axis_available` doit vérifier le
      **contenu utilisable** (sous-clés non-vides), pas `bool(dict)`. Voir §5.
- [ ] **Contraste sain** : si un axe cousin existe (ex. FOL pour PL), le probe
      doit montrer le cousin sain collectant son finding — prouve que la clé
      divergente est la cause.
- [ ] **Fail-loud sur contenu vide** : un reader qui reçoit un attribut non-vide
      mais au contenu inutilisable doit **fail-loud** (status degraded), pas
      silently produire un beat appauvri. (Leçon Finding A/C : dégradation
      silencieuse = anti-pattern #1019.)

## 5. Reco gate « contenu utilisable » (leçon #1150 + #1151)

Le gate actuel `quality_axis_available = bool(quality) and isinstance(quality, dict)`
(`act2_narrative_plugin.py:210`) ne détecte **aucun** des 3 bugs : le dict est
non-vide, donc `True`. La richesse est perdue silencieusement.

**Reco** (calibrée, pas sur-strict — anti-pendule) : le gate devrait vérifier
qu'au moins **une entrée a un contenu utilisable** (overall ET/OU vertus
non-vides), pas juste `bool(dict)`. Mais **calibrer sur le vrai schéma** :

```python
def _quality_usable(qs: dict) -> bool:
    """True iff at least one scored arg has a usable overall or virtues."""
    for entry in qs.values():
        if not isinstance(entry, dict):
            continue
        if entry.get("overall") is not None or entry.get("scores"):
            return True
    return False
```

**Anti-sur-strict** : ne PAS exiger *toutes* les vertus peuplées (certains args
sont courts/dégradés et n'ont qu'un overall). Ne PAS fail-loud si une seule
entrée est inutilisable (dégrader cette entrée, pas l'axe). Le gate reste
**binaire au niveau axe** (available / non-concluable) mais basé sur l'existence
d'au moins un score utilisable, pas sur `bool(dict)`.

**Attention** : ce gate-fix n'est pertinent **qu'après** le fix Finding A (sinon
`virtues` est toujours vide → le gate vérifierait `overall` seul, ce qui marche
déjà). Prioriser A/C/D d'abord, gate ensuite.

## 6. DoD checklist

- [x] **Table lecteur→clé-lue vs writer→clé-écrite** pour act1 + act2
      (+ helpers formels) — §tableau TL;DR + §2/§3.
- [x] **Mismatches prouvés** (Finding A déjà #1150, C + D nouveaux, preuve ligne
      exacte + repro contrastif) — §2. Absence honnête pour les 5 contrats sains
      — §3.
- [x] **Checklist réutilisable R4/R6** — §4.
- [x] **Reco gate contenu utilisable** (calibré pas sur-strict) — §5.
- [x] **Zéro edit** fichiers infra/plugins (audit pur).

## 7. Leçons (REUSABLE)

- **Un schema mismatch = un bug silencieux** : `*_available = bool(dict)` ne
  détecte jamais un bug de sous-clé. Le gate doit checker le contenu. (Prolonge
  #1150 leçon.)
- **Contraste sain = preuve** : le FOL sain (collecte son finding) à côté du PL
  cassé (0 finding) prouve que la clé divergente est la cause — réutilisable
  comme pattern de probe pour tout futur audit de contrat.
- **`add_*` ne stocke pas toujours ce que le reader lit** : toujours ouvrir
  l'`add_*` (pas juste le writer `state_writers.py`) pour voir les vraies clés
  du dict stocké. Le PL `satisfiable` vs `consistent` n'était visible qu'en
  lisant `add_propositional_analysis_result`, pas le writer wrapper.

## 8. Artefacts

- Probe de reproduction (throwaway, gitignored) :
  `.cache/_audit1151_contract_probe.py`.
- **Ce rapport** (committed, opaque) :
  `docs/reports/AUDIT_1151_READER_WRITER_CONTRACTS.md`.
