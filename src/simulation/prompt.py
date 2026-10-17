"""Build LLM prompts from persona cells, scenarios, and options."""

from __future__ import annotations


def build_persona_block(cell_fields: dict) -> str:
    """Natural-language persona description from conditioning fields only.

    Never references held-out fields.
    """
    return (
        f"You are a {cell_fields['age_band']} year old {cell_fields['gender']} "
        f"with a {cell_fields['education_level']} level education, "
        f"living in a {cell_fields['settlement_type']} area of {cell_fields['region']}. "
        f"You are {cell_fields['marital_status']}, "
        f"{cell_fields['employment_status']}, "
        f"and in income decile {cell_fields['income_decile']}."
    )


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
      [options, reversed if flagged]
      Instruction to pick exactly one option.
    """
    display_options = list(reversed(options)) if reverse_options else list(options)

    parts: list[str] = []
    if persona_block:
        parts.append(persona_block)
    if scenario_text:
        parts.append(scenario_text.strip())
    parts.append(question.strip())
    parts.append("Options: " + ", ".join(display_options))
    parts.append("Respond with exactly one of the options above, nothing else.")

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
