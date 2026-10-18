"""Tests for src.simulation.rounds."""

import numpy as np
import pandas as pd

from src.simulation.rounds import (
    assign_personas_round_1,
    run_round_1,
    run_round_2_fj,
    run_round_3_settle,
)
from src.simulation.model import MockModel


class TestRunRound1:
    def test_returns_distributions_per_cell(self):
        model = MockModel(seed=42)
        prompts = [
            {"cell_id": "c1", "prompt": "p1", "options_order": ["a", "b"], "reversed": False},
            {"cell_id": "c2", "prompt": "p2", "options_order": ["a", "b"], "reversed": False},
        ]
        dists = run_round_1(model, prompts, n_repeats=5, seed=42)
        assert set(dists.keys()) == {"c1", "c2"}
        for dist in dists.values():
            assert abs(sum(dist.values()) - 1.0) < 1e-9


class TestAssignPersonasRound1:
    def test_all_get_valid_choices(self):
        options = ["a", "b", "c"]
        personas = pd.DataFrame({
            "persona_id": ["p1", "p2", "p3"],
            "cell_id": ["c1", "c1", "c2"],
            "weight": [1.0, 1.0, 1.0],
            "region": ["R", "R", "R"],
            "age_band": ["18-24", "18-24", "25-34"],
        })
        cell_dists = {
            "c1": {"a": 0.5, "b": 0.3, "c": 0.2},
            "c2": {"a": 0.1, "b": 0.8, "c": 0.1},
        }
        df = assign_personas_round_1(personas, cell_dists, options, seed=42)
        assert "round_1_choice" in df.columns
        assert all(c in options for c in df["round_1_choice"])


class TestRunRound2FJ:
    def test_stubbornness_1_no_change(self):
        """With stubbornness=1.0 positions should not change."""
        options = ["a", "b"]
        df = pd.DataFrame({
            "persona_id": ["p1", "p2"],
            "cell_id": ["c1", "c2"],
            "weight": [1.0, 1.0],
            "region": ["R", "R"],
            "age_band": ["18-24", "25-34"],
            "round_1_choice": ["a", "b"],
        })
        result = run_round_2_fj(df, options, stubbornness=1.0, seed=42)
        for _, row in result.iterrows():
            dist = row["round_2_distribution"]
            choice = row["round_1_choice"]
            # The chosen option should still dominate.
            assert dist[choice] > 0.9

    def test_stubbornness_0_moves_to_neighbour_mean(self):
        """With stubbornness=0.0 positions should move toward neighbours."""
        options = ["a", "b"]
        df = pd.DataFrame({
            "persona_id": ["p1", "p2"],
            "cell_id": ["c1", "c2"],
            "weight": [1.0, 1.0],
            "region": ["R", "R"],
            "age_band": ["18-24", "25-34"],  # adjacent
            "round_1_choice": ["a", "b"],
        })
        result = run_round_2_fj(df, options, stubbornness=0.0, seed=42)
        # With stubbornness 0, each persona fully adopts neighbour mean.
        d0 = result.iloc[0]["round_2_distribution"]
        d1 = result.iloc[1]["round_2_distribution"]
        # p1's neighbour is p2 (chose b), so p1 should move toward b.
        assert d0["b"] > 0.4
        # p2's neighbour is p1 (chose a), so p2 should move toward a.
        assert d1["a"] > 0.4

    def test_singleton_stays_put(self):
        """A persona with no neighbours stays at initial position."""
        options = ["a", "b"]
        df = pd.DataFrame({
            "persona_id": ["p1"],
            "cell_id": ["c1"],
            "weight": [1.0],
            "region": ["Isolated"],
            "age_band": ["18-24"],
            "round_1_choice": ["a"],
        })
        result = run_round_2_fj(df, options, stubbornness=0.5, seed=42)
        dist = result.iloc[0]["round_2_distribution"]
        assert dist["a"] > 0.9

    def test_positions_stay_in_range(self):
        """No option probability should exceed the initial range of the neighbourhood."""
        options = ["a", "b", "c"]
        df = pd.DataFrame({
            "persona_id": ["p1", "p2", "p3"],
            "cell_id": ["c1", "c2", "c3"],
            "weight": [1.0, 1.0, 1.0],
            "region": ["R", "R", "R"],
            "age_band": ["18-24", "25-34", "35-44"],
            "round_1_choice": ["a", "b", "c"],
        })
        result = run_round_2_fj(df, options, stubbornness=0.3, seed=42)
        for _, row in result.iterrows():
            dist = row["round_2_distribution"]
            for opt in options:
                assert 0.0 <= dist[opt] <= 1.0


class TestRunRound3Settle:
    def test_all_get_valid_final_choices(self):
        options = ["a", "b"]
        df = pd.DataFrame({
            "persona_id": ["p1", "p2"],
            "round_2_distribution": [
                {"a": 0.7, "b": 0.3},
                {"a": 0.2, "b": 0.8},
            ],
        })
        result = run_round_3_settle(df, options, seed=42)
        assert "final_choice" in result.columns
        assert all(c in options for c in result["final_choice"])
