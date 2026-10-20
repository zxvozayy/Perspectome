"""Tests for src.simulation.rounds."""

import numpy as np
import pandas as pd

from src.simulation.model import MockModel
from src.simulation.rounds import initial_vectors, run_fj, run_round_1


def _personas(regions, bands):
    return pd.DataFrame({"region": regions, "age_band": bands})


class TestRound1:
    def test_returns_distributions_per_cell(self):
        model = MockModel(seed=42)
        prompts = [
            {"cell_id": "c1", "prompt": "p1", "options_order": ["a", "b"]},
            {"cell_id": "c2", "prompt": "p2", "options_order": ["b", "a"]},
        ]
        out = run_round_1(model, prompts, n_repeats=3, seed=1)
        assert set(out) == {"c1", "c2"}
        for dist in out.values():
            assert abs(sum(dist.values()) - 1.0) < 1e-9

    def test_initial_vectors_follow_the_cell(self):
        personas = pd.DataFrame({"cell_id": ["c1", "c2", "c1"]})
        cells = {"c1": {"a": 0.8, "b": 0.2}, "c2": {"b": 1.0}}
        x = initial_vectors(personas, cells, ["a", "b"])
        assert np.allclose(x, [[0.8, 0.2], [0.0, 1.0], [0.8, 0.2]])


class TestFriedkinJohnsen:
    def test_stubbornness_1_no_change(self):
        df = _personas(["Ege", "Ege"], ["25-34", "25-34"])
        x0 = np.array([[0.9, 0.1], [0.1, 0.9]])
        assert np.allclose(run_fj(df, x0, stubbornness=1.0, steps=3), x0)

    def test_stubbornness_0_moves_to_neighbour_mean(self):
        df = _personas(["Ege", "Ege"], ["25-34", "35-44"])
        x0 = np.array([[0.9, 0.1], [0.1, 0.9]])
        x = run_fj(df, x0, stubbornness=0.0, steps=1)
        assert np.allclose(x[0], [0.1, 0.9]) and np.allclose(x[1], [0.9, 0.1])

    def test_non_adjacent_bands_and_other_regions_are_not_neighbours(self):
        df = _personas(["Ege", "Ege", "Marmara"], ["18-24", "45-54", "18-24"])
        x0 = np.array([[0.9, 0.1], [0.1, 0.9], [0.5, 0.5]])
        assert np.allclose(run_fj(df, x0, stubbornness=0.0, steps=2), x0)

    def test_singleton_and_unknown_band_stay_put(self):
        df = _personas(["Ege", None], ["25-34", None])
        x0 = np.array([[0.7, 0.3], [0.2, 0.8]])
        assert np.allclose(run_fj(df, x0, stubbornness=0.3, steps=2), x0)

    def test_positions_stay_in_neighbourhood_range_and_sum_to_one(self):
        rng = np.random.default_rng(0)
        df = _personas(["Ege"] * 30, list(rng.choice(["25-34", "35-44", "45-54"], 30)))
        x0 = rng.dirichlet(np.ones(3), size=30)
        x = run_fj(df, x0, stubbornness=0.4, steps=3)
        assert np.allclose(x.sum(axis=1), 1.0)
        assert (x.min(axis=0) >= x0.min(axis=0) - 1e-9).all() and (x.max(axis=0) <= x0.max(axis=0) + 1e-9).all()

    def test_matches_the_explicit_loop(self):
        """Parity with the textbook update (rule 29), before clipping matters."""
        rng = np.random.default_rng(1)
        df = _personas(["Ege"] * 6 + ["Marmara"] * 4,
                       ["25-34", "35-44", "25-34", "45-54", "18-24", "35-44", "25-34", "25-34", "35-44", "65+"])
        x0 = rng.dirichlet(np.ones(2), size=10)
        s = 0.6
        bands = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
        n = len(df)
        nb = [[j for j in range(n) if j != i and df.region[i] == df.region[j]
               and abs(bands.index(df.age_band[i]) - bands.index(df.age_band[j])) <= 1] for i in range(n)]
        expected = np.array([s * x0[i] + (1 - s) * x0[nb[i]].mean(axis=0) if nb[i] else x0[i] for i in range(n)])
        for i in range(n):  # clip to the neighbourhood range, as the engine does
            hood = x0[nb[i] + [i]]
            expected[i] = np.clip(expected[i], hood.min(axis=0), hood.max(axis=0))
        expected /= expected.sum(axis=1, keepdims=True)
        assert np.allclose(run_fj(df, x0, stubbornness=s, steps=1), expected)
