# Discourse Pattern Report

**Generated**: 2026-05-12 13:20 UTC
**Documents analyzed**: 18
**Clusters**: 1 (unknown)
**Workflow**: spectacular 17 phases

---

## 1. Fallacy Spectra by Cluster

| Cluster | Acte de foi | Angélisme | Appel à l'ignorance assumée | Convaincre le public et non l'adversaire | Coup de pouce | Enthymême invalide | Haptique | Hendiadys | Illusion de regroupement | La pompe à intuitions |
|---------|---------|---------|---------|---------|---------|---------|---------|---------|---------|---------|
| unknown | 0.03 | 0.03 | 0.03 | 0.03 | 0.03 | 0.12 | 0.03 | 0.03 | 0.21 | 0.06 |

## 2. Tricherie ↔ Influence Asymmetry

_No asymmetry data._

## 3. Co-occurrence Top-20

| Fallacy A | Fallacy B | Support | Confidence | Lift | Jaccard |
|-----------|-----------|---------|------------|------|--------|
| Appel à l'ignorance assumée | Polytélie | 1 | 1.000 | 18.00 | 1.000 |
| Haptique | Lancer de soulier | 1 | 1.000 | 18.00 | 1.000 |
| Acte de foi | Coup de pouce | 1 | 1.000 | 18.00 | 1.000 |
| Acte de foi | Misogynie | 1 | 1.000 | 18.00 | 1.000 |
| Coup de pouce | Misogynie | 1 | 1.000 | 18.00 | 1.000 |
| Mauvaise étiquetage | Populisme | 1 | 1.000 | 18.00 | 1.000 |
| Sophisme du faisceau de preuves | Sycophantie | 1 | 1.000 | 9.00 | 0.500 |
| Appel à l'ignorance assumée | La pompe à intuitions | 1 | 1.000 | 9.00 | 0.500 |
| La pompe à intuitions | Polytélie | 1 | 0.500 | 9.00 | 0.500 |
| Convaincre le public et non l'adversaire | Sycophantie | 1 | 1.000 | 9.00 | 0.500 |
| Enthymême invalide | Souffle court | 1 | 0.250 | 4.50 | 0.250 |
| Convaincre le public et non l'adversaire | Enthymême invalide | 1 | 1.000 | 4.50 | 0.250 |
| Enthymême invalide | Hendiadys | 1 | 0.250 | 4.50 | 0.250 |
| Illusion de regroupement | Sophisme du faisceau de preuves | 1 | 0.143 | 2.57 | 0.143 |
| Illusion de regroupement | Souffle court | 1 | 0.143 | 2.57 | 0.143 |
| Illusion de regroupement | Pseudorationalisme | 1 | 0.143 | 2.57 | 0.143 |
| Illusion de regroupement | Mauvaise étiquetage | 1 | 0.143 | 2.57 | 0.143 |
| Illusion de regroupement | Populisme | 1 | 0.143 | 2.57 | 0.143 |
| Hendiadys | Illusion de regroupement | 1 | 1.000 | 2.57 | 0.143 |
| Enthymême invalide | Sycophantie | 1 | 0.250 | 2.25 | 0.200 |

_Units with co-occurrences: 18_

## 4. Formal Pattern Detectors

### dung_topology

| Cluster | n_args | n_attacks | density | n_extensions | max_extension_size |
|------|------|------|------|------|------|
| unknown | 8.000 | 3.000 | 0.054 | 1.000 | 8.000 |

### atms_branching

| Cluster | max_assumption_count | avg_assumptions | contradiction_rate |
|------|------|------|------|
| unknown | 8.000 | 5.330 | 0.000 |

### jtms_retraction_rate

| Cluster | n_beliefs | n_justifications | retraction_rate |
|------|------|------|------|
| unknown | 38.000 | 1.000 | 0.079 |

## 5. Cross-coverage: Informal ↔ Formal

| Fallacy Type | Fol_Invalid | Dung_Unsupported | Jtms_Retraction |
|------|------|------|------|
| Acte de foi | 0.00 | 0.00 | 1.00 |
| Angélisme | 0.00 | 0.00 | 1.00 |
| Appel à l'ignorance assumée | 0.00 | 0.00 | 1.00 |
| Convaincre le public et non l'adversaire | 0.00 | 0.00 | 1.00 |
| Coup de pouce | 0.00 | 0.00 | 1.00 |
| Enthymême invalide | 0.00 | 0.00 | 0.75 |
| Haptique | 0.00 | 0.00 | 1.00 |
| Hendiadys | 0.00 | 0.00 | 0.00 |
| Illusion de regroupement | 0.00 | 0.00 | 0.71 |
| La pompe à intuitions | 0.00 | 0.00 | 1.00 |
| Lancer de soulier | 0.00 | 0.00 | 1.00 |
| Manquement au rasoir d'Hanlon | 0.00 | 0.00 | 1.00 |
| Mauvaise étiquetage | 0.00 | 0.00 | 1.00 |
| Message subliminal | 0.00 | 0.00 | 1.00 |
| Misogynie | 0.00 | 0.00 | 1.00 |
| Persistance | 0.00 | 0.00 | 1.00 |
| Polytélie | 0.00 | 0.00 | 1.00 |
| Populisme | 0.00 | 0.00 | 1.00 |
| Procès d'intention | 0.00 | 0.00 | 1.00 |
| Pseudorationalisme | 0.00 | 0.00 | 1.00 |
| Sophisme du faisceau de preuves | 0.00 | 0.00 | 1.00 |
| Souffle court | 0.00 | 0.00 | 1.00 |
| Sycophantie | 0.00 | 0.00 | 1.00 |

_Rates = fraction of signatures with this fallacy that also exhibit each formal signal._

## 6. Limitations & Next Steps

- Coverage limited to available corpus subset
- Sampling bias toward represented discourse types
- Formal detector registry is extensible (see `pattern_mining.FORMAL_DETECTORS`)
- Future: temporal comparison, richer metadata, LLM-assisted narrative
