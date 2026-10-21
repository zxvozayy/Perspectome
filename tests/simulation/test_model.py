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


class _Item:
    def __init__(self, token, logprob):
        self.token, self.logprob = token, logprob


class _FakeClient:
    """Stands in for openai.OpenAI(); records every request payload."""

    def __init__(self, logprobs=None, answers=None):
        self.requests, self._logprobs, self._answers = [], logprobs, list(answers or [])
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        from types import SimpleNamespace as NS
        self.requests.append(kwargs)
        if kwargs.get("logprobs"):
            if self._logprobs is None:
                raise ValueError("this model does not support logprobs")
            top = [_Item(t, lp) for t, lp in self._logprobs]
            return NS(choices=[NS(logprobs=NS(content=[NS(top_logprobs=top)]), message=NS(content=top[0].token))])
        return NS(choices=[NS(message=NS(content=self._answers.pop(0)))])


class TestOpenAIModelAnswers:
    def _model(self, client, cap=50):
        from src.simulation.model import OpenAIModel
        return OpenAIModel(model_snapshot="test-snapshot", max_calls=cap, client=client)

    def test_reads_distribution_from_logprobs(self):
        import math
        client = _FakeClient(logprobs=[("A", math.log(0.6)), (" B", math.log(0.3)), ("Hmm", math.log(0.1))])
        dist = self._model(client).query("p", ["support", "oppose"], n_repeats=5, seed=1)
        assert dist == pytest.approx({"support": 0.6 / 0.9, "oppose": 0.3 / 0.9})
        assert len(client.requests) == 1 and client.requests[0]["max_tokens"] == 1
        assert client.requests[0]["temperature"] == 1

    def test_falls_back_to_sampling_and_counts_parse_failures(self):
        client = _FakeClient(logprobs=None, answers=["A", "B", "maybe", "A"])
        model = self._model(client)
        dist = model.query("p", ["support", "oppose"], n_repeats=4, seed=1)
        assert dist == {"support": 2 / 3, "oppose": 1 / 3}  # the unparseable answer goes nowhere
        assert model.summary()["parse_failures"] == 1
        assert all(r["temperature"] == 1 for r in client.requests)  # never temperature 0

    def test_letters_follow_the_displayed_order(self):
        import math
        client = _FakeClient(logprobs=[("A", math.log(0.9)), ("B", math.log(0.1))])
        dist = self._model(client).query("p", ["oppose", "support"], n_repeats=1, seed=1)
        assert dist["oppose"] == pytest.approx(0.9)


class _FakeAnthropic:
    """Stands in for anthropic.Anthropic: replies with the next scripted answer."""

    def __init__(self, answers):
        from types import SimpleNamespace
        self._answers, self.requests, self._ns = list(answers), [], SimpleNamespace
        self.messages = self

    def create(self, **kwargs):
        self.requests.append(kwargs)
        text = self._answers.pop(0)
        return self._ns(content=[self._ns(type="text", text=text)],
                        usage=self._ns(input_tokens=10, output_tokens=1))


class TestAnthropicModel:
    def _model(self, answers, cap=50):
        from src.simulation.model import AnthropicModel
        client = _FakeAnthropic(answers)
        return AnthropicModel(model_snapshot="claude-test", max_calls=cap, client=client, workers=1), client

    def test_samples_letters_and_counts_tokens(self):
        model, client = self._model(["A", "B", "?", "A"])
        dist = model.query("p", ["yes", "no"], n_repeats=4, seed=1)
        assert dist == {"yes": 2 / 3, "no": 1 / 3}
        summary = model.summary()
        assert summary["parse_failures"] == 1 and summary["input_tokens"] == 40 and summary["calls"] == 4
        assert all(r["max_tokens"] == 1 and r["model"] == "claude-test" for r in client.requests)

    def test_call_cap_holds(self):
        model, _ = self._model(["A"] * 10, cap=3)
        with pytest.raises(RuntimeError, match="cap"):
            model.query("p", ["yes", "no"], n_repeats=5, seed=1)
