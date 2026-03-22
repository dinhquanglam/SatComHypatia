# Explicit Report: FROG K Comparison

Date: 2026-03-22 (UTC)
Scope: Current artifacts under `report_artifacts/frog_k/`

## 1) Path-Length Impact (Hop Count)
Source: `frog_k_summary.json`, `frog_k_summary.csv`

| Comparison | Pairs | Shorter Paths | Worse Paths | Equal Paths | Baseline Mean Hops | Candidate Mean Hops | Mean Hop Reduction | Reduction (%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| k=3 vs k=1 | 100 | 14 | 0 | 86 | 10.58 | 9.10 | 1.48 | 13.99% |
| k=5 vs k=1 | 100 | 24 | 0 | 76 | 10.58 | 8.08 | 2.50 | 23.63% |

Explicit finding: both `k=3` and `k=5` reduce mean hop count with **zero worse paths** in this 100-pair sample.

## 2) Traffic Matrix Performance Summary
Source: `traffic_matrix/frog_k_compare_summary.csv`, `traffic_matrix/frog_k_compare_vs_k1.csv`

### TCP
| Metric | k=1 | k=3 | k=5 |
|---|---:|---:|---:|
| Mean goodput (Mbps) | 166.274 | 172.228 | 175.698 |
| Mean slowdown | 18.618 | 18.244 | 17.290 |

Explicit deltas vs k=1:
- `k=3`: goodput **+3.58%**, slowdown **-2.01%**
- `k=5`: goodput **+5.67%**, slowdown **-7.14%**

### UDP
| Metric | k=1 | k=3 | k=5 |
|---|---:|---:|---:|
| Mean goodput (Mbps) | 98.074 | 98.656 | 98.857 |
| Mean slowdown | 7.403 | 6.520 | 4.964 |

Explicit deltas vs k=1:
- `k=3`: goodput **+0.59%**, slowdown **-11.93%**
- `k=5`: goodput **+0.80%**, slowdown **-32.95%**

## 3) Paper-Style TCP Throughput Check
Source: `paper_style/paper_style_tcp_summary.json`

| K | Mean Flow Throughput (Mbps) | Paper Table Throughput (Mbps) | Delta (Abs Mbps) | Delta (%) |
|---|---:|---:|---:|---:|
| k=1 | 1.663 | 2.470 | -0.807 | -32.68% |
| k=3 | 1.722 | 2.650 | -0.928 | -35.01% |
| k=5 | 1.757 | 2.920 | -1.163 | -39.83% |

Explicit finding: current reproduced TCP flow-throughput values are below paper table values for all tested `k` settings.

## 4) Direct Conclusion
- Increasing `k` from 1 to 3 and 5 improves routing efficiency (lower hops) and does not introduce worse paths in the sampled set.
- For traffic matrix runs, both TCP and UDP show goodput gains and slowdown reductions as `k` increases, with strongest slowdown benefit in UDP at `k=5`.
- Paper-style throughput alignment remains incomplete; reproduced per-flow TCP throughput is 32.68% to 39.83% below table targets.

## 5) Referenced Files
- `report_artifacts/frog_k/frog_k_summary.json`
- `report_artifacts/frog_k/frog_k_summary.csv`
- `report_artifacts/frog_k/traffic_matrix/frog_k_compare_summary.csv`
- `report_artifacts/frog_k/traffic_matrix/frog_k_compare_vs_k1.csv`
- `report_artifacts/frog_k/paper_style/paper_style_tcp_summary.json`
