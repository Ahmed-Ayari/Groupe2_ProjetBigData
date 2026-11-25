# TITLE: Joint optimisation of resources and partitioning for the analysis of real sensor data (MetroPT-3, UK-DALE)

Authors: TO_FILL | Supervisor: Dr. Chiraz Trabelsi | M2 DSIR, 2026-2027

## Résumé / Abstract
TO_WRITE (FR + EN, after results). Keywords: TO_WRITE.

## 1. Introduction
Context, problem, Q1-Q3, hypotheses H1-H3, scope (single machine, local parallelism), contributions. TO_WRITE.

## Part I
### 2. Foundations
Big data, partitioning, Amdahl, speedup S(p)=T(p0)/T(p), efficiency E=S/(p/p0), size-up, cost C=p x T (core-minutes), memory/network. TO_WRITE.

### 3. State of the art
Table (problem | technique/platform | data | method | calibration cost | metrics | limits).
Starting points: Flora (CCGrid 2025, https://eprints.gla.ac.uk/349741/); Resource Efficiency of Big Data Autoscaling (https://eprints.gla.ac.uk/346542/).
Other >= 6 non-paywalled references since 2023: TO_FIND (do not invent references).
Positioning: precise difference of this work. TO_WRITE.

## Part II
### 4. Contribution
Architecture (docs: src/bigdata), B0 and Spark pipelines, decision algorithm, features, objective min p x T_hat s.t. T_hat + margin <= D, calibration cost. TO_WRITE.

### 5. Experimental study
5.1 Hardware and versions: environment/hardware.json. 5.2 Data and need: docs/audit_metropt3.md, manifests, licences (CC BY 4.0), quality, labels limits.
5.3 Protocol: lots, calibration/test split (manifests/splits.json), B0..B4, repetitions, caches, metrics, stopping criteria.
5.4 Results (each figure: title, axes with units, n trials, interpretation): see docs/report_facts.md and results/figures/*.md.
 - Q1 crossover: fig_time_vs_volume. Q2: fig_partitions_effect, fig_task_times, docs/pilot_diagnosis.md. Q3: fig_final_cost_hit_rate, fig_model_accuracy, results/final_*.csv.
 - Ablation B4 vs B3, failures table, equivalence table, calibration and preparation costs.
 - Data mining: results/metropt_mining.json (detection of an ongoing incident, not prediction).
5.5 Discussion: threats to validity (one machine, one house, OS cache, few lots), socio-economic utility (sourced), sobriety (core-minutes are not kWh/CO2).

### 6. Conclusion and perspectives
Answer to the research question, effective contributions, limits, doctoral perspectives (multi-node: docs/distributed_protocol.md, NOT EXECUTED).

## References and annexes
Datasets with DOI and licence; tools; code, manifest, full grid, raw measures, reproduction guide.
