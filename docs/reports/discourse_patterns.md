# Discourse Pattern Report

**Generated**: 2026-05-04 19:25 UTC
**Documents analyzed**: 8
**Clusters**: 2 (debate, propaganda)
**Workflow**: spectacular 17 phases

---

## 1. Fallacy Spectra by Cluster

| Cluster | ad_hominem | appeal_to_fear | false_dilemma | straw_man |
|---------|---------|---------|---------|---------|
| debate | 0.00 | 0.00 | 0.50 | 0.50 |
| propaganda | 0.50 | 0.50 | 0.00 | 0.00 |

## 2. Tricherie ↔ Influence Asymmetry

| Cluster | Tricherie | Influence | Ratio | Asymmetry |
|---------|-----------|-----------|-------|----------|
| debate | 0.000 | 1.000 | 1000000000.00 | +1.000 |
| propaganda | 0.000 | 1.000 | 1000000000.00 | +1.000 |

## 3. Co-occurrence Top-20

_No co-occurrence data._

## 4. Formal Pattern Detectors

### dung_topology

| Cluster | n_args | n_attacks | density | n_extensions | max_extension_size |
|------|------|------|------|------|------|
| debate | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| propaganda | 2.000 | 1.000 | 0.500 | 0.000 | 0.000 |

### atms_branching

| Cluster | max_assumption_count | avg_assumptions | contradiction_rate |
|------|------|------|------|
| debate | 0.000 | 0.000 | 0.000 |
| propaganda | 0.000 | 0.000 | 0.000 |

### jtms_retraction_rate

| Cluster | n_beliefs | n_justifications | retraction_rate |
|------|------|------|------|
| debate | 1.000 | 1.000 | 0.000 |
| propaganda | 0.000 | 0.000 | 0.000 |

## 5. Cross-coverage: Informal ↔ Formal

| Fallacy Type | Fol_Invalid | Dung_Unsupported | Jtms_Retraction |
|------|------|------|------|
| ad_hominem | 0.00 | 0.00 | 0.00 |
| appeal_to_fear | 0.00 | 0.00 | 0.00 |
| false_dilemma | 1.00 | 0.00 | 0.00 |
| straw_man | 1.00 | 0.00 | 0.00 |

_Rates = fraction of signatures with this fallacy that also exhibit each formal signal._

## 6. Limitations & Next Steps

- Coverage limited to available corpus subset
- Sampling bias toward represented discourse types
- Formal detector registry is extensible (see `pattern_mining.FORMAL_DETECTORS`)
- Future: temporal comparison, richer metadata, LLM-assisted narrative
