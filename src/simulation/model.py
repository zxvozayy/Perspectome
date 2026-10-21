"""Model clients: mock (default), OpenAI and Anthropic (--live only)."""

from __future__ import annotations

import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from src.common import env

# Room for a refusal to show itself: with one token, "I can't ..." reads as
# option I on a 9+ option scale. A real answer is one letter, then the model stops.
ANSWER_TOKENS = 3


class NoAnswer(RuntimeError):
    """Every repeat of a query was unreadable (typically the model refused)."""


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

    def summary(self) -> dict:
        return {"mock": True}


class OpenAIModel:
    """Real model client. Only instantiated with --live flag.

    Reads the answer distribution from next-token log-probabilities when the
    model exposes them (one call per prompt, full distribution over the option
    letters; rule 24). Otherwise it samples ``n_repeats`` answers at
    temperature 1. ``temperature: 0`` is never used: it is not deterministic
    and collapses every repeat onto one answer.

    Answers that are not a valid option letter are counted in ``stats`` and
    left out of the distribution, never assigned to an option.

    Never prints API keys or auth headers in logs (rule 31).
    """

    MIN_COVERAGE = 0.5  # share of probability mass that must land on option letters

    def __init__(
        self,
        model_snapshot: str,
        max_calls: int = 200,
        api_key: str | None = None,
        client=None,
    ):
        if client is None:
            try:
                import openai
            except ImportError:
                raise ImportError(
                    "openai package required for live mode. "
                    "Install with: pip install perspectome[llm]"
                )
            client = openai.OpenAI(api_key=api_key)
        self._client = client
        self._model = model_snapshot
        self._max_calls = max_calls
        self._call_count = 0
        self._logprobs_supported = True
        self._lock = threading.Lock()
        self.workers = 1  # parallel repeats per query
        self.stats = {"logprob_queries": 0, "sampled_queries": 0, "parse_failures": 0,
                      "low_coverage": 0, "coverage": []}

    def _reserve(self):
        with self._lock:
            if self._call_count >= self._max_calls:
                raise RuntimeError(
                    f"Hard call cap reached ({self._max_calls}). "
                    "Aborting to prevent runaway spend."
                )
            self._call_count += 1

    def _call(self, prompt: str, max_tokens: int = 1, **kwargs):
        self._reserve()
        return self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            max_tokens=max_tokens,
            **kwargs,
        )

    @staticmethod
    def _letter(token: str, letters: str):
        t = token.strip().rstrip(").:").upper()
        return t if len(t) == 1 and t in letters else None

    def _from_logprobs(self, prompt: str, letters: str):
        if self._call_count >= self._max_calls:  # the cap must never be swallowed below
            self._call(prompt)
        try:
            resp = self._call(prompt, logprobs=True, top_logprobs=20)
            top = resp.choices[0].logprobs.content[0].top_logprobs
        except Exception:
            self._logprobs_supported = False
            return None
        mass = {letter: 0.0 for letter in letters}
        for item in top:
            letter = self._letter(item.token, letters)
            if letter:
                mass[letter] += float(np.exp(item.logprob))
        coverage = sum(mass.values())
        self.stats["coverage"].append(coverage)
        if coverage < self.MIN_COVERAGE:
            self.stats["low_coverage"] += 1
            return None
        self.stats["logprob_queries"] += 1
        return {letter: m / coverage for letter, m in mass.items()}

    def _sample_text(self, prompt: str, seed: int) -> str:
        return self._call(prompt, max_tokens=ANSWER_TOKENS, seed=seed).choices[0].message.content or ""

    def _from_samples(self, prompt: str, letters: str, n_repeats: int, seed: int):
        counts = {letter: 0 for letter in letters}
        with ThreadPoolExecutor(self.workers) as pool:
            texts = list(pool.map(lambda i: self._sample_text(prompt, seed + i), range(n_repeats)))
        for text in texts:
            letter = self._letter(text, letters)
            if letter:
                counts[letter] += 1
            else:
                self.stats["parse_failures"] += 1
        total = sum(counts.values())
        if total == 0:
            raise NoAnswer("No parseable answer in any repeat (the model may have refused).")
        self.stats["sampled_queries"] += 1
        return {letter: c / total for letter, c in counts.items()}

    def query(
        self, prompt: str, options: list[str], n_repeats: int, seed: int,
    ) -> dict[str, float]:
        """``options`` must be in the order shown in the prompt (A, B, C, ...)."""
        from src.simulation.prompt import option_letters

        letters = option_letters(len(options))
        dist = self._from_logprobs(prompt, letters) if self._logprobs_supported else None
        if dist is None:
            dist = self._from_samples(prompt, letters, n_repeats, seed)
        return {opt: dist[letter] for letter, opt in zip(letters, options)}

    def summary(self) -> dict:
        cov = self.stats["coverage"]
        return {
            "logprob_queries": self.stats["logprob_queries"],
            "sampled_queries": self.stats["sampled_queries"],
            "parse_failures": self.stats["parse_failures"],
            "low_coverage": self.stats["low_coverage"],
            "mean_coverage": round(float(np.mean(cov)), 4) if cov else None,
            "calls": self._call_count,
        }


class AnthropicModel(OpenAIModel):
    """Claude through the Anthropic API (--live with a ``claude-*`` snapshot).

    The API returns no log-probabilities, so every query samples ``n_repeats``
    answers at temperature 1 (in parallel) and counts the letters. The key is
    ANTHROPIC_API_KEY or CLAUDE_API_KEY (environment or .env); a key that isn't
    scoped to a workspace also needs ANTHROPIC_WORKSPACE_ID. Never printed.
    """

    def __init__(self, model_snapshot: str, max_calls: int = 200, client=None, workers: int = 8):
        if client is None:
            try:
                import anthropic
            except ImportError:
                raise ImportError("anthropic package required for live mode. "
                                  "Install with: pip install perspectome[llm]")
            key = env.get("ANTHROPIC_API_KEY") or env.get("CLAUDE_API_KEY")
            if not key:
                raise RuntimeError("Set ANTHROPIC_API_KEY or CLAUDE_API_KEY (environment or .env).")
            workspace = env.get("ANTHROPIC_WORKSPACE_ID")
            client = anthropic.Anthropic(api_key=key, max_retries=8,
                                         default_headers={"anthropic-workspace-id": workspace} if workspace else None)
        super().__init__(model_snapshot, max_calls, client=client)
        self._logprobs_supported = False
        self.workers = workers
        self.stats.update(input_tokens=0, output_tokens=0)

    def _sample_text(self, prompt: str, seed: int) -> str:
        self._reserve()
        # sampling temperature is the API default, 1; thinking off, or newer models
        # spend the one-token budget on a thinking block and never answer
        resp = self._client.messages.create(model=self._model, max_tokens=ANSWER_TOKENS, thinking={"type": "disabled"},
                                            messages=[{"role": "user", "content": prompt}])
        with self._lock:
            self.stats["input_tokens"] += resp.usage.input_tokens
            self.stats["output_tokens"] += resp.usage.output_tokens
        return "".join(block.text for block in resp.content if block.type == "text")

    def summary(self) -> dict:
        return {**super().summary(), "input_tokens": self.stats["input_tokens"],
                "output_tokens": self.stats["output_tokens"]}
