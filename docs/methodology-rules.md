# Methodology rules

Most of this file is **defaults**, not law: the best approach we currently
know of, so nobody starts from zero. You are expected to look for better
ones. Only a handful of rules are fixed, because breaking them makes every
result untrustworthy no matter how clever the method.

## Invariants — these don't bend

- **Held-out fields never reach persona generation or simulation.** Only
  Track C reads `heldout.csv`.
- **No absolute-share claims, no individual-level outputs** (rules 1–2).
- **Every claimed effect has a control** — placebo for scenarios, vanilla for
  the persona layer (rule 5) — and must clear the noise floor (rule 6).
- **Criterion before run, record after** (rules 9 and 32). Partial or
  rate-limited runs are not results.
- **Fit and measure on different data** (rule 10).
- **Contracts change only by PR** with a heads-up to the tracks that consume
  them.

Everything else below is a default.

## Research first, then test, then adopt

Before building anything non-trivial — a generator, an update rule, a
metric, a prompt format, a chart — **search for current work first**: recent
papers (arXiv, ACL/NeurIPS/ICWSM, journals), official docs, maintained open
source projects. The field moves fast; a method from this year may beat
anything here. Link what you found in your PR.

If you find something that looks better than a default here, **don't swap
it in directly**:

1. Write the idea and a success criterion into [`findings.md`](findings.md)
   *before* testing ("beats the default by more than the noise floor on
   TVD for probes X, Y, Z").
2. Run it **against the current default** on the same personas, same seeds,
   same items, with the invariants intact.
3. Record the result either way. A good idea that didn't beat the default is
   still a finding — it saves the next person from re-trying it.
4. If it wins, open a PR that changes the code *and* updates the default in
   this file, linking the finding.

A default that turns out wrong gets the same treatment: show it with a test,
record it, change it here.

## What we can and can't claim

1. **No absolute shares.** Never report "X% of the population would support
   this." Absolute shares from LLM-simulated populations move a lot with the
   model, provider and prompt wording (Santurkar et al. 2023; the MatrAIx
   cross-model results). Report **comparisons**: treatment vs. placebo,
   ranking of items or scenarios, direction of subgroup differences.
2. **Personas are not people.** A persona describes "someone with these
   attributes," never a real respondent. Outputs are population
   distributions only.
3. **Subgroup gaps: direction and rank only**, and only after Track C has
   checked that the gap exists in the real data. Simulated populations tend
   to invent stereotyped gradients between groups and exaggerate real ones.
4. **Deliberation output is a trend indicator**, not a realistic model of how
   people talk each other into things.

## Experiment design

5. **Three arms per run.** *Treatment* (personas + scenario), *placebo* (same
   personas, same prompt length, an irrelevant shock text), *vanilla* (no
   persona at all). Scenario effect = treatment − placebo. What the persona
   layer contributes = persona arms vs. vanilla. Adding any block of text to
   a prompt shifts answers by itself, so an effect without a placebo is
   overstated.
6. **Noise floor first.** Run an identical configuration twice with different
   seeds. Any difference smaller than that run-to-run gap is not reported.
7. **Saturation screen.** If the placebo share for the option of interest is
   outside 10–90%, the item cannot show an effect. Pick another item.
8. **Matched comparison for layer effects.** When testing whether a component
   matters, compare the *same* personas with vs. without it. Aggregate
   distributions are blind to answers swapping between personas.
9. **Pre-register.** Write the success criterion in
   [`findings.md`](findings.md) before running. A partial or rate-limited
   run is not a result.
10. **Fit and measure on different data.** A parameter tuned on one split is
    measured on another. The item that revealed a bug can't also validate the
    fix — that's a regression check, not evidence.
11. **Know your power.** Compute the minimum detectable difference for your n
    before running. A null result means "not measurable at this n," not
    "no effect."
12. **Multiple tests → Benjamini–Hochberg.** Subgroup cells with an effective
    n below 30 are flagged, not tested. Rank tests need enough *groups*, not
    just enough people per group.
13. **Spread is two numbers:** total SD and between-persona SD. If they
    diverge, the apparent diversity is coming from averaging soft answers,
    not from personas differing.
14. **At least two models.** Report what they agree on (usually rankings).
    Disagreement is shown, not averaged away.

## Prompt and question design (when an LLM is in the loop)

15. Use the original survey wording. Don't paraphrase, and keep wording
    identical across arms that are compared.
16. Reverse the option order for half the panel.
17. Prefer a forced choice between two concrete options over
    agree/disagree, which carries an acquiescence bias.
18. Option labels are symmetric actions. Costs and consequences go into the
    question text, never into a label.
19. Don't ask for a rationale alongside the choice — it narrows the
    distribution.
20. No base-rate hints ("most people think…") in a prompt. That's telling the
    model the answer.
21. Log how often each option is chosen. An option nobody ever picks (often
    "uncertain" / "don't know") is a finding, not noise.
22. Give personas concrete stakes ("this tax does not apply to your income
    bracket") rather than abstract instructions ("consider your situation").
23. **Never show an LLM the other agents' opinions and re-ask.** That
    produces artificial cascades. Opinion updates happen in code (e.g.
    Friedkin–Johnsen); the LLM may only score argument strength.
24. Pin the exact model snapshot, never an alias. `temperature: 0` is not
    determinism. Record model, seed and persona-set hash on every run. If the
    model exposes token log-probabilities, read the full answer distribution
    from them instead of sampling — check support first.
25. With more than 8 options, verify every option actually gets a label.

## Engineering

26. **One source of truth for categories:**
    [`src/common/schema.py`](../src/common/schema.py). Never re-type age bands
    or field lists in another module.
27. **Test what is actually sent.** A prompt-building test captures the real
    request payload, not just a helper's return value. A computed block that
    never reaches the prompt passes every other test.
28. **Prove a test can fail.** Break the input on purpose once and watch it
    go red.
29. **Two code paths, same output.** If the same thing is built in two places,
    a parity test compares them on the same data.
30. Derive seeds from a hash's *value*, never its length.
31. **Paid runs:** dry-run by default, explicit flag to spend, hard call cap.
    Never print API keys or auth headers in logs or errors.
32. **Write it down.** Every measurement goes into [`findings.md`](findings.md)
    the same day — config, result, status. Unrecorded results get rediscovered
    the hard way.

## Scale and retrospective validation

33. **Query per archetype, not per agent.** Group personas into cells
    (Track A's post-stratification cells are natural archetypes), query the
    LLM once per cell × option set with a few repeats, and let agents sample
    from the cell's answer distribution. This keeps cost flat as the
    population grows (LLM archetypes, Chopra et al. / AgentTorch). Note that
    archetypes flatten within-cell variation — say so when reporting spread.
34. **Watch for contamination.** An LLM may have seen the outcome of a
    historical period during training. For retrospective validation prefer
    periods after the model's training cutoff, or flag the result as
    possibly contaminated.
35. **Use ideas, not the library.** AgentTorch is AGPL-3.0 and GPU/PyTorch
    heavy; our repo is MIT. Re-implement what we need in numpy/pandas.
