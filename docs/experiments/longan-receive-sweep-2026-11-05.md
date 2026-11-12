# Longan-class receive path added to the Appendix B.1 listen-current sweep

**Date:** 2026-11-05
**Status:** MODEL-ONLY, uncalibrated. Not part of the submitted report.
**Scope:** extends Appendix B.1 of `reports/directed-study-report-2026-08-03.md`
(lines ~693–736) with a sub-2 mA receive-current series representing a
Longan-class ultra-low-power LoRa receiver. The submitted report is unmodified.

> **All numbers here are model output, not measurement.** `rx_listen_ma`
> (68 mA) and `light_sleep_ma` (12 mA) in `config/sim/wmnf_sim.yaml` are
> explicitly tagged `[BENCH-CALIBRATE]` — community/datasheet composites, never
> measured on our own hardware. The Longan rows inherit that status and add a
> second layer of modelling assumption (see §2 caveats). Nothing below is
> evidence about physical hardware.

**Hardware reference.** Longan: Ultra-Low-Power, Long-Range LoRa Receiver for
LPWANs, SenSys '26, <https://doi.org/10.1145/3774906.3802753>. Per its
abstract: kilometer-scale links at **about 1 mW**, against commercial
transceivers consuming **up to 42.4 mW** in Class C always-on operation.
Only the abstract's figures are used here; no other claim from the paper is
relied upon.

New artifacts: `artifacts/sim/longan_sweep_2026-11-05/` (13 run JSONs,
`sweep_summary.csv`, `sweep_manifest.json`, `runtimes.csv`). No existing
artifact under `artifacts/sim/` was modified.

---

## 1. Supply-voltage / power basis (found in code, not assumed)

Appendix B.1's axis is a **current** in mA. Longan reports **power** in mW. The
conversion needs the supply voltage the energy model assumes. It is explicit in
the configuration and used multiplicatively in the engine:

**The voltage:**

```
config/sim/wmnf_sim.yaml:46
  battery_v: 3.7
```

in context (`config/sim/wmnf_sim.yaml:40–46`):

```yaml
energy:
  # Heltec LoRa32 V3 current draws at 3.7 V nominal.
  ...
  battery_v: 3.7
```

**The place the current becomes energy.** Appendix B.1 was produced by the Rust
engine (`sweep_manifest.json` → `engine_git_head: 31f422a`, `engine: fastsim
(rust)`). In that engine the listen current is multiplied by `battery_v`
directly:

```
fastsim/src/engine2.rs:809  (at commit 31f422a)
    let drain = (listen_s * listen_ma / 1000.0 * battery_v
        + sleep_s * sleep_w
        + gps_s * gps_w)
        / 3600.0;
```

with `battery_v` read at `engine2.rs:766` and the per-node `listen_ma`
(including the `--relay-rx-ma` override) selected at `engine2.rs:767–777`.
The Python engine mirrors this at `scripts/mesh_sim.py:1688–1690`.

**Verdict: the model is voltage-explicit, parameterised in current.** It is
*not* parameterised in power, so the conversion is required — and because the
engine's own relation is exactly `P = I × 3.7 V`, the conversion is exact
*within the model*, not an approximation of a real supply rail.

## 2. mW → mA conversion, shown

```
I [mA] = P [mW] / battery_v [V] = P / 3.7

0.5 mW / 3.7 V = 0.135135... mA  -> 0.1351 mA   (bracket low)
1.0 mW / 3.7 V = 0.270270... mA  -> 0.2703 mA   (Longan headline)
2.0 mW / 3.7 V = 0.540540... mA  -> 0.5405 mA   (bracket high)
```

For orientation on the same axis, the commercial Class-C figure Longan compares
against: 42.4 mW / 3.7 V = **11.46 mA**, which sits essentially on B.1's 10 mA
viability knee — a coincidence worth noting but not used in any run.

**Two caveats that bound how far these rows can be pushed.** Both are
modelling gaps, not arithmetic ones:

1. **Scope mismatch.** Longan's ~1 mW is the *receiver front end*. The
   simulator's `rx_listen_ma` is documented as "router idle/RX, screen+BT off"
   — i.e. **board total**, including the host MCU. Mapping 1 mW onto board
   total silently assumes the rest of the board is free. These rows are
   therefore an **optimistic lower bound** on what a Longan-based relay would
   draw, not a prediction of one.
2. **Receiver-only substitution.** The `--relay-rx-ma` override changes the
   listen term only. `tx_current_ma` (245 mA) and `light_sleep_ma` (12 mA) are
   untouched, as in B.1. See §5 for why the sleep term is the interesting one.

## 3. Reproduction check on an existing B.1 row

