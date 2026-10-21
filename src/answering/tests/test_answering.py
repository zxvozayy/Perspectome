"""src/answering: anchors stay off held-out items, importance, cells, prompt context."""

import ast

import numpy as np
import pandas as pd
import pytest

from src.answering import anchors, cells
from src.common import paths, schema
from src.personas import ingest
from src.personas.sources import wvs

pytest.importorskip("sklearn")
from src.answering import importance, qembed  # noqa: E402  (need scikit-learn)


def _spec():
    return anchors._spec()


def test_no_anchor_is_a_heldout_item_or_a_persona_field():
    codes = [it["code"] for it in _spec()["items"]]
    assert len(codes) == len(set(codes))
    assert len({it["name"] for it in _spec()["items"]}) == len(codes)
    heldout_codes = {col for col, _ in ingest.HELDOUT_SRC.values()}
    assert not set(codes) & heldout_codes
    assert not set(codes) & set(wvs.SRC.values())
    assert not {it["name"] for it in _spec()["items"]} & set(schema.HELDOUT_FIELDS)


def test_exclusions_name_heldout_targets_and_real_anchors():
    codes = {it["code"] for it in _spec()["items"]}
    assert set(_spec()["exclude"]) == set(schema.HELDOUT_FIELDS)
    for target, banned in _spec()["exclude"].items():
        assert set(banned) <= codes, target
        assert not {it["code"] for it in anchors.items(target)} & set(banned)
    assert len(anchors.items(None)) == len(codes)


def test_from_raw_drops_missing_and_off_scale_codes():
    item = anchors.items()[0]
    raw = pd.DataFrame({item["code"]: [1, -2, 99, None]})
    out = anchors.from_raw(raw, ["a", "b", "c", "d"])
    assert out[item["name"]].tolist()[0] == 1
    assert out[item["name"]].isna().tolist() == [False, True, True, True]


def _core(n=900, seed=0):
    rng = np.random.default_rng(seed)
    base = {f: rng.choice(schema.CATEGORIES[f], n) for f in schema.CATEGORIES}
    return pd.DataFrame({"persona_id": [f"p{i}" for i in range(n)], "weight": 1.0, **base})


def test_importance_finds_the_field_that_drives_the_answer():
    core = _core()
    answers = pd.DataFrame({"persona_id": core["persona_id"],
                            "q": core["religiosity_band"].map({"low": 1, "medium": 2, "high": 3, "very_high": 3})})
    row = importance.fit(core, answers).loc["q"]
    assert row.idxmax() == "religiosity_band" and row["religiosity_band"] > 0.8
    assert row.sum() == pytest.approx(1.0)


def test_nearest_ranks_by_wording():
    items = [{"code": "A", "title": "Confidence: the army", "question": "How much confidence in the armed forces?"},
             {"code": "B", "title": "Prayer", "question": "How often do you pray?"}]
    best, sim = qembed.nearest("Do you pray every day?", items, 1)[0]
    assert best["code"] == "B" and sim > 0


def test_choose_follows_the_most_similar_anchor():
    names = [it["name"] for it in anchors.items()]
    imp = pd.DataFrame(1.0 / len(importance.FIELDS), index=names, columns=list(importance.FIELDS))
    imp.loc["prayer_frequency"] = 0.0
    imp.loc["prayer_frequency", ["gender", "age_band"]] = [0.7, 0.3]
    out = cells.choose("Apart from weddings and funerals, how often do you pray?", imp, n_fields=2)
    assert out["anchors"][0] == "prayer_frequency"
    assert out["fields"][0] == "gender"
    nothing = cells.choose("zzz qqq", imp)  # no shared words: average importance, no anchors
    assert nothing["anchors"] == [] and len(nothing["fields"]) == cells.N_FIELDS


def test_assign_backs_off_small_cells():
    frame = pd.DataFrame({"gender": ["male"] * 5 + ["female"] * 3,
                          "region": ["Ege"] * 4 + ["Marmara"] + ["Ege"] * 3})
    cell, reps = cells.assign(frame, ["gender", "region"], min_n=3)
    assert cell.tolist() == ["male|Ege"] * 4 + ["all"] + ["female|Ege"] * 3
    assert reps["male|Ege"] == {"gender": "male", "region": "Ege"} and reps["all"] == {}


def test_context_gives_the_weighted_modal_answer():
    item = next(it for it in anchors.items() if it["name"] == "important_religion")
    core = pd.DataFrame({"gender": ["male"] * 3 + ["female"] * 3, "weight": [1, 1, 3, 1, 2, 1],
                         "important_religion": [1, 1, 2, 4, 4, 4]})
    text = cells.context({"gender": "male"}, core, ["important_religion"], min_n=3)
    assert f"{item['title']}: {item['options'][2]} (60%)" in text
    text = cells.context({"gender": "male"}, core, ["important_religion"], min_n=4)  # backs off to everyone
    assert f"{item['options'][4]} (44%)" in text


def test_answer_text_on_a_numbered_scale():
    assert cells.answer_text({1: "Bad", 2: "Good"}, 2) == "Good"
    assert cells.answer_text({1: "Not at all", 2: "2", 3: "Completely"}, 2) == "2 on a scale from 1 (Not at all) to 3 (Completely)"


def test_simulation_and_answering_never_touch_heldout_data():
    """Held-out answers reach validation only: no import of src.validation and no
    held-out file in the code that builds prompts (rule: held-out never reaches simulation)."""
    for folder in ("answering", "simulation"):
        for path in (paths.REPO / "src" / folder).glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    mods = [node.module or ""] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names]
                    assert not any(m.startswith("src.validation") for m in mods), path
                if isinstance(node, (ast.Name, ast.Attribute)):
                    name = node.id if isinstance(node, ast.Name) else node.attr
                    assert name not in ("HELDOUT_CSV", "HELDOUT_FIXTURE", "pull_heldout"), path
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    assert "heldout.csv" not in node.value and "heldout." not in node.value, path
