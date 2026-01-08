"""Benchmark module for LLM inference performance testing.

Measures:
- Tokens per second (generation speed)
- Time to first token (latency)
- Memory usage
- Throughput under load
"""

import contextlib
import gc
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

from suksham_vachak.commentary.providers import OllamaProvider, create_llm_provider
from suksham_vachak.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""

    model: str
    num_samples: int
    total_time_seconds: float
    tokens_generated: int
    tokens_per_second: float
    time_to_first_token_ms: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    memory_peak_mb: float | None = None
    errors: int = 0
    raw_latencies: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "model": self.model,
            "num_samples": self.num_samples,
            "total_time_seconds": round(self.total_time_seconds, 2),
            "tokens_generated": self.tokens_generated,
            "tokens_per_second": round(self.tokens_per_second, 2),
            "time_to_first_token_ms": round(self.time_to_first_token_ms, 2),
            "latency_p50_ms": round(self.latency_p50_ms, 2),
            "latency_p95_ms": round(self.latency_p95_ms, 2),
            "latency_p99_ms": round(self.latency_p99_ms, 2),
            "memory_peak_mb": round(self.memory_peak_mb, 2) if self.memory_peak_mb else None,
            "errors": self.errors,
        }

    def __repr__(self) -> str:
        """Concise representation."""
        return (
            f"BenchmarkResult({self.model}: {self.tokens_per_second:.1f} tok/s, "
            f"p50={self.latency_p50_ms:.0f}ms, p99={self.latency_p99_ms:.0f}ms)"
        )


# Sample cricket prompts for benchmarking
BENCHMARK_PROMPTS = [
    {
        "system": "You are Richie Benaud, the legendary cricket commentator. Respond in 1-3 words maximum.",
        "user": "Kohli hits a boundary through covers.",
    },
    {
        "system": "You are a cricket commentator. Be concise.",
        "user": "The bowler takes a wicket, clean bowled. Score is 245/6 in the 45th over.",
    },
    {
        "system": "You are Richie Benaud. Maximum 5 words.",
        "user": "A massive six over long-on in the death overs. Target is 180, need 12 off 6 balls.",
    },
    {
        "system": "Generate brief cricket commentary.",
        "user": "Dot ball. Good length delivery outside off, batter leaves it alone.",
    },
    {
        "system": "You are a minimalist cricket commentator. One sentence only.",
        "user": "Partnership of 100 runs between Rohit and Kohli in the World Cup final.",
    },
]


