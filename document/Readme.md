Below is the link to my document summarizing my understanding of the paper “W1_imc2020-hypatia”:
https://www.notion.so/Week-3-Reading-paper-310d0b1b334d80239416eb2218a45ce3?source=copy_link

<img src="./HYPATIA_ARCHITECTURE.png" alt="Hypatia Architecture" width="600">

## Architecture components

### 1) State generation and routing precomputation (`satgenpy` and `paper/satellite_networks_state`)

The repository’s `paper/satellite_networks_state` scripts orchestrate generation of:

- **(i) Static constellation description files**
- **(ii) Dynamic state over time** (forwarding + optional per-interface bandwidth)

The top-level README in that directory enumerates:

**Static outputs**
- `tles.txt`
- `isls.txt`
- `ground_stations.txt`
- `description.txt`
- `gsl_interfaces_info.txt`

**Dynamic outputs**
- `fstate_<time>.txt`
- `gsl_if_bandwidth_<time>.txt`

The IMC’20 paper describes the same step as:
Users specify satellite trajectory parameters and ground station locations; Hypatia then generates satellite state over time (TLEs), connectivity, and time-varying forwarding state.

---

### 2) Packet-level simulation (`ns3-sat-sim`)

`ns3-sat-sim` builds a satellite-network topology in ns-3 by reading:

- `tles.txt`
- `ground_stations.txt`
- `isls.txt`
- `gsl_interfaces_info.txt`

It then creates nodes, mobility models, ISL/GSL net devices, IP addresses, and ARP cache entries.

During simulation:

- `ArbiterSingleForwardHelper` periodically loads `fstate_<t>.txt` into routing arbiters and schedules the next load at `dynamic_state_update_interval_ns`.
- `GslIfBandwidthHelper` loads `gsl_if_bandwidth_<t>.txt` and adjusts GSL interface data rates based on a configured baseline `gsl_data_rate_megabit_per_s` multiplied by a per-interface `bandwidth_fraction`.

---

### 3) Experiment orchestration and analysis (`paper`)

The `paper` component is effectively a pipeline driver: it describes stepwise reproduction:

1. Generate state
2. Build ns-3 simulator
3. `satgenpy` analysis
4. ns-3 experiments
5. `satviz` figures
6. Plot paper figures

`paper/ns3_experiments` generates run directories and config files, executes ns-3 runs, and then generates plots.

---

### 4) Visualisation (`satviz`)

`satviz` is a script-based pipeline that generates CesiumJS code (HTML files) and requires a Cesium access token placed into:

- `static_html/top.html`

It includes scripts to visualise constellations, paths, and utilisation; the README maps them to paper figures.

Practically, these scripts consume Hypatia outputs such as:

- `networkx_path_...txt` (from `satgenpy` post-analysis)
- `isl_utilization.csv` (from ns-3 runs)

These drive the Cesium renderings.
