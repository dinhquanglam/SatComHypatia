#!/usr/bin/env python3

import argparse
import csv
import glob
import json
import os
import re
from pathlib import Path

ALGO_TO_K = {
    "algorithm_free_one_only_over_isls": "k=1",
    "algorithm_free_one_only_over_isls3": "k=3",
    "algorithm_free_one_only_over_isls5": "k=5",
}


def parse_args():
    p = argparse.ArgumentParser(
        description=(
            "Compute paper-style average throughput per k from NS-3 runs. "
            "Default behavior uses TCP per-flow average throughput."
        )
    )
    p.add_argument(
        "--runs-dir",
        default="/workspaces/FROGalgorithm-worktree/papier2/ns3_experiments/traffic_matrix_load/runs",
        help="Directory with run_loaded_tm_pairing_* folders",
    )
    p.add_argument(
        "--protocol",
        choices=["tcp", "udp"],
        default="tcp",
        help="Protocol to process (paper table is usually TCP-style)",
    )
    p.add_argument(
        "--out-dir",
        default="/workspaces/FROGalgorithm-worktree/report_artifacts/frog_k/paper_style",
        help="Output directory (CSV/JSON)",
    )
    p.add_argument(
        "--paper-k1",
        type=float,
        default=2.47,
        help="Paper Table II reference throughput for k=1 (Mbit/s)",
    )
    p.add_argument(
        "--paper-k3",
        type=float,
        default=2.65,
        help="Paper Table II reference throughput for k=3 (Mbit/s)",
    )
    p.add_argument(
        "--paper-k5",
        type=float,
        default=2.92,
        help="Paper Table II reference throughput for k=5 (Mbit/s)",
    )
    return p.parse_args()


def read_finished(logs_dir):
    fin = os.path.join(logs_dir, "finished.txt")
    if not os.path.exists(fin):
        return False
    with open(fin, "r") as f:
        return f.read().strip() == "Yes"


def parse_run_meta(run_name):
    m = re.search(r"_for_(\d+)s_with_(tcp|udp)_(algorithm_.+)$", run_name)
    if not m:
        return None
    duration_s = float(m.group(1))
    proto = m.group(2)
    algo = m.group(3)
    return duration_s, proto, algo


def per_flow_throughput_mbps_tcp(tcp_flows_csv, duration_s):
    vals = []
    with open(tcp_flows_csv, "r", newline="") as f:
        for r in csv.reader(f):
            if not r or r[0] == "idx":
                continue
            sent_bytes = float(r[7])
            vals.append((sent_bytes / duration_s) / 125000.0)
    return vals


def per_flow_throughput_mbps_udp(udp_in_csv, duration_s):
    # One row per burst/flow idx in this setup; use payload bytes column 10.
    vals = []
    with open(udp_in_csv, "r", newline="") as f:
        for r in csv.reader(f):
            if not r or r[0] == "idx":
                continue
            payload_bytes = float(r[10])
            vals.append((payload_bytes / duration_s) / 125000.0)
    return vals


def collect_rows(runs_dir, protocol):
    rows = []
    for run in sorted(glob.glob(os.path.join(runs_dir, "run_loaded_tm_pairing_*"))):
        run_name = os.path.basename(run)
        meta = parse_run_meta(run_name)
        if meta is None:
            continue
        duration_s, proto, algo = meta
        if proto != protocol:
            continue
        k = ALGO_TO_K.get(algo)
        if k is None:
            continue

        logs = os.path.join(run, "logs_ns3")
        if not read_finished(logs):
            continue

        if protocol == "tcp":
            p = os.path.join(logs, "tcp_flows.csv")
            if not os.path.exists(p):
                continue
            per_flow = per_flow_throughput_mbps_tcp(p, duration_s)
        else:
            p = os.path.join(logs, "udp_bursts_incoming.csv")
            if not os.path.exists(p):
                continue
            per_flow = per_flow_throughput_mbps_udp(p, duration_s)

        if not per_flow:
            continue

        mean_flow = sum(per_flow) / float(len(per_flow))
        total_goodput = sum(per_flow)
        rows.append({
            "run": run,
            "k": k,
            "protocol": protocol,
            "flows_count": len(per_flow),
            "mean_flow_throughput_mbps": mean_flow,
            "total_goodput_mbps": total_goodput,
        })
    return rows