class ModelBenchmark:
    """Benchmark LLM models for inference performance.

    Example:
        benchmark = ModelBenchmark()

        # Test a single model
        result = benchmark.run_speed_test("qwen2.5:7b", num_samples=50)
        print(f"Speed: {result.tokens_per_second} tok/s")

        # Compare multiple models
        results = benchmark.compare_models(["qwen2.5:7b", "llama3.2:3b"])
        for r in results:
            print(f"{r.model}: {r.tokens_per_second} tok/s")
    """

    def __init__(self, base_url: str | None = None) -> None:
        """Initialize benchmark runner.

        Args:
            base_url: Ollama server URL. Defaults to localhost:11434.
        """
        self.base_url = base_url
        self._prompts = BENCHMARK_PROMPTS

    def run_speed_test(
        self,
        model: str,
        num_samples: int = 50,
        max_tokens: int = 30,
        warmup_runs: int = 3,
    ) -> BenchmarkResult:
        """Run inference speed benchmark on a model.

        Args:
            model: Model name (e.g., "qwen2.5:7b")
            num_samples: Number of inference runs
            max_tokens: Maximum tokens per response
            warmup_runs: Number of warmup runs (not counted)

        Returns:
            BenchmarkResult with performance metrics
        """
        logger.info("Starting benchmark", model=model, num_samples=num_samples)

        # Create provider
        try:
            provider = create_llm_provider("ollama", model=model, base_url=self.base_url)
        except Exception:
            logger.exception("Failed to create provider", model=model)
            return BenchmarkResult(
                model=model,
                num_samples=0,
                total_time_seconds=0,
                tokens_generated=0,
                tokens_per_second=0,
                time_to_first_token_ms=0,
                latency_p50_ms=0,
                latency_p95_ms=0,
                latency_p99_ms=0,
                errors=1,
            )

        # Warmup runs
        logger.debug("Running warmup", warmup_runs=warmup_runs)
        for _ in range(warmup_runs):
            prompt = self._prompts[0]
            with contextlib.suppress(Exception):
                provider.complete(prompt["system"], prompt["user"], max_tokens=max_tokens)
            gc.collect()

        # Benchmark runs
        latencies: list[float] = []
        total_tokens = 0
        errors = 0
        first_token_times: list[float] = []

        start_time = time.perf_counter()

        for i in range(num_samples):
            prompt = self._prompts[i % len(self._prompts)]

            run_start = time.perf_counter()
            try:
                response = provider.complete(prompt["system"], prompt["user"], max_tokens=max_tokens)
                run_end = time.perf_counter()

                latency_ms = (run_end - run_start) * 1000
                latencies.append(latency_ms)
                total_tokens += response.output_tokens

                # Estimate time to first token (roughly tokens/latency * first token)
                if response.output_tokens > 0:
                    first_token_times.append(latency_ms / response.output_tokens)

            except Exception as e:
                logger.warning("Benchmark run failed", run=i, error=str(e))
                errors += 1

            # Progress logging
            if (i + 1) % 10 == 0:
                logger.debug("Benchmark progress", completed=i + 1, total=num_samples)

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Calculate statistics
        if latencies:
            sorted_latencies = sorted(latencies)
            p50_idx = len(sorted_latencies) // 2
            p95_idx = int(len(sorted_latencies) * 0.95)
            p99_idx = int(len(sorted_latencies) * 0.99)

            result = BenchmarkResult(
                model=model,
                num_samples=num_samples,
                total_time_seconds=total_time,
                tokens_generated=total_tokens,
                tokens_per_second=total_tokens / total_time if total_time > 0 else 0,
                time_to_first_token_ms=statistics.mean(first_token_times) if first_token_times else 0,
                latency_p50_ms=sorted_latencies[p50_idx],
                latency_p95_ms=sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)],
                latency_p99_ms=sorted_latencies[min(p99_idx, len(sorted_latencies) - 1)],
                errors=errors,
                raw_latencies=latencies,
            )
        else:
            result = BenchmarkResult(
                model=model,
                num_samples=num_samples,
                total_time_seconds=total_time,
                tokens_generated=0,
                tokens_per_second=0,
                time_to_first_token_ms=0,
                latency_p50_ms=0,
                latency_p95_ms=0,
                latency_p99_ms=0,
                errors=errors,
            )

        logger.info("Benchmark complete", model=model, tokens_per_second=result.tokens_per_second)
        return result

    def compare_models(
        self,
        models: list[str],
        num_samples: int = 30,
        max_tokens: int = 30,
    ) -> list[BenchmarkResult]:
        """Compare multiple models side-by-side.

        Args:
            models: List of model names to compare
            num_samples: Samples per model
            max_tokens: Max tokens per response

        Returns:
            List of BenchmarkResults, sorted by tokens_per_second
        """
        results = []

        for model in models:
            logger.info("Benchmarking model", model=model)
            result = self.run_speed_test(model, num_samples, max_tokens)
            results.append(result)

            # Cool down between models
            gc.collect()
            time.sleep(2)

        # Sort by speed (fastest first)
        results.sort(key=lambda r: r.tokens_per_second, reverse=True)
        return results

    def list_available_models(self) -> list[str]:
        """List models available on the Ollama server."""
        try:
            provider = OllamaProvider(base_url=self.base_url)
            return provider.list_models()
        except Exception as e:
            logger.warning("Failed to list models", error=str(e))
            return []

    def print_comparison_table(self, results: list[BenchmarkResult]) -> None:
        """Print a formatted comparison table."""
        print("\n" + "=" * 80)
        print("MODEL BENCHMARK COMPARISON")
        print("=" * 80)
        print(f"{'Model':<25} {'Tok/s':>8} {'p50 (ms)':>10} {'p95 (ms)':>10} {'p99 (ms)':>10}")
        print("-" * 80)

        for r in results:
            print(
                f"{r.model:<25} {r.tokens_per_second:>8.1f} {r.latency_p50_ms:>10.0f} "
                f"{r.latency_p95_ms:>10.0f} {r.latency_p99_ms:>10.0f}"
            )

        print("=" * 80)

        if results:
            fastest = results[0]
            print(f"\nFastest: {fastest.model} ({fastest.tokens_per_second:.1f} tokens/sec)")
