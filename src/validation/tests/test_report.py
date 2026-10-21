"""comparison.json: contract shape, gating rules, and end-to-end on Track B output."""

import copy
import json

import pandas as pd
import pytest

from src.common import paths
from src.validation import real, report

CONTRACT_TOP = {"generated_at", "persona_set_hash", "noise_floor_tvd", "probes",
                "rank_agreement", "scenarios", "warnings"}
CONTRACT_PROBE = {"item", "options", "real", "methods", "models"}
CONTRACT_SCENARIO = {"scenario_id", "effect_vs_placebo", "effect_tvd", "measurable", "saturated",
                     "equation_baseline_effect", "subgroup_direction", "small_cells", "models_agree"}
OPTS = ["support", "oppose", "uncertain"]


@pytest.fixture
def fixture_report():
    runs = report.load_runs(report.RESULTS_FIXTURES)
    return report.build(runs, real.load(), fixtures=True)


def test_fixture_report_matches_contract(fixture_report):
    assert CONTRACT_TOP <= set(fixture_report)
    probe = fixture_report["probes"][0]
    assert CONTRACT_PROBE <= set(probe)
    assert {"engine", "vanilla", "ml_baseline"} <= set(probe["methods"])
    for m in probe["methods"].values():
        assert {"distribution", "tvd"} <= set(m)
        assert sum(m["distribution"].values()) == pytest.approx(1.0, abs=1e-3)
    assert CONTRACT_SCENARIO <= set(fixture_report["scenarios"][0])
    json.dumps(fixture_report)  # serializable


def test_fixture_report_is_honest_about_its_inputs(fixture_report):
    text = " ".join(fixture_report["warnings"])
    assert "fixture" in text and "Noise floor unknown" in text and "one model" in text


def test_scenarios_never_carry_absolute_shares(fixture_report):
    sc = fixture_report["scenarios"][0]
    assert "real" not in sc and "distribution" not in sc
    assert sum(sc["effect_vs_placebo"].values()) == pytest.approx(0.0, abs=1e-3)


def test_real_distribution_uses_persona_weights():
    frame = pd.DataFrame({"persona_id": ["a", "b"], "weight": [3.0, 1.0], "x": ["yes", "no"]})
    assert real.distribution(frame, "x", ["yes", "no"]) == {"yes": 0.75, "no": 0.25}


def test_real_numeric_answers_match_string_options():
    frame = pd.DataFrame({"persona_id": ["a", "b"], "weight": [1.0, 1.0], "x": [7.0, 3.0]})
    assert real.distribution(frame, "x", ["3", "7"]) == {"3": 0.5, "7": 0.5}


# --- gating: noise floor, saturation, MDD, subgroups -----------------------------

def _scenario_run(seed, treat, placebo, n=2000, cells=None, snapshot="m-1"):
    def arm(dist, sub):
        a = {"response_distribution": dist, "option_usage": {}}
        if sub:
            a["by_subgroup"] = {"age_band": sub}
        return a
    cells = cells or {}
    return {
        "run_id": f"s__{seed}", "run_type": "scenario", "scenario_id": "unemployment_shock_v1",
        "target_item": None, "options": OPTS, "n_personas": n,
        "arms": {"treatment": arm(treat, cells.get("t")), "placebo": arm(placebo, cells.get("p")),
                 "vanilla": {"response_distribution": treat}},
        "metadata": {"model_snapshot": snapshot, "seed": seed, "persona_set_hash": "h", "n_rounds": 3},
    }


T = {"support": .55, "oppose": .40, "uncertain": .05}
T2 = {"support": .54, "oppose": .41, "uncertain": .05}
P = {"support": .35, "oppose": .60, "uncertain": .05}


def _score(runs, cap=float("inf")):
    warnings = []
    noise = report.noise_floor(runs)
    return report.score_scenarios(runs, noise, cap, warnings)[0], noise


def test_noise_floor_is_max_seed_gap():
    assert report.noise_floor([_scenario_run(1, T, P), _scenario_run(2, T2, P)]) == pytest.approx(0.01)
    assert report.noise_floor([_scenario_run(1, T, P)]) is None


def test_large_clean_effect_is_measurable():
    sc, _ = _score([_scenario_run(1, T, P), _scenario_run(2, T2, P)])
    assert sc["measurable"] is True and sc["saturated"] is False
    assert sc["option_of_interest"] == "support"
    assert sc["effect_vs_placebo"]["support"] == pytest.approx(0.195, abs=1e-3)


def test_single_seed_is_never_measurable():
    sc, _ = _score([_scenario_run(1, T, P)])
    assert sc["measurable"] is False


def test_effect_below_noise_floor_is_not_measurable():
    far = {"support": .20, "oppose": .75, "uncertain": .05}  # seed gap 0.35 >> effect
    sc, noise = _score([_scenario_run(1, T, P), _scenario_run(2, far, P)])
    assert noise > sc["effect_tvd"] and sc["measurable"] is False


def test_saturated_placebo_blocks_measurability():
    sat_p = {"support": .95, "oppose": .05, "uncertain": 0}
    sat_t = {"support": .80, "oppose": .20, "uncertain": 0}
    sat_t2 = {"support": .79, "oppose": .21, "uncertain": 0}
    sc, _ = _score([_scenario_run(1, sat_t, sat_p), _scenario_run(2, sat_t2, sat_p)])
    assert sc["saturated"] is True and sc["measurable"] is False