def summarize(rows, paper_targets):
    by_k = {}
    for r in rows:
        by_k.setdefault(r["k"], []).append(r)

    summary = []
    for k in ["k=1", "k=3", "k=5"]:
        grp = by_k.get(k, [])
        if not grp:
            continue
        mean_of_run_means = sum(x["mean_flow_throughput_mbps"] for x in grp) / float(len(grp))
        mean_total_goodput = sum(x["total_goodput_mbps"] for x in grp) / float(len(grp))
        target = paper_targets.get(k)
        delta_abs = (mean_of_run_means - target) if target is not None else None
        delta_pct = ((delta_abs / target) * 100.0) if target not in (None, 0.0) else None
        summary.append({
            "k": k,
            "runs_count": len(grp),
            "mean_flow_throughput_mbps": mean_of_run_means,
            "mean_total_goodput_mbps": mean_total_goodput,
            "paper_table_throughput_mbps": target,
            "delta_vs_paper_abs_mbps": delta_abs,
            "delta_vs_paper_pct": delta_pct,
        })
    return summary


def write_outputs(out_dir, protocol, rows, summary):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    detail_csv = out / f"paper_style_{protocol}_detail.csv"
    summary_csv = out / f"paper_style_{protocol}_summary.csv"
    summary_json = out / f"paper_style_{protocol}_summary.json"

    with open(detail_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "protocol",
            "k",
            "flows_count",
            "mean_flow_throughput_mbps",
            "total_goodput_mbps",
            "run",
        ])
        for r in rows:
            w.writerow([
                r["protocol"],
                r["k"],
                r["flows_count"],
                r["mean_flow_throughput_mbps"],
                r["total_goodput_mbps"],
                r["run"],
            ])

    with open(summary_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "k",
            "runs_count",
            "mean_flow_throughput_mbps",
            "mean_total_goodput_mbps",
            "paper_table_throughput_mbps",
            "delta_vs_paper_abs_mbps",
            "delta_vs_paper_pct",
        ])
        for s in summary:
            w.writerow([
                s["k"],
                s["runs_count"],
                s["mean_flow_throughput_mbps"],
                s["mean_total_goodput_mbps"],
                s["paper_table_throughput_mbps"],
                s["delta_vs_paper_abs_mbps"],
                s["delta_vs_paper_pct"],
            ])

    with open(summary_json, "w") as f:
        json.dump({"protocol": protocol, "summary": summary}, f, indent=2)

    return detail_csv, summary_csv, summary_json


def main():
    args = parse_args()

    paper_targets = {
        "k=1": args.paper_k1,
        "k=3": args.paper_k3,
        "k=5": args.paper_k5,
    }

    rows = collect_rows(args.runs_dir, args.protocol)
    summary = summarize(rows, paper_targets)
    detail_csv, summary_csv, summary_json = write_outputs(args.out_dir, args.protocol, rows, summary)

    print("k,runs_count,mean_flow_throughput_mbps,mean_total_goodput_mbps,paper_table_throughput_mbps,delta_vs_paper_abs_mbps,delta_vs_paper_pct")
    for s in summary:
        print(
            f"{s['k']},{s['runs_count']},{s['mean_flow_throughput_mbps']:.6f},{s['mean_total_goodput_mbps']:.6f},"
            f"{s['paper_table_throughput_mbps']:.6f},{s['delta_vs_paper_abs_mbps']:.6f},{s['delta_vs_paper_pct']:.2f}"
        )

    print("Wrote detail CSV:", detail_csv)
    print("Wrote summary CSV:", summary_csv)
    print("Wrote summary JSON:", summary_json)


if __name__ == "__main__":
    main()
