"""Evaluation harness for LLM model benchmarking.

This module provides tools to:
- Benchmark inference speed (tokens/sec)
- Compare commentary quality across models
- Measure memory usage and latency
- Generate evaluation reports

Usage:
    from suksham_vachak.eval import ModelBenchmark, QualityEvaluator

    # Benchmark inference speed
    benchmark = ModelBenchmark()
    results = benchmark.run_speed_test("qwen2.5:7b", num_samples=100)

    # Compare model quality
    evaluator = QualityEvaluator()
    comparison = evaluator.compare_models(["qwen2.5:7b", "llama3.2:3b"])
"""

from .benchmark import ModelBenchmark
from .quality import QualityEvaluator
from .report import EvaluationReport

__all__ = [
    "ModelBenchmark",
    "QualityEvaluator",
    "EvaluationReport",
]
