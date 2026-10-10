# Track D — UI / Dashboard

**You own:** making the simulation's results legible to a human — nothing
about how they were produced.

## Scope

- A lightweight dashboard (Streamlit recommended — pure Python, no separate
  frontend stack needed, fast to iterate on) that reads one or more
  `results.json` files (Track B's output) and Track C's comparison report,
  and presents them.
- Minimum views:
  - **Scenario view**: a scenario's overall `response_distribution` as a bar
    chart, plus the `by_subgroup` breakdown (e.g. by `age_band`) next to it.
  - **Comparison view**: the agent-based engine vs. the equation-based and ML
    baselines vs. the real held-out answer, for a given scenario (from
    Track C's report) — this is the slide that answers "should we trust it."
- Never compute or reinterpret a metric here. If a number isn't already in
  `results.json` or Track C's report, that's a sign it belongs in Track C,
  not in the UI.
- No individual-level views — population distributions only, same rule as
  Track B.

## What you consume

Track B's `results.json` schema and Track C's comparison report — see
[`../simulation/README.md`](../simulation/README.md) and
[`../validation/README.md`](../validation/README.md). You don't define a new
contract; you're a pure consumer, same position in the pipeline as Track C.

## Don't wait for anyone

Build against [`../simulation/fixtures/results.sample.json`](../simulation/fixtures/results.sample.json)
today. A real comparison report from Track C doesn't exist yet either — until
it does, mock one by hand (same shape: engine vs. baselines vs. real answer,
per scenario) so your comparison view has something to render. Swap in real
files from Tracks B and C once they land; the dashboard code shouldn't need
to change, only its inputs.

## Definition of done

- [ ] Scenario view: response distribution + subgroup breakdown, rendered from any `results.json`
- [ ] Comparison view: engine vs. both baselines vs. real answer, rendered from Track C's report
- [ ] Runs against the fixture data with zero real pipeline code installed
- [ ] Runs end-to-end once real `results.json` / comparison report exist