Re-ran the published **10 mA** row (the most informative, being the only
non-saturated, non-trivial row near the knee) on the same frozen inputs.

**Engine provenance.** The Appendix B.1 manifest names engine commit
`31f422a`; the repository is now 21 commits ahead at `8cc573a`, and
`fastsim/src/` has changed by 1,048 lines since (wur mode, re-earn campaign,
decade runner). Reproducing against HEAD would therefore not be a clean test,
so the B.1 engine was rebuilt from `31f422a` via `git archive` into `/tmp`
(no checkout, no branch, no git state touched). The resulting binary's
sha256 differs from the manifest's (`6c1bdf03…` vs `0b8d5dde…`) — expected
from a different build environment; the run output is the arbiter.

**Frozen inputs verified first.** All four release_v1 inputs in the working
tree match `artifacts/sim/corrected/release_v1/input_hashes.txt` byte-for-byte:

| Input | sha256 (prefix) | matches release_v1 |
|---|---|---|
| `artifacts/sim/topology_statewide.json` | `97ec3986…` | yes |
| `artifacts/sim/routes_statewide.json` | `b6e61359…` | yes |
| `artifacts/sim/weather_year.json` | `55c3df53…` | yes |
| `config/sim/wmnf_sim.yaml` | `a42bc069…` | yes |

**Structural check** (new run vs `artifacts/sim/appendixB_sweeps/rxma10_s42.json`):
`mode`, `days`, `seed`, `n_nodes` (457), `n_renters` (212), `start_date`
(2025-07-01), `packets_originated` (10,183,840), `packet_ttl_s`, and the entire
`resolved_parameters` block are **identical**. (There is no committed B.1
sweep driver — it was reconstructed from `resolved_parameters`, which equals
fastsim's CLI defaults plus `--mode energy_aware --relay-rx-ma N`. Note this
is *not* the invocation in `scripts/run_corrected_release.sh`, which uses
different beacon/telemetry/energy-step flags.)

**Numeric check:**

| Metric | Published B.1 | This re-run | Delta |
|---|---|---|---|
| Depletions/yr | 27 | 27 | **0.0000%** |
| Fleet availability | 0.99762 | 0.99762 | **0.0000%** |
| PDR | 0.8305 | 0.8305 | **0.0000%** |

**Result: PASSED, and more tightly than the stated tolerance.** The output file
is **byte-for-byte identical** to the published artifact, with sha256
`ddf72e73044a6996d47516e1b530de711320ddc27ea5ffa7b9088394b2166a8b` — which is
exactly the hash recorded for `rxma10_s42.json` in
`artifacts/sim/appendixB_sweeps/sweep_manifest.json`. Tolerance claimed:
**0% (bit-exact)**, versus the ≤0.04% the report reports for its own baseline.

**Four of four re-run rows reproduce byte-for-byte.** The sweep's 2 mA control
arm re-runs B.1's published 2 mA row on all three of its seeds, and each output
also matches its manifest hash exactly:

| Run | sha256 | Manifest hash for | Match |
|---|---|---|---|
| `repro_rxma10_s42` | `ddf72e73…` | `rxma10_s42.json` | **identical** |
| `ctl_rxma2_s42` | `739cbe84…` | `rxma2_s42.json` | **identical** |
| `ctl_rxma2_s43` | `dfb73c24…` | `rxma2_s43.json` | **identical** |
| `ctl_rxma2_s44` | `a3b1a4d0…` | `rxma2_s44.json` | **identical** |

The engine is bit-deterministic across build environments for this
configuration, so the new rows are directly comparable to the published ones
and the reconstructed invocation is confirmed correct.

## 4. Results — B.1 extended with the Longan-class rows

Same shape as Appendix B.1. Always-on `energy_aware` routing, stock energy kit
(37 Wh battery, 6 W panel), release_v1 frozen inputs, 365 days.
Rows marked *(published)* are quoted from `appendixB_sweeps/sweep_summary.csv`
and were **not** re-run here except where §3 says so. New rows are the mean of
**seeds 42/43/44** — the same three seeds B.1 used for its 2 mA and 5 mA rows.

| Listen current | Receive power @3.7 V | Depletions/yr | Fleet availability | PDR |
|---|---|---|---|---|
| 68 mA (ESP32-class, stock) *(published)* | 251.6 mW | 29,175 | 53.5% | 0.843 |
| 10 mA *(published; reproduced bit-exact)* | 37.0 mW | 27 | 99.8% | 0.831 |
| 5 mA *(published, 3 seeds)* | 18.5 mW | 0 | 100.0% | 0.831 |
| 2 mA (nRF52-class) *(published, 3 seeds; re-run here, bit-exact)* | 7.4 mW | 0 | 100.0% | 0.8315 |
| **0.5405 mA — Longan bracket high (2.0 mW)** | 2.0 mW | **0** | **100.0%** | **0.8324** |
| **0.2703 mA — Longan headline (1.0 mW)** | 1.0 mW | **0** | **100.0%** | **0.8326** |
| **0.1351 mA — Longan bracket low (0.5 mW)** | 0.5 mW | **0** | **100.0%** | **0.8325** |

