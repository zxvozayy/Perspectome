"""Build LLM prompts from persona cells, scenarios, and options."""

from __future__ import annotations


# Fields that define an archetype cell (Track A's cell_id). Only these describe a
# cell; any other field would be one arbitrary member's value, not the cell's.
CELL_FIELDS = ("age_band", "gender", "education_level")

# Single-token option labels, so a model's answer can be read from its
# next-token log-probabilities (rule 24). Rule 25: every option gets one.
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def option_letters(n: int) -> str:
    if n > len(LETTERS):
        raise ValueError(f"{n} options; at most {len(LETTERS)} can be labelled")
    return LETTERS[:n]


def build_persona_block(cell_fields: dict) -> str:
    """Natural-language persona description from conditioning fields only.

    Never references held-out fields. Missing values are left out rather than
    written as "nan".
    """
    def has(key):
        v = cell_fields.get(key)
        return v is not None and str(v) not in ("", "nan", "<NA>")

    text = (
        f"You are a {cell_fields['age_band']} year old {cell_fields['gender']} "
        f"with a {cell_fields['education_level']} level education"
    )
    if has("settlement_type") and has("region"):
        text += f", living in a {cell_fields['settlement_type']} area of {cell_fields['region']}"
    text += "."
    extras = [str(cell_fields[k]) for k in ("marital_status", "employment_status") if has(k)]
    if extras:
        text += " You are " + ", ".join(extras) + "."
    if has("income_decile"):
        text += f" Your household is in income decile {cell_fields['income_decile']}."
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
) -> list[dict]:
    """Build all prompts for one arm.

    Parameters
    ----------
    arm : "treatment" | "placebo" | "vanilla"
    scenario : parsed scenario dict
    cell_representatives : {cell_id: {field: value, ...}} for each unique cell
    reverse_half : if True, alternate cells get reversed option order

    Returns
    -------
    List of dicts: {cell_id, prompt, options_order, reversed}
    """
    question = scenario["question"]
    options = scenario["options"]

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

        reverse = reverse_half and (i % 2 == 1)
        display_options = list(reversed(options)) if reverse else list(options)

        prompt = build_prompt(
            persona_block=persona_block,
            scenario_text=scenario_text,
            question=question,
            options=options,
            reverse_options=reverse,
        )

        results.append({
            "cell_id": cell_id,
            "prompt": prompt,
            "options_order": display_options,
            "reversed": reverse,
        })

    return results