def test_small_n_effect_is_below_mdd():
    runs = [_scenario_run(1, T, P, n=30), _scenario_run(2, T2, P, n=30)]
    sc, _ = _score(runs)
    assert sc["minimum_detectable_difference"] > 0.2 and sc["measurable"] is False


def test_synthetic_personas_dont_add_power():
    """20,000 personas drawn from 1,000 effective respondents have the power of 1,000."""
    runs = [_scenario_run(1, T, P, n=20000), _scenario_run(2, T2, P, n=20000)]
    capped, _ = _score(runs, cap=1000)
    same_n, _ = _score([_scenario_run(1, T, P, n=1000), _scenario_run(2, T2, P, n=1000)])
    assert capped["minimum_detectable_difference"] == pytest.approx(same_n["minimum_detectable_difference"])


def test_subgroups_small_cells_flagged_and_bh_directions():
    cells = {
        "t": {"18-24": {"n": 400, "distribution": {"support": .70, "oppose": .30, "uncertain": 0}},
              "35-44": {"n": 400, "distribution": {"support": .41, "oppose": .59, "uncertain": 0}},
              "65+": {"n": 12, "distribution": {"support": .90, "oppose": .10, "uncertain": 0}}},
        "p": {"18-24": {"n": 400, "distribution": {"support": .40, "oppose": .60, "uncertain": 0}},
              "35-44": {"n": 400, "distribution": {"support": .40, "oppose": .60, "uncertain": 0}},
              "65+": {"n": 12, "distribution": {"support": .10, "oppose": .90, "uncertain": 0}}},
    }
    sc, _ = _score([_scenario_run(1, T, P, cells=cells), _scenario_run(2, T2, P, cells=cells)])
    assert sc["small_cells"] == ["65+"]
    assert sc["subgroup_direction"]["age_band"] == {"18-24": "+", "35-44": "0"}


def test_models_agree_flag():
    flipped_t = {"support": .20, "oppose": .75, "uncertain": .05}
    runs = [_scenario_run(1, T, P, snapshot="m-1"), _scenario_run(1, flipped_t, P, snapshot="m-2")]
    sc, _ = _score(runs)
    assert sc["models_agree"] is False
    sc, _ = _score([_scenario_run(1, T, P, snapshot="m-1"), _scenario_run(1, T2, P, snapshot="m-2")])
    assert sc["models_agree"] is True


def test_rank_agreement_needs_three_items_then_scores_perfect_order():
    base = report.load_runs(report.RESULTS_FIXTURES[1:])[0]
    frame = real.load()
    runs = []
    for item in ("trust_police", "trust_courts", "trust_government"):
        r = copy.deepcopy(base)
        r["target_item"] = item
        r["arms"]["treatment"]["response_distribution"] = real.distribution(frame, item, r["options"])
        runs.append(r)
    out = report.build(runs, frame)
    assert out["rank_agreement"]["n_items"] == 3
    assert out["rank_agreement"]["methods"]["engine"] == pytest.approx(1.0)
    assert all(p["methods"]["engine"]["tvd"] == pytest.approx(0.0, abs=1e-3) for p in out["probes"])


def test_rank_agreement_uses_only_test_items_when_enough():
    probes = [{"item": f"i{k}", "ordinal": True, "role": role, "options": ["1", "2"],
               "real": {"1": k / 10, "2": 1 - k / 10},
               "methods": {"engine": {"distribution": {"1": k / 10, "2": 1 - k / 10}}}}
              for k, role in enumerate(["test", "test", "test", "fit"], start=1)]
    out = report.rank_agreement(probes, [])
    assert out["items"] == ["i1", "i2", "i3"] and out["n_items"] == 3


# --- end to end on Track B's real runner (mock model) ----------------------------

def test_end_to_end_on_simulation_runner(tmp_path):
    runner = pytest.importorskip("src.simulation.runner")
    for seed in (1, 2):
        for name in ("probe_trust_police.yaml", "unemployment_shock_v1.yaml"):
            runner.run_simulation(paths.PERSONAS_FIXTURE, paths.SCENARIOS_DIR / name,
                                  output_dir=tmp_path, seed=seed)
    runs = report.load_runs(sorted(tmp_path.glob("*.json")))
    out = report.build(runs, real.load())
    assert out["noise_floor_tvd"] is not None
    assert [p["item"] for p in out["probes"]] == ["trust_police"]
    assert out["scenarios"][0]["scenario_id"] == "unemployment_shock_v1"
    assert out["scenarios"][0]["equation_baseline_effect"] is not None


def test_rank_agreement_never_mixes_answer_scales():
    def probe(item, options, pos):
        dist = {o: (1.0 if i == pos else 0.0) for i, o in enumerate(options)}
        return {"item": item, "ordinal": True, "role": "test", "options": options, "real": dist,
                "methods": {"engine": {"distribution": dist}}}
    four = ["a", "b", "c", "d"]
    ten = [str(i) for i in range(1, 11)]
    probes = [probe("t1", four, 0), probe("t2", four, 1), probe("t3", four, 2),
              probe("s1", ten, 1), probe("s2", ten, 8)]  # only 2 items on the 1-10 scale
    out = report.rank_agreement(probes, [])
    assert [g["items"] for g in out["scales"]] == [["t1", "t2", "t3"]]
    assert out["items"] == ["t1", "t2", "t3"] and out["methods"]["engine"] == pytest.approx(1.0)