Per-seed detail (new runs; every seed independently gives 0 depletions and
100.0% availability):

| Config | `--relay-rx-ma` | s42 PDR | s43 PDR | s44 PDR | SOS delivered | SOS p95 |
|---|---|---|---|---|---|---|
| 2 mA control (= published row) | 2 | 0.8315 | 0.8315 | 0.8315 | 99.46% | 3.20 s |
| 2.0 mW | 0.5405 | 0.8323 | 0.8325 | 0.8323 | 99.47% | 3.06 s |
| 1.0 mW | 0.2703 | 0.8325 | 0.8326 | 0.8326 | 99.13% | 3.06 s |
| 0.5 mW | 0.1351 | 0.8325 | 0.8326 | 0.8325 | 99.13% | 2.91 s |

**Read the SOS columns within this sweep only.** §5.4's table quotes 100% SOS
delivery for its 2 mA null, but that is a *different run set* (5 seeds, a
different driver, flags not verified here) and is **not comparable** to the
rows above. Compare instead against this sweep's own 2 mA control, which
reproduces B.1 bit-exactly: 99.46% vs 99.13%. The denominator is ~186 SOS
incidents per seed, so that gap is **one packet** (185/186 vs 184/186) — noise,
not a regression. Across every sub-10 mA row in this sweep, SOS delivery varies
by ≤1 packet. The column that actually carries the §5.3 argument is **p95
latency**, which holds at ~2.9–3.2 s everywhere here, against `duty_sync`'s
35-minute p95 (§5.4).

**Headline.** A Longan-class receive path is **flat against the existing 2–5 mA
rows on every axis measured**: zero depletions, 100% fleet availability,
PDR 0.8324–0.8326 (vs 0.8315 at 2 mA), SOS p95 ~2.9–3.1 s. The sweep is
**saturated** well above 1 mW. The result is robust across the full
0.5–2.0 mW bracket and across all three seeds.

**Why the conclusion cannot depend on the exact conversion.** Two facts make
this provable from source rather than merely bracketed empirically. (i) For any
supply voltage above 0.5 V, 1 mW converts to a current below 2 mA — i.e. below
B.1's published zero-depletion row. (ii) Per-node drain is **strictly monotone
increasing** in `listen_ma`: with `duty = 1.0`, the engine charges
`listen_ma` over the whole interval (`engine2.rs:809`) and charges transmit as
the *incremental* term `(tx_current_ma - baseline_ma)` over airtime only
(`engine2.rs:487`), so total drain ∝ `listen_ma·(T − air) + tx_current_ma·air`,
whose derivative with respect to `listen_ma` is `(T − air) > 0`. Lowering
listen current therefore cannot increase consumption. Any conversion placing
Longan below 2 mA lands inside an already-saturated, monotone region, so the
zero-depletion / 100%-availability result holds for every plausible supply
voltage — and no voltage above 0.5 V is implausible for this hardware class.

## 5. Does a Longan-class receive path change the Appendix B.1 conclusion?

It does not change B.1's conclusion; it moves the question somewhere else. B.1
already found that the fleet loses no node all year at 2–5 mA, so arriving at
0.27 mA buys nothing further on survivability — the metric has no headroom
left, and the PDR difference (0.8326 vs 0.8315) is a tenth of a percent, well
inside the band B.1 itself calls "essentially flat." In that narrow sense this
sweep is a null result, and the honest reading is that B.1's engineering target
("bring idle receive under ~10 mA") was already the right target and Longan
clears it by a factor of roughly forty. The more interesting finding is what
happens to the §5.3 duty-cycle-versus-latency trade, and there the answer is
that it does not merely weaken — it **inverts**, for a reason visible in the
source rather than inferred from the output. Section 5.3 rests on the energy
budget being dominated by idle listening, "68 mA modeled listen vs 12 mA
sleep." Duty-cycling pays latency to buy that 68→12 mA gap. But the engine
computes a duty-cycled node's baseline draw as
`duty * listen_ma + (1 - duty) * light_sleep_ma` (`fastsim/src/engine2.rs:485–486`
@31f422a), and `--relay-rx-ma` lowers `listen_ma` while leaving
`light_sleep_ma` at 12 mA. At 0.27 mA listen, sleeping costs about **44 times
more** than listening, so any duty cycle below 1.0 *increases* consumption:
duty-cycling becomes strictly dominated, with no latency compensation to argue
about. The trade does not survive at that receive power — it ceases to be a
trade. Two cautions keep this from being a finished result. First, it is an
artifact of holding `light_sleep_ma` fixed at an ESP32-class placeholder while
dropping the listen term by two orders of magnitude; a real Longan-class
design would pair the low-power receiver with a correspondingly low-power
sleep state, and the honest conclusion is that **`light_sleep_ma` becomes the
binding constant the moment listen current goes sub-mA** — it, not listen
current, is then the number to pin at the bench. Second, both constants remain
uncalibrated placeholders and the ~1 mW figure is receiver-only mapped onto a
board-total parameter (§2), so this says what the *model* does, not what
hardware would do.

