"""The UI's honesty rules (src/ui/README.md), checked on the rendered HTML."""

import copy
import re
from pathlib import Path

import pytest

from src.common import paths
from src.ui import answers, views
from src.ui.data import load

UI_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def bundle():
    return load(results_dir=paths.RESULTS_FIXTURES[0].parent, comparison_path=paths.COMPARISON_FIXTURE)


@pytest.fixture
def scored(bundle):
    return copy.deepcopy(bundle.comparison["scenarios"][0])


def test_loads_without_pipeline_code(bundle):
    assert len(bundle.runs("scenario")) == 1 and len(bundle.runs("probe")) == 1
    for py in UI_DIR.glob("*.py"):
        assert not re.search(r"src\.(personas|simulation|validation)", py.read_text())


def test_measurable_effect_is_the_headline(scored):
    html = views.effect_headline(scored, 0.04)
    assert "+14 puan" in html and "%" not in re.sub(r"style=\"[^\"]*\"", "", html)


def test_unmeasurable_effect_shows_no_number(scored):
    scored["measurable"] = False
    html = views.effect_headline(scored, 0.04)
    assert views.NO_EFFECT in html
    assert not re.search(r"\d puan", html) and "0,14" not in html


def test_unscored_scenario_shows_no_effect(bundle):
    run = bundle.runs("scenario")[0]
    assert views.NOT_SCORED in views.effect_headline(None, 0.04)
    assert not re.search(r"\d puan", views.slope(run, None))
    assert not re.search(r"\d puan", views.scenario_text(run, None, 0.04))


def test_small_cells_are_greyed_and_show_no_direction(scored):
    html = views.subgroups(scored)  # in the fixture every cell is small
    assert html.count(views.SMALL_CELL) == 6
    assert "arrow" not in html


def test_subgroups_show_arrows_never_percentages(scored):
    scored["small_cells"] = ["65+"]
    html = views.subgroups(scored)
    assert html.count('class="arrow') == 5 and html.count(views.SMALL_CELL) == 1
    assert "%" not in re.sub(r"style=\"[^\"]*\"", "", html)


def test_income_and_province_breakdowns_are_never_rendered(scored):
    scored["subgroup_direction"]["income_decile"] = {"1": "+", "10": "-"}
    scored["subgroup_direction"]["province"] = {"Ankara": "+"}
    html = views.subgroups(scored)
    assert "income" not in html and "Ankara" not in html


def test_warnings_are_verbatim_with_the_prior_caveat(bundle):
    html = views.warnings(bundle.warnings + ["a <b> & c"], scenario_caveat=True)
    for w in bundle.warnings:
        assert w in html
    assert "a &lt;b&gt; &amp; c" in html
    assert "This may reflect the model&#x27;s prior, not the population." in html


def test_routing(bundle):
    run_id = bundle.runs("scenario")[0]["run_id"]
    assert answers.route("İşsizlik artarsa ne olur?", bundle) == {"kind": "scenario", "run_id": run_id}
    assert answers.route(answers.VALIDATION_QUESTION, bundle)["kind"] == "validation"
    assert answers.route(answers.DETAILS_QUESTION, bundle)["kind"] == "details"
    assert answers.route("Bugün hava nasıl?", bundle)["kind"] == "unknown"
    for q in answers.suggestions(bundle):
        assert answers.route(q, bundle)["kind"] != "unknown"


def test_no_real_runs_means_nothing_shown(tmp_path):
    """The site never falls back to fabricated example data."""
    empty = load(results_dir=tmp_path, comparison_path=tmp_path / "none.json")
    assert empty.results == {} and empty.comparison is None
