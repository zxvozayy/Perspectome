# Track B — Scenario Simulation Engine

**Owner:** Yiğithan ([@DeFultt](https://github.com/DeFultt))

**You own:** turning a population + a question into population-level answer
distributions — and nothing about where the population came from or how
it's scored afterward.

> **Room to improve.** Fixed: no held-out fields, the three arms, the
> contract. Everything else — the update rule, the prompt format, archetype
> querying, even whether an LLM is the best response model — is a starting
> default. Research current work first and beat the default with a test
> ([how](../../docs/methodology-rules.md#research-first-then-test-then-adopt)).
> Open questions: Friedkin–Johnsen vs. bounded-confidence vs. other opinion
> dynamics; social network structure between personas; newer
> distribution-level prompting or fine-tuned persona models.

## Your branch

- Work **only** on the `yigithan` branch, inside `src/simulation/`. Don't commit to
  anyone else's branch, and never push to `main` — it only accepts pull
  requests with a teammate's approval.
- Start every session with `git pull origin main`.
- Finished an issue? Push to `yigithan` and open a PR into `main` with
  `Closes #<issue>` in the description. Don't wait for the sprint to end.
- Full workflow: [`CONTRIBUTING.md`](../../CONTRIBUTING.md).

## Two kinds of run

- **`probe`** — ask the population a real survey item whose true answers sit
  in Track A's `heldout.csv` (e.g. institutional trust). This is how the
  engine gets validated: Track C compares it to the real distribution.
- **`scenario`** — a counterfactual shock (unemployment rises, rapid AI
  adoption…). There's no ground truth, so the output that matters is the
  **difference from the placebo arm**, not the absolute shares.

Both produce the same `results.json` shape.

## Scope

- Define a scenario format (YAML or JSON): the shock text, the question in
  its exact wording, the options, and a matching **placebo** text of similar
  length that changes nothing relevant.
- **Three arms on every run** (see
  [rule 5](../../docs/methodology-rules.md)): `treatment` (personas +
  scenario), `placebo` (personas + placebo text), `vanilla` (no persona). For
  probes, `placebo` may be `null`.
- **Query per archetype, not per persona.** Track A gives every persona a
  `cell_id` (age band × gender × education). Ask the model once per cell and
  give every persona its cell's probability vector
  ([rule 33](../../docs/methodology-rules.md)). Cost stays flat as the
  population grows. Only the cell-defining fields describe the cell in the
  prompt; other fields differ inside a cell. Personas without a `cell_id`
  are left out and counted in `metadata.n_excluded_no_cell`.
- **Question-specific cells (optional).** `cell_fields: auto` in a scenario
  (or `--cells auto`) lets `src/answering` choose the cells per question: the
  anchor items worded most like the question, which persona fields predict
  them on the real core (gradient boosting + permutation importance), and the
  top 3 fields become the cells; cells under 30 personas fall back to fewer
  fields. The prompt then carries the cell's most common answers to those
  anchors among real respondents. `cell_fields: [religiosity_band, region]`
  fixes the fields instead. `metadata.cells` records the fields, anchors and
  number of cells. Anchors near-duplicating a probe's target item are never
  used (`src/answering/anchors.yaml`, `exclude`). Needs `pip install -e ".[ml]"`.
- **How the answer is read.** Options are labelled with single letters
  (`A) support`, `B) oppose`, ...) and the model answers with one letter.
  When the model returns token log-probabilities, one call gives the full
  distribution over the letters (`top_logprobs`); otherwise `n_repeats`
  answers are sampled at temperature 1. Never `temperature: 0` — it is not
  deterministic and collapses every repeat onto one answer. Answers that
  aren't a valid letter are counted in `metadata.model_stats.parse_failures`
  and never assigned to an option.
- **Round 1 — independent stance:** each persona's initial opinion is its
  cell's probability vector. Nothing is sampled anywhere.
- **Rounds 2..n — update in code, not in the prompt.** Never show the model other
  agents' opinions and re-ask — that produces artificial cascades toward one
  answer. Opinions are updated numerically with Friedkin–Johnsen on the
  probability vectors (`rounds.run_fj`): each persona moves partly toward the
  mean of its neighbours (same region, adjacent age band), anchored to its own
  initial stance, and never leaves the range of initial opinions in its
  neighbourhood. The model may only be used to *score how strong an argument
  is*.
- **Result:** the weighted mean of the final vectors, overall and by
  `age_band`, `gender` and `education_level` (the cell-defining fields), with
  `n` next to every subgroup. `option_usage` is the expected number of
  personas per option. `vanilla` is the model's raw answer with no persona and
  no deliberation.
- **Held-out fields are off limits.** Nothing in `heldout.csv` may influence
  generation or simulation — not even to set how much a persona shifts. Only
  the conditioning fields in `personas.csv` exist for this track.
- Never output an individual-level prediction — only population-level
  distributions.

## Question and prompt rules

From [`docs/methodology-rules.md`](../../docs/methodology-rules.md),
rules 15–25. The short version:
- Exact survey wording, no paraphrase, identical across arms.
- Reverse option order for half the panel; record which half got which.
- Two concrete options beat agree/disagree. Labels are symmetric actions;
  costs go in the question.
- No rationale alongside the choice. No base-rate hints.
- Concrete stakes ("this tax does not apply to your income bracket") beat
  abstract instructions ("consider your situation").
- **Expect `uncertain` to be almost never chosen.** That's why
  `option_usage` is in the output — report it, don't hide it.
- Pin the model snapshot. Record seed and `persona_set_hash` every run. If
  the model gives token log-probabilities, read the distribution from those
  instead of sampling — check support first.
- Expect a status-quo reflex on "new regulation" questions; keep a placebo
  regulation in mind when designing policy scenarios.
- Avoid scenarios whose headline is a political-party direction — that's
  the area where simulated opinion is least trustworthy.

## What you ship

A runner under `src/simulation/` that takes a `personas.csv` (any file
matching Track A's schema) and a scenario/probe definition, and writes one
`results/<run_id>.json` per run. Paid model calls: dry-run by default,
explicit flag to spend, hard call cap ([rule 31](../../docs/methodology-rules.md)).

## The contract (freeze this on day 1)

```json
{
  "run_id": "string, unique",
  "run_type": "probe | scenario",
  "scenario_id": "string",
  "target_item": "heldout field name for probes, null for scenarios",
  "options": ["support", "oppose", "uncertain"],
  "n_personas": 500,
  "arms": {
    "treatment": {
      "response_distribution": {"support": 0.42, "oppose": 0.55, "uncertain": 0.03},
      "option_usage": {"support": 210, "oppose": 275, "uncertain": 15},
      "by_subgroup": {
        "age_band": {
          "18-24": {"n": 80, "distribution": {"support": 0.55, "oppose": 0.43, "uncertain": 0.02}}
        }
      }
    },
    "placebo": { "same shape as treatment, or null for probes" },
    "vanilla": {
      "response_distribution": {"support": 0.90, "oppose": 0.10, "uncertain": 0.00}
    }
  },
  "metadata": {
    "model": "mock | <provider>/<model>",
    "model_snapshot": "exact pinned version",
    "seed": 42,
    "persona_set_hash": "sha256 of personas.csv",
    "option_order": "fixed | reversed_half",
    "n_rounds": 3,
    "timestamp": "ISO 8601"
  }
}
```

Distributions are as produced; Track C decides what may be claimed from
them. A sample is in [`fixtures/`](fixtures/) — fabricated numbers.

## Don't wait for anyone

Use [`../personas/fixtures/personas.sample.csv`](../personas/fixtures/personas.sample.csv)
and a `mock` model to develop against. You don't need Track A's real
pipeline or any API key to build and test the whole three-round loop.

## Live runs

`--live --model <snapshot>` calls a real model, capped by `--max-calls`.
`claude-*` snapshots go to the Anthropic API (`pip install -e ".[llm]"`), with
the key in the git-ignored `.env` as `ANTHROPIC_API_KEY` or `CLAUDE_API_KEY`
(plus `ANTHROPIC_WORKSPACE_ID` if the key isn't scoped to a workspace). The
API gives no log-probabilities, so each cell samples `--n-repeats` answers at
temperature 1. Every held-out item has a probe in `scenarios/` with the WVS-7
wording; `option_labels` is the text shown to the model, `options` the keys
that match `heldout.csv`.

## If you need to change the contract

Open a PR and say so in the team channel — Tracks C and D are coding against
`results.json`'s shape from day one.

## Definition of done

- [ ] Scenario format documented, with at least 2 scenarios and their placebo texts, and 1 probe
- [ ] Per-archetype querying with a `mock` model
- [ ] Three rounds implemented, Round 2 updating in code
- [ ] All three arms emitted; output matches the schema above
- [ ] Prompt-payload test: captures what is actually sent and checks the persona block and exact question wording are in it
- [ ] Runs end-to-end against both the fixture personas and Track A's real `personas.csv`
