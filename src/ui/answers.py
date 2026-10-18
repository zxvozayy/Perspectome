"""Map a typed question onto runs that already exist.

There is no model behind the chat box: the dashboard only shows what Tracks B
and C have produced. A question either matches an existing run / report or
gets an honest "nothing has been run for that".
"""

from __future__ import annotations

import re

from src.ui.data import Bundle

# Turkish words a user is likely to type for tokens that appear in scenario ids.
TR_HINTS = {
    "unemployment": ("işsiz",),
    "ai": ("yapay zeka", "yapay zekâ"),
    "adoption": ("benimse", "yaygınlaş"),
    "inflation": ("enflasyon",),
    "tax": ("vergi",),
    "wage": ("ücret", "maaş"),
    "migration": ("göç",),
    "pension": ("emekli",),
    "education": ("eğitim",),
    "health": ("sağlık",),
}
# Ready-made question per scenario family, for the suggestion chips.
SCENARIO_QUESTIONS = {
    "unemployment": "İşsizlik artarsa tutumlar nasıl değişir?",
    "ai": "Hızlı yapay zeka benimsenmesine tepkiler nasıl?",
}
VALIDATION_QUESTION = "Bu sonuçlara ne kadar güvenebiliriz?"
DETAILS_QUESTION = "Çalıştırma detaylarını göster"

_DETAILS = ("detay", "seed", "hash", "çalıştırma", "calistirma", "snapshot", "run ")
_MODELS = ("model",)
_VALIDATION = (
    "güven", "guven", "doğrul", "dogrul", "valid", "tvd", "gerçek", "gercek",
    "isabet", "baseline", "tutarl", "trust", "sıralama",
)
_SKIP_TOKENS = {"v", "shock", "probe", "scenario"}


def _norm(text: str) -> str:
    return text.replace("İ", "i").replace("I", "ı").lower()


def _tokens(scenario_id: str) -> list[str]:
    return [
        t for t in re.split(r"[^a-z]+", scenario_id.lower())
        if len(t) > 1 and t not in _SKIP_TOKENS
    ]


def _score(question: str, scenario_id: str) -> int:
    if scenario_id.lower() in question:
        return 100
    score = 0
    for tok in _tokens(scenario_id):
        if re.search(rf"\b{re.escape(tok)}", question):
            score += 1
        score += sum(1 for hint in TR_HINTS.get(tok, ()) if hint in question)
    return score


def _best_scenario(question: str, bundle: Bundle) -> dict | None:
    scored = [(_score(question, r["scenario_id"]), r) for r in bundle.runs("scenario")]
    scored = [x for x in scored if x[0] > 0]
    return max(scored, key=lambda x: x[0])[1] if scored else None


def suggestions(bundle: Bundle) -> list[str]:
    out = []
    for run in bundle.runs("scenario"):
        toks = _tokens(run["scenario_id"])
        ready = next((SCENARIO_QUESTIONS[t] for t in toks if t in SCENARIO_QUESTIONS), None)
        q = ready or f"{run['scenario_id']} senaryosunda ne değişti?"
        if q not in out:
            out.append(q)
    if bundle.comparison:
        out.append(VALIDATION_QUESTION)
    if bundle.results:
        out.append(DETAILS_QUESTION)
    return out


def route(question: str, bundle: Bundle) -> dict:
    """Return {"kind": scenario|validation|details|unknown, ...ids}."""
    q = _norm(question)
    scenario = _best_scenario(q, bundle)

    if any(k in q for k in _DETAILS):
        run_ids = [scenario["run_id"]] if scenario else list(bundle.results)
        if run_ids:
            return {"kind": "details", "run_ids": run_ids}
    if scenario:
        return {"kind": "scenario", "run_id": scenario["run_id"]}
    if bundle.comparison and any(k in q for k in _VALIDATION + _MODELS):
        return {"kind": "validation"}
    return {"kind": "unknown"}
