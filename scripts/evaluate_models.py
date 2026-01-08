#!/usr/bin/env python3
"""CLI script for evaluating LLM models.

Usage:
    # List available models
    python scripts/evaluate_models.py --list

    # Benchmark a single model
    python scripts/evaluate_models.py --model qwen2.5:7b --speed

    # Quality evaluation
    python scripts/evaluate_models.py --model qwen2.5:7b --quality

    # Full evaluation (speed + quality)
    python scripts/evaluate_models.py --model qwen2.5:7b --full

    # Compare multiple models
    python scripts/evaluate_models.py --compare qwen2.5:7b llama3.2:3b phi3.5:3.8b

    # Save report to file
    python scripts/evaluate_models.py --compare qwen2.5:7b llama3.2:3b --output report.json
"""

import argparse
import platform
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from suksham_vachak.eval import EvaluationReport, ModelBenchmark, QualityEvaluator
from suksham_vachak.logging import configure_logging


def get_hardware_info() -> dict:
    """Get current hardware information."""
    import os

    try:
        # Try to detect Pi
        if Path("/proc/device-tree/model").exists():
            with open("/proc/device-tree/model") as f:
                device = f.read().strip().replace("\x00", "")
        else:
            device = platform.machine()
    except Exception:
        device = platform.machine()

    return {
        "device": device,
        "cpu": platform.processor() or "unknown",
        "os": f"{platform.system()} {platform.release()}",
        "ram_gb": round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024**3), 1)
        if hasattr(os, "sysconf")
        else None,
    }


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Evaluate LLM models for cricket commentary",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("--list", action="store_true", help="List available models on Ollama server")
    parser.add_argument("--model", type=str, help="Single model to evaluate (e.g., qwen2.5:7b)")
    parser.add_argument("--compare", nargs="+", help="Compare multiple models")
    parser.add_argument("--speed", action="store_true", help="Run speed benchmark only")
    parser.add_argument("--quality", action="store_true", help="Run quality evaluation only")
    parser.add_argument("--full", action="store_true", help="Run both speed and quality evaluation")
    parser.add_argument("--samples", type=int, default=30, help="Number of samples for speed benchmark (default: 30)")
    parser.add_argument("--output", type=str, help="Save report to JSON file")
    parser.add_argument("--markdown", type=str, help="Save report as Markdown file")
    parser.add_argument("--base-url", type=str, help="Ollama server URL (default: http://localhost:11434/v1)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    return parser


def list_available_models(benchmark: ModelBenchmark) -> None:
    """List models available on Ollama server."""
    print("Available models on Ollama server:")
    models = benchmark.list_available_models()
    if models:
        for model in models:
            print(f"  - {model}")
    else:
        print("  No models found (is Ollama running?)")


def run_evaluations(
    models: list[str],
    benchmark: ModelBenchmark,
    evaluator: QualityEvaluator,
    report: EvaluationReport,
    run_speed: bool,
    run_quality: bool,
    samples: int,
) -> None:
    """Run speed and/or quality evaluations for all models."""
    for model in models:
        print(f"\n--- Evaluating: {model} ---\n")

        speed_result = None
        quality_result = None

        if run_speed:
            print("Running speed benchmark...")
            speed_result = benchmark.run_speed_test(model, num_samples=samples)
            print(f"  Speed: {speed_result.tokens_per_second:.1f} tokens/sec")
            print(f"  Latency p50: {speed_result.latency_p50_ms:.0f}ms")
            print(f"  Latency p99: {speed_result.latency_p99_ms:.0f}ms")

        if run_quality:
            print("Running quality evaluation...")
            quality_result = evaluator.evaluate_model(model)
            print(f"  Overall quality: {quality_result.avg_overall:.3f}")
            print(f"  Average word count: {quality_result.avg_word_count:.1f}")

        report.add_result(model, speed_result, quality_result)


def save_reports(report: EvaluationReport, output_path: str | None, markdown_path: str | None) -> None:
    """Save reports to JSON and/or Markdown files."""
    if output_path:
        report.save(output_path)
        print(f"\nReport saved to: {output_path}")

    if markdown_path:
        md_content = report.generate_markdown()
        Path(markdown_path).write_text(md_content)
        print(f"Markdown report saved to: {markdown_path}")


def main():
    parser = create_argument_parser()
    args = parser.parse_args()

    # Configure logging
    configure_logging(level="DEBUG" if args.verbose else "INFO")

    # Initialize benchmarks
    benchmark = ModelBenchmark(base_url=args.base_url)
    evaluator = QualityEvaluator(base_url=args.base_url)

    # List models
    if args.list:
        list_available_models(benchmark)
        return

    # Determine which models to evaluate
    if args.model:
        models_to_eval = [args.model]
    elif args.compare:
        models_to_eval = args.compare
    else:
        print("Error: Specify --model or --compare")
        parser.print_help()
        return

    # Determine what to evaluate
    run_speed = args.speed or args.full or (not args.speed and not args.quality)
    run_quality = args.quality or args.full or (not args.speed and not args.quality)

    # Create report
    report = EvaluationReport()
    report.set_hardware_info(**get_hardware_info())

    print(f"\n{'=' * 60}")
    print("LLM MODEL EVALUATION")
    print(f"{'=' * 60}")
    print(f"Models: {', '.join(models_to_eval)}")
    print(f"Speed benchmark: {'Yes' if run_speed else 'No'}")
    print(f"Quality evaluation: {'Yes' if run_quality else 'No'}")
    print(f"Samples: {args.samples}")
    print(f"{'=' * 60}\n")

    # Run evaluations
    run_evaluations(models_to_eval, benchmark, evaluator, report, run_speed, run_quality, args.samples)

    # Print summary
    report.print_summary()

    # Print comparison tables (results are already stored in report)
    if len(models_to_eval) > 1:
        if run_speed:
            speed_results = [benchmark.run_speed_test(m, num_samples=args.samples) for m in models_to_eval]
            benchmark.print_comparison_table(speed_results)

        if run_quality:
            quality_results = [evaluator.evaluate_model(m) for m in models_to_eval]
            evaluator.print_comparison_table(quality_results)

    # Save reports
    save_reports(report, args.output, args.markdown)


if __name__ == "__main__":
    main()
