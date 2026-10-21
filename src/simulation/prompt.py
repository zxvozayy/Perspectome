"""Build LLM prompts from persona cells, scenarios, and options."""

from __future__ import annotations


# Single-token option labels, so a model's answer can be read from its
# next-token log-probabilities (rule 24). Rule 25: every option gets one.
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def option_letters(n: int) -> str:
    if n > len(LETTERS):
        raise ValueError(f"{n} options; at most {len(LETTERS)} can be labelled")
    return LETTERS[:n]


RELIGIOSITY_TEXT = {"low": "not important", "medium": "somewhat important",
                    "high": "very important", "very_high": "extremely important"}
POLITICAL_TEXT = {"left": "on the left", "centre": "in the centre", "right": "on the right"}


def build_persona_block(cell_fields: dict) -> str:
    """Natural-language persona description from whichever conditioning fields a cell has.

    Never references held-out fields. Missing values are left out rather than
    written as "nan".
    """
    def has(key):
        v = cell_fields.get(key)
        return v is not None and str(v) not in ("", "nan", "<NA>")

    who = [f"{cell_fields['age_band']} year old"] if has("age_band") else []
    who.append(str(cell_fields["gender"]) if has("gender") else "person")
    if has("education_level"):
        who.append(f"with a {cell_fields['education_level']} level education")
    text = "You are a " + " ".join(who)
    if has("settlement_type") and has("region"):
        text += f", living in a {cell_fields['settlement_type']} area of {cell_fields['region']}"
    elif has("region") or has("settlement_type"):
        text += f", living in {cell_fields['region']}" if has("region") else             f", living in a {cell_fields['settlement_type']} area"
    text += "."
    extras = [str(cell_fields[k]) for k in ("marital_status", "employment_status") if has(k)]
    if extras:
        text += " You are " + ", ".join(extras) + "."
    if has("income_decile"):
        text += f" Your household is in income decile {cell_fields['income_decile']}."
    if has("religiosity_band"):
        text += f" God is {RELIGIOSITY_TEXT[cell_fields['religiosity_band']]} in your life."
    if has("political_leaning_band"):
        text += f" Politically, you place yourself {POLITICAL_TEXT[cell_fields['political_leaning_band']]}."
    return text


def build_prompt(
    persona_block: str | None,
    scenario_text: str | None,
    question: str,
    options: list[str],
    reverse_options: bool,
) -> str:
    """Assemble the full prompt string.

    Structure:
      [persona_block if present]
      [scenario_text if present]
      [question]
      [options as lettered lines A) ... B) ..., reversed if flagged]
      Instruction to answer with one letter.
    """
    display_options = list(reversed(options)) if reverse_options else list(options)

    parts: list[str] = []
    if persona_block:
        parts.append(persona_block)
    if scenario_text:
        parts.append(scenario_text.strip())
    parts.append(question.strip())
    letters = option_letters(len(display_options))
    parts.append("\n".join(f"{letter}) {opt}" for letter, opt in zip(letters, display_options)))
    parts.append("Answer with the letter of exactly one option, nothing else.")

    return "\n\n".join(parts)


def build_prompts_for_arm(
    arm: str,
    scenario: dict,
    cell_representatives: dict[str, dict],
    reverse_half: bool = True,
    contexts: dict[str, str] | None = None,
) -> list[dict]:
    """Build all prompts for one arm.

    Parameters
    ----------
    arm : "treatment" | "placebo" | "vanilla"
    scenario : parsed scenario dict
    cell_representatives : {cell_id: {field: value, ...}} for each unique cell
    reverse_half : if True, alternate cells get reversed option order
    contexts : optional {cell_id: text} added after the persona block (src/answering)

    Returns
    -------
    List of dicts: {cell_id, prompt, options_order, reversed}
    """
    question = scenario["question"]
    options = scenario["options"]
    shown = scenario.get("option_labels") or options  # text in the prompt; results keep the option keys

    if arm == "treatment":
        scenario_text = scenario.get("treatment_text")
    elif arm == "placebo":
        scenario_text = scenario.get("placebo_text")
    else:
        scenario_text = None

    results = []
    for i, (cell_id, fields) in enumerate(sorted(cell_representatives.items())):
        if arm == "vanilla":
            persona_block = None
        else:
            persona_block = build_persona_block(fields)
            if contexts and contexts.get(cell_id):
                persona_block += "\n\n" + contexts[cell_id]

        reverse = reverse_half and (i % 2 == 1)
        display_options = list(reversed(options)) if reverse else list(options)

        prompt = build_prompt(
            persona_block=persona_block,
            scenario_text=scenario_text,
            question=question,
            options=shown,
            reverse_options=reverse,
        )

        results.append({
            "cell_id": cell_id,
            "prompt": prompt,
            "options_order": display_options,
            "reversed": reverse,
        })

    return results
