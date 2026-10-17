"""Model clients: mock (default) and OpenAI (--live only)."""

from __future__ import annotations

import hashlib
from typing import Protocol

import numpy as np


class ModelClient(Protocol):
    """Uniform interface for querying a model."""

    def query(
        self, prompt: str, options: list[str], n_repeats: int, seed: int,
    ) -> dict[str, float]:
        """Return {option: probability} summing to 1.0."""
        ...


class MockModel:
    """Deterministic mock that returns Dirichlet-drawn distributions.

    The distribution varies by (seed, prompt) so different cells/scenarios
    get different results, but runs are fully reproducible.
    """

    def __init__(self, seed: int = 42):
        self._base_seed = seed

    def query(
        self, prompt: str, options: list[str], n_repeats: int, seed: int,
    ) -> dict[str, float]:
        # Derive a per-call seed from the hash *value*, never its length (rule 30).
        h = hashlib.sha256(f"{seed}:{prompt}".encode()).hexdigest()
        call_seed = int(h[:16], 16) % (2**31)
        rng = np.random.default_rng(call_seed)

        alpha = np.ones(len(options))  # symmetric Dirichlet
        probs = rng.dirichlet(alpha)

        return {opt: float(p) for opt, p in zip(options, probs)}


class OpenAIModel:
    """Real model client. Only instantiated with --live flag.

    Never prints API keys or auth headers in logs (rule 31).
    """

    def __init__(
        self,
        model_snapshot: str,
        max_calls: int = 200,
        api_key: str | None = None,
    ):
        try:
            import openai  # noqa: F401
        except ImportError:
            raise ImportError(
                "openai package required for live mode. "
                "Install with: pip install perspectome[llm]"
            )
        self._model = model_snapshot
        self._max_calls = max_calls
        self._call_count = 0
        self._api_key = api_key

    def query(
        self, prompt: str, options: list[str], n_repeats: int, seed: int,
    ) -> dict[str, float]:
        import openai

        counts = {opt: 0 for opt in options}

        for _ in range(n_repeats):
            if self._call_count >= self._max_calls:
                raise RuntimeError(
                    f"Hard call cap reached ({self._max_calls}). "
                    "Aborting to prevent runaway spend."
                )
            self._call_count += 1

            client = openai.OpenAI(api_key=self._api_key)
            response = client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                seed=seed,
                max_tokens=20,
            )
            answer = response.choices[0].message.content.strip().lower()

            # Map response to the closest valid option.
            matched = False
            for opt in options:
                if opt.lower() == answer:
                    counts[opt] += 1
                    matched = True
                    break
            if not matched:
                # Unrecognised answer — count but don't crash.
                # Distribute to "uncertain" if present, else first option.
                fallback = "uncertain" if "uncertain" in options else options[0]
                counts[fallback] += 1

        total = sum(counts.values())
        return {opt: c / total for opt, c in counts.items()}
