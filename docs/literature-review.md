# Literature Review & Related Work

Research notes for the field research presentation and TÜBİTAK 2209-B form
(Innovative Aspect / Methodology sections).

## 1. Academic Literature

1. **Li, X., Hao, Y., et al. (2026). "MatrAIx: Simulating the World with 8.3 Billion Persona Agents."**
   arXiv:2608.04205 — https://arxiv.org/abs/2608.04205
   Infrastructure of 8.3B persona records (1,290 categorical dimensions, human-grounded +
   synthetic) driving LLM agents through Survey/Chatbot/Web/App environments across 1,010
   tasks in 25+ domains; 91.5% adherence to declared persona attributes across 366 trials.
   *Relevance:* the paper this project's brief cites directly — shows population-scale
   persona infrastructure and behavioral-adherence validation are feasible at massive
   scale. This project scales the same idea to a calibrated general-population panel
   instead of product-testing personas.
   *Critical note:* the reported 91.5% figure measures whether an agent expresses its
   **assigned** persona trait, not whether it predicts real human behavior — the paper
   itself treats human-comparison as a separate, unresolved question. This project must
   not conflate persona-adherence with predictive accuracy. Open-source components:
   [MatrAIx-Persona-8B (GitHub, MIT-licensed code)](https://github.com/MatrAIx-ai/MatrAIx-Persona-8B),
   [MatrAIx_Persona_1M dataset card (Hugging Face, non-commercial research use only)](https://huggingface.co/datasets/MatrAIx2026/MatrAIx_Persona_1M).

2. **Park, J.S., O'Brien, J., Cai, C.J., Morris, M.R., Liang, P., Bernstein, M.S. (2023).
   "Generative Agents: Interactive Simulacra of Human Behavior."**
   arXiv:2304.03442 — https://arxiv.org/abs/2304.03442
   Introduces the generative-agent architecture — LLM + natural-language memory stream +
   reflection + retrieval-based planning — letting agents form believable routines,
   opinions, and social behavior in a simulated town.
   *Relevance:* foundational architecture pattern for giving synthetic agents persistent,
   coherent behavior across a multi-round scenario rather than one-shot prompting.

3. **Argyle, L.P. et al. (2023). "Out of One, Many: Using Language Models to Simulate
   Human Samples."** arXiv:2209.06899 — https://arxiv.org/abs/2209.06899 (*Political
   Analysis*)
   Introduces "algorithmic fidelity" and "silicon sampling" — conditioning GPT-3 on real
   respondents' demographic backstories to reproduce human response distributions and
   cross-item correlations on political surveys.
   *Relevance:* core methodological precedent for calibrating synthetic personas against
   real survey microdata rather than free-generating attitudes.

4. **Santurkar, S. et al. (2023). "Whose Opinions Do Language Models Reflect?"**
   arXiv:2303.17548 — https://arxiv.org/abs/2303.17548 (ICML 2023)
   OpinionQA benchmark comparing LM opinions to 60 US demographic subgroups; finds
   systematic misalignment persisting under explicit steering, and identifies which
   subgroups are least well represented.
   *Relevance:* direct evidence for why uncalibrated LLM opinion simulation is
   unreliable — motivates the project's requirement to calibrate against real aggregate
   data and report where the model under/over-represents subgroups.

5. **(2026). "Improving Cross-Cultural Survey Simulation with Calibrated Value
   Personas."** arXiv:2605.16193 — https://arxiv.org/abs/2605.16193
   Builds personas from Inglehart–Welzel cultural-value dimensions derived from the World
   Values Survey; raw prompting stays biased toward Western priors, while a calibration
   step measurably reduces cross-country prediction error, especially for
   underrepresented populations.
   *Relevance:* near-identical calibration pipeline (WVS-grounded value dimensions →
   persona conditioning → calibration) to what this project needs; supports the case for
   calibration over raw prompting.

6. **Li, M., Conrad, F.G. (2026). "Persona-Based Simulation of Human Opinion at
   Population Scale."** arXiv:2603.27056 — https://arxiv.org/abs/2603.27056
   Critiques the assumption that demographics alone explain opinion variation; shows
   persona-simulated opinion is highly sensitive to question wording/formatting.
   *Relevance:* methodological caution to build into the validation plan (robustness
   checks, not just mean accuracy).

7. **Chopra, A., Raskar, R. et al. — "Large Population Models" / AgentTorch line of
   work.** arXiv:2507.09901 (overview), arXiv:2207.09714 (differentiable agent-based
   epidemiology) — https://arxiv.org/abs/2507.09901
   MIT framework combining GPU-accelerated, differentiable agent-based simulation with
   LLM behavior modules at million-agent scale, enabling gradient-based calibration
   against real outcome data (e.g. epidemic curves, vaccine policy).
   *Relevance:* concrete precedent for the differentiable/ML-calibrated ABM arm of the
   project's model-comparison activity (agent-based vs. equation-based vs. ML).

8. **Google DeepMind — "Generative Agent-Based Modeling with Actions Grounded in
   Physical, Social, or Digital Space Using Concordia."** arXiv:2312.03664, follow-up
   arXiv:2411.07038 — https://arxiv.org/abs/2312.03664
   Library for generative agent-based modeling with a "Game Master" entity that
   adjudicates natural-language agent actions against environment rules; designed for
   scientific social-simulation experiments as well as synthetic user evaluation.
   *Relevance:* closest existing open-source engine design for scenario orchestration
   (a moderator/environment layer arbitrating multi-agent scenario response).

9. **Ozkan, G. (2026). "Distribution-First Population Simulation: Collapse, Calibration,
   and Recall in Non-WEIRD LLM Persona Modeling."**
   arXiv:2607.18310 — https://arxiv.org/abs/2607.18310
   Grounds personas on 2,414 real World Values Survey respondents from Turkey (a
   non-WEIRD population) and shows that running each persona as an independent LLM
   agent causes severe "modal collapse" toward the majority answer; proposes a
   distribution-first approach — model the population's response distribution once and
   assign it to grounded characters, rather than sampling each agent independently.
   *Relevance:* directly informs this project's core design choice for the general
   population panel: independent per-agent sampling is measurably unreliable, and the
   simulation pipeline should calibrate distributions rather than trust naive
   per-persona majority votes — especially important since this project also targets a
   non-WEIRD (Turkish) population.

## 2. Similar Tools and Systems

| Tool | What it does | Strengths | Limitations / gap this project addresses |
|---|---|---|---|
| **Mesa** (Python) | Classic ABM framework: agents, scheduler, spatial grid, data collector, browser visualization | Mature, Pythonic, huge ecosystem, integrates easily with pandas/numpy | No native LLM/persona layer, no built-in survey-calibration or opinion-dynamics module — agents are rule-based, not language-conditioned |
| **NetLogo** | GUI-based ABM environment, most widely used teaching/research ABM platform | Extremely accessible, huge model library, strong pedagogy | Not built for large-scale (millions of agents) or LLM-driven heterogeneous personas; scripting language isn't suited to modern ML/LLM pipelines |
| **AgentTorch** (MIT) | Differentiable, GPU-accelerated ABM with LLM-agent integration, used for epidemic/policy simulation at population scale | Real large-scale policy validation record (vaccine rollout), gradient-based calibration | Heavier infra/ML dependency, epidemiology-first design; general social-attitude calibration against opinion surveys is not its focus |
| **Concordia** (Google DeepMind) | Generative agent-based modeling library with LLM agents + "Game Master" environment adjudicator | Clean architecture for grounding LLM-agent actions in scenario rules; built for both science and synthetic-user testing | No built-in demographic-calibration/post-stratification against real census/survey data; validation tooling (TVD, calibration error) not first-class |
| **MatrAIx** (2026) | 8.3B-persona database + testing playground for AI/product evaluation | Massive scale, strong behavioral-adherence validation | Oriented at product/UX evaluation, not policy/social-science scenario simulation or historical retrospective validation |

**Gap this project targets:** none of the above combine (a) demographic/attitude
calibration against real public survey microdata, (b) multi-round scenario simulation of
policy/economic/demographic shocks, (c) retrospective validation against historical
outcomes, and (d) a head-to-head comparison against non-agent baselines
(equation-based / ML). That combination is the project's original contribution.

## 3. Methodology References

- **Post-stratification / MRP** (Gelman et al.) —
  https://sites.stat.columbia.edu/gelman/research/published/improving_mrp.pdf
  Model-based small-area estimation + post-stratification to known population margins;
  standard technique for aligning a synthetic panel to true population composition.
- **ABM vs. system dynamics (equation-based) comparison** — established literature
  contrasting top-down aggregate equations (SD) with bottom-up heterogeneous agents
  (ABM), which can diverge under policy shocks even with matching baselines. Justifies
  the project's Model Comparison work package.
- **Algorithmic fidelity / silicon sampling** (Argyle et al., above) — standard
  framework and metrics (response-distribution match, cross-item correlation) for
  measuring how well an LLM persona panel reproduces real subgroup response
  distributions.
- **Validation metric**: total variation distance (TVD) and held-out calibration error,
  used consistently across the calibrated-persona literature above, recommended as this
  project's core accuracy metric for historical validation.
