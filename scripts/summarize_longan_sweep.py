#!/usr/bin/env python3
"""Aggregate the Longan receive-path sweep into sweep_summary.csv + a manifest.

Mirrors the column shape of artifacts/sim/appendixB_sweeps/sweep_summary.csv
(run,deaths,availability,pdr) so the new rows drop straight into the B.1 table.

MODEL-ONLY: rx_listen_ma / light_sleep_ma in config/sim/wmnf_sim.yaml are
[BENCH-CALIBRATE] placeholders, not measured values.

Usage: python3 scripts/summarize_longan_sweep.py [out_dir]
"""
import csv
import hashlib
import json
import pathlib
import subprocess
import sys

OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else
                   "artifacts/sim/longan_sweep_2026-11-05")
REPO = pathlib.Path(__file__).resolve().parent.parent

INPUTS = ["artifacts/sim/topology_statewide.json",
          "artifacts/sim/routes_statewide.json",
          "artifacts/sim/weather_year.json",
          "config/sim/wmnf_sim.yaml"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    runs = sorted(p for p in OUT.glob("*.json")
                  if p.name not in ("sweep_manifest.json",))
    rows, params = [], {}
    for p in runs:
        d = json.loads(p.read_text())
        fe = d["fleet_energy"]
        s = d["sos"]
        lat = sorted(s.get("latencies_s") or [])
        p95 = (lat[min(len(lat) - 1, int(0.95 * len(lat)))] if lat else None)
        rows.append({"run": p.stem,
                     "deaths": fe["deaths_total"],
                     "availability": fe["availability"],
                     "pdr": d["pdr_overall"],
                     "sos_delivered_frac": (round(s["delivered"] / s["sent"], 4)
                                            if s.get("sent") else None),
                     "sos_p95_s": p95})
        params[p.stem] = {
            "relay_rx_ma": d["resolved_parameters"]["relay_rx_ma_override"],
            "seed": d["seed"], "days": d["days"], "mode": d["mode"],
            "n_nodes": d["n_nodes"], "n_renters": d["n_renters"],
            "start_date": d["start_date"],
            "resolved_parameters": d["resolved_parameters"],
            "sha256": sha256(p)}

    with open(OUT / "sweep_summary.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, ["run", "deaths", "availability", "pdr",
                                "sos_delivered_frac", "sos_p95_s"])
        w.writeheader()
        w.writerows(rows)

    manifest = {
        "purpose": "Longan-class ultra-low-power receive path added to the "
                   "Appendix B.1 listen-current sweep. MODEL-ONLY; listen and "
                   "sleep currents are [BENCH-CALIBRATE] placeholders.",
        "hardware_reference": "Longan: Ultra-Low-Power, Long-Range LoRa "
                              "Receiver for LPWANs, SenSys '26, "
                              "https://doi.org/10.1145/3774906.3802753 "
                              "(~1 mW receive vs up to 42.4 mW Class C)",
        "power_basis": {
            "battery_v": 3.7,
            "source": "config/sim/wmnf_sim.yaml:46 (energy.battery_v)",
            "conversion_site": "fastsim/src/engine2.rs:809 @31f422a "
                               "(listen_s * listen_ma / 1000.0 * battery_v)",
            "mw_to_ma": {"0.5 mW": 0.1351, "1.0 mW": 0.2703, "2.0 mW": 0.5405}},
        "engine_git_head_source": "31f422a (Appendix B.1 engine, per "
                                  "artifacts/sim/appendixB_sweeps/"
                                  "sweep_manifest.json)",
        "engine_build": "git archive 31f422a fastsim | tar -x -C /tmp/fastsim-b1; "
                        "DEVELOPER_DIR=/Library/Developer/CommandLineTools "
                        "cargo build --release (rustc 1.89.0 Homebrew)",
        "repo_git_head": subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
            capture_output=True, text=True).stdout.strip(),
        "base_inputs": "release_v1 frozen inputs (hashes below match "
                       "artifacts/sim/corrected/release_v1/input_hashes.txt)",
        "input_sha256": {p: sha256(REPO / p) for p in INPUTS},
        "runs": params,
    }
    (OUT / "sweep_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")

    for r in rows:
        print(f"{r['run']:40s} deaths={r['deaths']:>6} "
              f"avail={r['availability']:.4f} pdr={r['pdr']:.4f} "
              f"sos={r['sos_delivered_frac']} p95={r['sos_p95_s']}s")


if __name__ == "__main__":
    main()
