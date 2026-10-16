# Resilient Emergency MANETs for Wilderness Safety

Terrain-aware planning and year-scale reliability simulation for a solar-powered
LoRa/Meshtastic mesh intended for wilderness search and rescue. Master's directed study,
Northeastern University, Summer 2026 (CS 5976), advised by Prof. Stefano Basagni and
Prof. Guevara Noubir.

**Full report:** [`reports/directed-study-report-2026-08-03.md`](reports/directed-study-report-2026-08-03.md)
([PDF](reports/directed-study-report-2026-08-03.pdf))

---

## Results

**1. Survivability is governed by duty-cycling policy, not routing choice.**
Across five materially different always-on routing modes — flooding, minimum-hop, ETX,
energy-aware and load-balanced — annual energy-depletion events vary by **less than 0.3%**
(29,164–29,234). Changing the duty policy moves them **5.5–24×** (down to 1,217–5,311) and
fleet availability from 54% to 90–96%, at a quantified cost in delivery ratio and SOS
latency. Idle listening dominates the energy budget. A listen-current sweep locates the
design threshold: **below roughly 10 mA idle receive current the trade-off disappears**
(27 depletions/year, 99.8% availability). A ten-year ERA5 climate campaign confirms the
advantage in every weather year 2016–2025 (15.4–26.5×, mean 20.7×).
*Model-only, pending field calibration.*

**2. Real-terrain modelling reversed the project's own coverage conclusions, by up to 62.3 dB.**
Replacing free-space analysis with Longley–Rice ITM over USGS 3DEP elevation data flipped
the link picture: relay-to-summit chords came out terrain-blocked (−132.2 dBm, below the
assumed −131 dBm sensitivity), while valley crossings came out clear line-of-sight and
roughly 55 dB stronger (−76.6 / −74.1 dBm). The blocker is diffraction over the convexity of
the summit cone, with terrain rising up to 53 m above the direct ray. A raised mast, a lower
relocation and a summit-sited node were each modelled and rejected. *Model-only.*

**3. A pre-registered wake-up-radio hypothesis, refuted.**
Both registered claims failed: always-on 2 mA-class silicon dominated every wake-receiver
variant on every axis, including the physically unrealisable ideal one. At realistic
sensitivity deltas, 40.1% of routing-eligible links cannot carry the wake chirp and a median
of 89 of 457 sites lose every wake-feasible path to a gateway. Published as a negative result.

**4. Opportunistic validation against a public mesh is infeasible — measured, not argued.**
Field measurement put public-station transmit cadence at **0–4 packets per hour**, yielding
~0.6 expected transmissions from the primary target across a 33-minute GPS-verified summit
dwell; and among six origin-decoded foreign frames, **zero were direct receptions** — each
arrived relayed, attributing its RSSI to an unknown last hop. This result motivated the
controlled-beacon protocol subsequently pre-registered here.

## Reproducibility

Two independently written discrete-event engines — a Python/SimPy reference and a Rust
performance engine — are cross-validated on a shared micro-scenario against pre-registered
tolerance bands (max 0.0045 absolute PDR difference). Output is byte-reproducible: four
independent runs produced identical 419,738-byte artifacts. The released campaign is
9 policy modes × 5 seeds × 365 simulated days with hash-locked inputs.

## How this repository handles evidence

Claims are labelled by evidence class, and the labels are enforced rather than decorative:

- [`docs/audit-correction-ledger-2026-07-13.md`](docs/audit-correction-ledger-2026-07-13.md) — dated defect ledger
- [`docs/claims-source-audit-2026-07.md`](docs/claims-source-audit-2026-07.md) — sentence-level claims audit
- [`WITHDRAWN-DO-NOT-CITE/`](WITHDRAWN-DO-NOT-CITE/) — superseded results, retained for provenance and excluded from citation
- Prediction packs are SHA-256 frozen and registered before the data they concern is collected

**Scope.** This is a research prototype: a planning and simulation study with a field
acquisition system, not a field-validated or legally cleared emergency network. The
controlled calibration dataset remains outstanding — the released dataset is labelled
accordingly in its manifest — and the remaining step is specified in the report's future
work.

## Repository contents

- Planning and methodology; data-acquisition schema and QA
- AIRMap prediction pipeline, terrain layer and calibration tooling
- Analysis outputs and final report artifacts
- Companion runtimes: [`meshradio-head-runtime`](https://github.com/edoherty2017/meshradio-head-runtime), [`meshradio-node-runtime`](https://github.com/edoherty2017/meshradio-node-runtime)

## Architecture — class diagrams

Structural map of the codebase (as of 2026-08-04). Mermaid sources live next to
the PNGs in [`docs/diagrams/`](docs/diagrams/); regenerate with
`npx @mermaid-js/mermaid-cli -i <file>.mmd -o <file>.png -b white -s 2`.

### System overview

Four frozen inputs feed two peer engines implementing the same model: the Rust
`fastsim` runs the canonical year-scale campaigns, the Python SimPy twin
generates the packet traces behind the replay viewer, and
`sim_micro_parity.py` runs both on identical arguments to compare summary
scalars.

![System overview](docs/diagrams/01-system-overview.png)

### Python twin — `scripts/mesh_sim.py`

Four classes. `Node` is pure state (its only method is `__init__`); all
behavior — PHY, MAC, routing, energy, traffic, wake-up radio, lifecycle — lives
on `MeshSim`, driven by a `simpy.Environment` of generator processes. The 12
policy arms (including the RL modes `q_routing`/`rl_duty`, which exist only in
this engine) are branch selections inside `MeshSim` methods, not subclasses.

![Python twin class diagram](docs/diagrams/02-python-mesh-sim.png)

### Rust fastsim — config and input schemas (`inputs.rs`)

Only `Deserialize` is ever derived in the crate; the output summary JSON is
hand-built in `main.rs`. A fail-closed `validate_model_inputs()` checks all
four inputs before the engine is constructed.

![Rust config schema](docs/diagrams/03-rust-config-schema.png)

![Rust input file schema](docs/diagrams/04-rust-input-files.png)

### Rust fastsim — runtime core: events and packets

`Sim` is the deliberate god object mirroring `MeshSim`. Scheduling is a
`BinaryHeap` of `Sched` entries (ordered time → priority → sequence) carrying
one of 18 `Ev` variants, dispatched by a single 18-arm `handle()` match.
Packets travel as `Flight` values, in the air as `ActiveTx`. RNG is two-tier:
stateless keyed draws (14 domain tags + per-entity counters) plus stateful
per-link streams for shadowing.

![Rust events and packets](docs/diagrams/05-rust-events-packets.png)

### Rust fastsim — population, energy, and rental

Dashed arrows are `u32` index references into `Sim::nodes` / `Sim::routes` —
the crate's convention instead of ownership; `name_to_idx` is the only
name→index bridge. Energy is banked lazily as `EnergySegment`s and settled in
batch.

![Rust population and energy](docs/diagrams/06-rust-population-energy.png)

### Rust source layout — one class, three files

`engine.rs` and `engine2.rs` are **not** two engines: they are two halves of
one `impl Sim` (construction vs. run loop), split by file size and always
modified together. Every mode runs the identical pair; `Mode` only selects
behavior branches inside it.

![Rust module layout](docs/diagrams/07-rust-module-layout.png)

### Supporting tooling and test doubles

Outside the engines the only real classes are `Dem` (DEM raster → ITM terrain
profiles) and `TrailGraph` (OSM trail routing); the rest of the toolchain is
functional modules.

![Tooling and test doubles](docs/diagrams/08-tooling-test-doubles.png)