## 6. Reproduction

All commands from the repository root.
No virtualenv was created: the repo has none, and only the Python standard
library (`json`, `csv`, `hashlib`) is used for aggregation, run under
system `python3` with `-I`.

**Step 1 — build the Appendix B.1 engine (commit 31f422a) outside the worktree.**
`DEVELOPER_DIR` is pinned to the Command Line Tools so the link step cannot
reach into Xcode.app.

```bash
rm -rf /tmp/fastsim-b1 && mkdir -p /tmp/fastsim-b1
git archive 31f422a fastsim | tar -x -C /tmp/fastsim-b1
cd /tmp/fastsim-b1/fastsim && \
  DEVELOPER_DIR=/Library/Developer/CommandLineTools cargo build --release
```
*Runtime: 23 s* (cargo 1.89.0 / rustc 1.89.0, Homebrew; matches the
`rust-toolchain.toml` channel pinned at that commit). Pure-Rust dependencies
only; no Xcode or CLT installer was triggered.

**Step 2 — reproduction run (10 mA, seed 42).**

```bash
/tmp/fastsim-b1/fastsim/target/release/fastsim \
  --topology artifacts/sim/topology_statewide.json \
  --routes   artifacts/sim/routes_statewide.json \
  --weather  artifacts/sim/weather_year.json \
  --config   config/sim/wmnf_sim.yaml \
  --days 365 --seed 42 --mode energy_aware --relay-rx-ma 10 \
  --out artifacts/sim/longan_sweep_2026-11-05/repro_rxma10_s42.json
```
*Runtime: 675.5 s wall (11 min 16 s), single-threaded.*

Verify bit-exactness against the published artifact:

```bash
cmp artifacts/sim/appendixB_sweeps/rxma10_s42.json \
    artifacts/sim/longan_sweep_2026-11-05/repro_rxma10_s42.json
```

**Step 3 — the 12-run Longan sweep** (3 power points + 2 mA control, × seeds
42/43/44). The driver is `scripts/run_longan_sweep.sh` (new; it hard-codes the
reconstructed B.1 invocation and writes `runtimes.csv`):

```bash
scripts/run_longan_sweep.sh artifacts/sim/longan_sweep_2026-11-05
```
*Runtime: ~24 min wall for all 12, run 8-way then 4-way parallel on an 8-core
(6 performance-core) machine. Per-run wall times, from `runtimes.csv`:
571–845 s; sum of single-run CPU time = 9,019 s (2 h 30 min).*

**Step 4 — aggregate.**

```bash
python3 -I scripts/summarize_longan_sweep.py artifacts/sim/longan_sweep_2026-11-05
```
*Runtime: 3 s.* Writes `sweep_summary.csv` (same column shape as
`appendixB_sweeps/sweep_summary.csv`, plus SOS columns) and
`sweep_manifest.json` (input hashes, engine provenance, per-run sha256,
power basis, and the mW→mA conversion).

**Total: ~36 min wall (11 min repro + ~24 min sweep + build/aggregate),
9,694 s ≈ 2 h 42 min of engine CPU time.**

### Files added (nothing modified)

- `docs/experiments/longan-receive-sweep-2026-11-05.md` (this file)
- `scripts/run_longan_sweep.sh`
- `scripts/summarize_longan_sweep.py`
- `artifacts/sim/longan_sweep_2026-11-05/` (13 run JSONs + 3 summary files)

Not committed, not pushed, no branch created — working tree only, pending review.

**Note on tracking.** `.gitignore:34` ignores `artifacts/sim/*` by default; the
published bundles are tracked via explicit `!` negation lines below it. The new
`artifacts/sim/longan_sweep_2026-11-05/` bundle is therefore **ignored** and
present on disk only. Promoting it would need negation lines added to
`.gitignore` in the same style as the existing entries — left for review rather
than done here, since it edits a tracked file.
