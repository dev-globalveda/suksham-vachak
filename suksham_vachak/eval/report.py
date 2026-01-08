"""Evaluation report generation and export."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .benchmark import BenchmarkResult
from .quality import ModelQualityReport


@dataclass
class EvaluationReport:
    """Complete evaluation report combining speed and quality benchmarks.

    Example:
        from suksham_vachak.eval import ModelBenchmark, QualityEvaluator, EvaluationReport

        benchmark = ModelBenchmark()
        evaluator = QualityEvaluator()

        report = EvaluationReport()

        for model in ["qwen2.5:7b", "llama3.2:3b"]:
            speed = benchmark.run_speed_test(model)
            quality = evaluator.evaluate_model(model)
            report.add_result(model, speed, quality)

        report.save("evaluation_results.json")
        report.print_summary()
    """

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    hardware_info: dict[str, Any] = field(default_factory=dict)
    results: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add_result(
        self,
        model: str,
        speed_result: BenchmarkResult | None = None,
        quality_result: ModelQualityReport | None = None,
    ) -> None:
        """Add benchmark results for a model."""
        if model not in self.results:
            self.results[model] = {}

        if speed_result:
            self.results[model]["speed"] = speed_result.to_dict()

        if quality_result:
            self.results[model]["quality"] = quality_result.to_dict()

    def set_hardware_info(
        self,
        device: str = "unknown",
        ram_gb: float | None = None,
        cpu: str | None = None,
        os: str | None = None,
    ) -> None:
        """Set hardware information for the report."""
        self.hardware_info = {
            "device": device,
            "ram_gb": ram_gb,
            "cpu": cpu,
            "os": os,
            "timestamp": self.timestamp,
        }

    def get_rankings(self) -> dict[str, list[str]]:
        """Get model rankings by different metrics."""
        models_with_speed = [
            (m, data["speed"]["tokens_per_second"]) for m, data in self.results.items() if "speed" in data
        ]
        models_with_quality = [
            (m, data["quality"]["avg_overall"]) for m, data in self.results.items() if "quality" in data
        ]

        return {
            "by_speed": [m for m, _ in sorted(models_with_speed, key=lambda x: x[1], reverse=True)],
            "by_quality": [m for m, _ in sorted(models_with_quality, key=lambda x: x[1], reverse=True)],
        }

    def get_best_model(self, metric: str = "overall") -> str | None:
        """Get the best model by a specific metric.

        Args:
            metric: "speed", "quality", or "overall" (balanced)

        Returns:
            Best model name or None
        """
        if not self.results:
            return None

        if metric == "speed":
            models = [(m, data.get("speed", {}).get("tokens_per_second", 0)) for m, data in self.results.items()]
        elif metric == "quality":
            models = [(m, data.get("quality", {}).get("avg_overall", 0)) for m, data in self.results.items()]
        else:  # overall - balanced score
            models = []
            for m, data in self.results.items():
                speed = data.get("speed", {}).get("tokens_per_second", 0)
                quality = data.get("quality", {}).get("avg_overall", 0)
                # Normalize and combine (assuming speed range 0-50, quality 0-1)
                normalized_speed = min(speed / 50, 1.0)
                overall = (normalized_speed + quality) / 2
                models.append((m, overall))

        if not models:
            return None

        return max(models, key=lambda x: x[1])[0]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "hardware": self.hardware_info,
            "results": self.results,
            "rankings": self.get_rankings(),
            "best_overall": self.get_best_model("overall"),
            "best_speed": self.get_best_model("speed"),
            "best_quality": self.get_best_model("quality"),
        }

    def save(self, filepath: str | Path) -> None:
        """Save report to JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with filepath.open("w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str | Path) -> "EvaluationReport":
        """Load report from JSON file."""
        filepath = Path(filepath)

        with filepath.open() as f:
            data = json.load(f)

        report = cls(
            timestamp=data.get("timestamp", ""),
            hardware_info=data.get("hardware", {}),
            results=data.get("results", {}),
        )
        return report

    def print_summary(self) -> None:
        """Print a summary of the evaluation."""
        print("\n" + "=" * 80)
        print("EVALUATION REPORT SUMMARY")
        print("=" * 80)
        print(f"Timestamp: {self.timestamp}")

        if self.hardware_info:
            print(f"Hardware: {self.hardware_info.get('device', 'unknown')}")

        print(f"\nModels Evaluated: {len(self.results)}")

        # Speed rankings
        rankings = self.get_rankings()
        if rankings["by_speed"]:
            print("\nSpeed Rankings (fastest first):")
            for i, model in enumerate(rankings["by_speed"], 1):
                speed = self.results[model].get("speed", {}).get("tokens_per_second", 0)
                print(f"  {i}. {model}: {speed:.1f} tok/s")

        # Quality rankings
        if rankings["by_quality"]:
            print("\nQuality Rankings (best first):")
            for i, model in enumerate(rankings["by_quality"], 1):
                quality = self.results[model].get("quality", {}).get("avg_overall", 0)
                print(f"  {i}. {model}: {quality:.3f}")

        # Recommendations
        print("\n" + "-" * 40)
        best_overall = self.get_best_model("overall")
        best_speed = self.get_best_model("speed")
        best_quality = self.get_best_model("quality")

        print("RECOMMENDATIONS:")
        if best_overall:
            print(f"  Best Overall: {best_overall}")
        if best_speed:
            print(f"  Fastest: {best_speed}")
        if best_quality:
            print(f"  Best Quality: {best_quality}")

        print("=" * 80)

    def generate_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            "# LLM Evaluation Report",
            "",
            f"**Generated**: {self.timestamp}",
            "",
        ]

        if self.hardware_info:
            lines.extend([
                "## Hardware",
                "",
                f"- Device: {self.hardware_info.get('device', 'unknown')}",
                f"- RAM: {self.hardware_info.get('ram_gb', 'unknown')} GB",
                f"- CPU: {self.hardware_info.get('cpu', 'unknown')}",
                "",
            ])

        lines.extend([
            "## Results",
            "",
            "| Model | Speed (tok/s) | Quality | p50 Latency (ms) |",
            "|-------|---------------|---------|------------------|",
        ])

        for model, data in self.results.items():
            speed = data.get("speed", {}).get("tokens_per_second", "N/A")
            quality = data.get("quality", {}).get("avg_overall", "N/A")
            p50 = data.get("speed", {}).get("latency_p50_ms", "N/A")

            speed_str = f"{speed:.1f}" if isinstance(speed, float) else speed
            quality_str = f"{quality:.3f}" if isinstance(quality, float) else quality
            p50_str = f"{p50:.0f}" if isinstance(p50, float) else p50

            lines.append(f"| {model} | {speed_str} | {quality_str} | {p50_str} |")

        lines.extend([
            "",
            "## Recommendations",
            "",
            f"- **Best Overall**: {self.get_best_model('overall')}",
            f"- **Fastest**: {self.get_best_model('speed')}",
            f"- **Best Quality**: {self.get_best_model('quality')}",
            "",
        ])

        return "\n".join(lines)
