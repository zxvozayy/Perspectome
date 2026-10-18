"""Tests for src.simulation.model."""

import pytest

from src.simulation.model import MockModel


class TestMockModel:
    def test_returns_valid_distribution(self):
        model = MockModel(seed=42)
        dist = model.query("test prompt", ["a", "b", "c"], n_repeats=5, seed=42)
        assert set(dist.keys()) == {"a", "b", "c"}
        assert all(0.0 <= v <= 1.0 for v in dist.values())
        assert abs(sum(dist.values()) - 1.0) < 1e-9

    def test_deterministic(self):
        m1 = MockModel(seed=42)
        m2 = MockModel(seed=42)
        d1 = m1.query("same prompt", ["x", "y"], n_repeats=5, seed=42)
        d2 = m2.query("same prompt", ["x", "y"], n_repeats=5, seed=42)
        assert d1 == d2

    def test_different_prompts_give_different_distributions(self):
        model = MockModel(seed=42)
        d1 = model.query("prompt A", ["x", "y"], n_repeats=5, seed=42)
        d2 = model.query("prompt B", ["x", "y"], n_repeats=5, seed=42)
        assert d1 != d2

    def test_different_seeds_give_different_distributions(self):
        model = MockModel(seed=42)
        d1 = model.query("same prompt", ["x", "y"], n_repeats=5, seed=42)
        d2 = model.query("same prompt", ["x", "y"], n_repeats=5, seed=99)
        assert d1 != d2


class TestOpenAIModel:
    def test_call_cap_raises(self):
        """OpenAIModel should raise RuntimeError when cap is exceeded."""
        from unittest.mock import patch, MagicMock

        with patch.dict("sys.modules", {"openai": MagicMock()}):
            from src.simulation.model import OpenAIModel

            model = OpenAIModel(
                model_snapshot="test-snapshot", max_calls=2, api_key="fake"
            )
            # Manually set call count to the cap.
            model._call_count = 2
            with pytest.raises(RuntimeError, match="Hard call cap reached"):
                model.query("prompt", ["a", "b"], n_repeats=1, seed=42)
