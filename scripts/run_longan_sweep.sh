#!/bin/bash
# Longan-class ultra-low-power receive-path extension of Appendix B.1
# (listen-current sensitivity sweep). MODEL-ONLY: rx_listen_ma / light_sleep_ma
# in config/sim/wmnf_sim.yaml are [BENCH-CALIBRATE] placeholders, not measured.
#
# Reproduces the B.1 invocation exactly (fastsim defaults + --mode energy_aware
# + --relay-rx-ma N), on the release_v1 frozen inputs, 365 days.
#
# The engine is built from the Appendix B.1 commit 31f422a (the manifest's
# engine_git_head), extracted with `git archive` so no git state is touched:
#   rm -rf /tmp/fastsim-b1 && mkdir -p /tmp/fastsim-b1
#   git archive 31f422a fastsim | tar -x -C /tmp/fastsim-b1
#   (cd /tmp/fastsim-b1/fastsim && \
#      DEVELOPER_DIR=/Library/Developer/CommandLineTools cargo build --release)
#
# Usage: scripts/run_longan_sweep.sh [out_dir]
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-artifacts/sim/longan_sweep_2026-11-05}"
BIN="${FASTSIM_BIN:-/tmp/fastsim-b1/fastsim/target/release/fastsim}"
CFG="config/sim/wmnf_sim.yaml"
TOPO="artifacts/sim/topology_statewide.json"
ROUTES="artifacts/sim/routes_statewide.json"
WEATHER="artifacts/sim/weather_year.json"

[ -x "$BIN" ] || { echo "build the B.1 engine first (see header)"; exit 1; }
mkdir -p "$OUT"

run() {  # run <tag> <relay_rx_ma> <seed>
  local tag="$1" ma="$2" seed="$3" t0 t1
  t0=$(date +%s)
  "$BIN" --topology "$TOPO" --routes "$ROUTES" --weather "$WEATHER" \
    --config "$CFG" --days 365 --seed "$seed" --mode energy_aware \
    --relay-rx-ma "$ma" --out "$OUT/${tag}.json" >/dev/null 2>&1
  t1=$(date +%s)
  echo "${tag},${ma},${seed},$((t1 - t0))" >> "$OUT/runtimes.csv"
}

echo "run,relay_rx_ma,seed,wall_s" > "$OUT/runtimes.csv"

# Longan bracket: 1 mW / 3.7 V = 0.2703 mA (0.5 and 2.0 mW as the bracket),
# plus the published 2 mA nRF52-class row as a control, on B.1's seeds 42/43/44.
i=0
for S in 42 43 44; do
  run "longan_p5mw_rxma0p1351_s${S}" 0.1351 "$S" &
  run "longan_1mw_rxma0p2703_s${S}"  0.2703 "$S" &
  run "longan_2mw_rxma0p5405_s${S}"  0.5405 "$S" &
  run "ctl_rxma2_s${S}"              2      "$S" &
  i=$((i + 4))
  [ $((i % 8)) -eq 0 ] && wait
done
wait
echo "ran $i longan-sweep runs into $OUT"
