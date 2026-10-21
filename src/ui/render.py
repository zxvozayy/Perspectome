"""Compose the blocks in views.py into one HTML answer per chat message.

The server sends these fragments to the panel as-is; the browser only toggles
chart tabs and opens details. Nothing here computes a metric.
"""

from __future__ import annotations

import re

from src.ui import answers, views
from src.ui.data import Bundle

CHART_VIEWS = (("bars", "Çubuk"), ("dots", "Nokta"), ("slope", "Eğim"), ("map", "Harita"))


def prose(text: str) -> str:
    """The answer texts use **bold** and *italic*; everything else is escaped."""
    out = views.esc(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"\*(.+?)\*", r"<i>\1</i>", out)
    return f'<p class="pt-say">{out}</p>'


def chips(labels: list[str]) -> str:
    buttons = "".join(f'<button type="button" class="chip" data-q="{views.esc(q)}">{views.esc(q)}</button>' for q in labels)
    return f'<div class="chips">{buttons}</div>' if buttons else ""


def details(run: dict, open_: bool = False) -> str:
    return (
        f'<details class="pt-details"{" open" if open_ else ""}>'
        f"<summary>Çalıştırma detayı · {views.esc(run['run_id'])}</summary>"
        f"{views.run_details(run)}</details>"
    )


def chart_tabs(key: str, run: dict, scored: dict | None) -> str:
    panels = {
        "bars": views.arm_bars(run),
        "dots": views.arm_dots(run),
        "slope": views.slope(run, scored),
        "map": views.turkey_map(scored),
    }
    tabs = "".join(
        f'<button type="button" role="tab" data-tab="{k}" aria-selected="{str(i == 0).lower()}">{label}</button>'
        for i, (k, label) in enumerate(CHART_VIEWS)
    )
    body = "".join(
        f'<div class="tab-panel" data-panel="{k}"{"" if i == 0 else " hidden"}>{panels[k]}</div>'
        for i, (k, _) in enumerate(CHART_VIEWS)
    )
    return f'<div class="tabs" id="tabs-{views.esc(key)}"><div class="tab-list" role="tablist" aria-label="Grafik türü">{tabs}</div>{body}</div>'


def scenario(key: str, msg: dict, bundle: Bundle) -> str:
    run = bundle.results.get(msg["run_id"])
    if run is None:
        return prose("Bu çalıştırma artık veri klasöründe yok.")
    scored = bundle.scored(run["scenario_id"])
    noise = (bundle.comparison or {}).get("noise_floor_tvd")
    return (
        prose(views.scenario_text(run, scored, noise))
        + views.warnings(bundle.warnings, scenario_caveat=True)
        + views.effect_headline(scored, noise)
        + chart_tabs(key, run, scored)
        + views.subgroups(scored)
        + details(run)
        + views.footnote()
    )


def validation(bundle: Bundle) -> str:
    comparison = bundle.comparison
    if not comparison:
        return prose("Track C'nin karşılaştırma raporu henüz yok.")
    noise = comparison.get("noise_floor_tvd")
    out = prose(views.validation_text(comparison)) + views.warnings(bundle.warnings)
    for probe in comparison.get("probes") or []:
        out += views.dist_lines(probe) + views.tvd_bars(probe, noise)
        out += "".join(details(r) for r in bundle.runs("probe") if r.get("target_item") == probe["item"])
    return out + views.rank_table(comparison.get("rank_agreement")) + views.models(comparison) + views.footnote()


def run_list(msg: dict, bundle: Bundle) -> str:
    runs = [bundle.results[r] for r in msg["run_ids"] if r in bundle.results]
    return prose(views.details_text(len(runs))) + "".join(details(r, open_=len(runs) == 1) for r in runs)


def message(key: str, msg: dict, last: bool, bundle: Bundle) -> str:
    if msg["role"] == "user":
        return views.user_bubble(msg["text"])
    kind = msg.get("kind")
    if kind == "scenario":
        body = scenario(key, msg, bundle)
        if last and bundle.comparison:
            body += chips([answers.VALIDATION_QUESTION])
    elif kind == "validation":
        body = validation(bundle)
    elif kind == "details":
        body = run_list(msg, bundle)
    elif kind == "comments":
        body = prose(views.comments_intro(msg)) + views.persona_comments(msg)
    else:
        body = prose(views.UNKNOWN_TEXT) + (chips(answers.suggestions(bundle)) if last else "")
    return f'<div class="answer">{views.assistant_label()}{body}</div>'


def chat(chat: dict, bundle: Bundle) -> str:
    """One question and its answer; ``chat["id"]`` keeps element ids unique on the page."""
    msgs = chat["messages"]
    return "".join(message(f"{chat['id']}-{i}", m, i == len(msgs) - 1, bundle) for i, m in enumerate(msgs))
