"""Quality evaluation module for comparing commentary output.

Evaluates:
- Brevity (word count, character count)
- Style adherence (persona matching)
- Relevance (mentions key entities)
- Coherence (grammatical correctness)
"""

from dataclasses import dataclass, field
from typing import Any

from suksham_vachak.commentary.providers import create_llm_provider
from suksham_vachak.logging import get_logger
from suksham_vachak.personas import BENAUD, GREIG, Persona

logger = get_logger(__name__)


@dataclass
class QualityScore:
    """Quality scores for a single commentary."""

    brevity_score: float  # 0-1, higher = more concise
    relevance_score: float  # 0-1, mentions key entities
    style_score: float  # 0-1, matches persona style
    overall_score: float  # Weighted average
    word_count: int
    char_count: int
    text: str
    model: str
    persona: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "brevity_score": round(self.brevity_score, 3),
            "relevance_score": round(self.relevance_score, 3),
            "style_score": round(self.style_score, 3),
            "overall_score": round(self.overall_score, 3),
            "word_count": self.word_count,
            "char_count": self.char_count,
            "text": self.text,
            "model": self.model,
            "persona": self.persona,
        }


@dataclass
class ModelQualityReport:
    """Quality report for a model across multiple samples."""

    model: str
    num_samples: int
    avg_brevity: float
    avg_relevance: float
    avg_style: float
    avg_overall: float
    avg_word_count: float
    samples: list[QualityScore] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model": self.model,
            "num_samples": self.num_samples,
            "avg_brevity": round(self.avg_brevity, 3),
            "avg_relevance": round(self.avg_relevance, 3),
            "avg_style": round(self.avg_style, 3),
            "avg_overall": round(self.avg_overall, 3),
            "avg_word_count": round(self.avg_word_count, 1),
        }


# Test scenarios for quality evaluation
QUALITY_TEST_CASES = [
    {
        "event": "Kohli hits a boundary through covers off Anderson",
        "entities": ["kohli", "boundary", "four", "anderson", "cover"],
        "persona": "benaud",
        "ideal_length": 5,  # Benaud is minimalist
    },
    {
        "event": "Wicket! Bumrah gets Smith caught behind for 45",
        "entities": ["wicket", "bumrah", "smith", "caught", "45"],
        "persona": "benaud",
        "ideal_length": 3,
    },
    {
        "event": "Massive six by Rohit over long-on, the ball lands in the crowd",
        "entities": ["six", "rohit", "long-on", "crowd", "massive"],
        "persona": "greig",
        "ideal_length": 15,  # Greig is more dramatic
    },
    {
        "event": "Dot ball, good length outside off, left alone",
        "entities": ["dot", "ball", "left", "good"],
        "persona": "benaud",
        "ideal_length": 2,
    },
    {
        "event": "Partnership reaches 100 between Gill and Kohli in the World Cup final",
        "entities": ["partnership", "100", "gill", "kohli", "world cup"],
        "persona": "greig",
        "ideal_length": 20,
    },
]


class QualityEvaluator:
    """Evaluate commentary quality across different models.

    Example:
        evaluator = QualityEvaluator()

        # Evaluate single model
        report = evaluator.evaluate_model("qwen2.5:7b")
        print(f"Quality: {report.avg_overall}")

        # Compare models
        reports = evaluator.compare_models(["qwen2.5:7b", "llama3.2:3b"])
    """

    def __init__(self, base_url: str | None = None) -> None:
        """Initialize evaluator.

        Args:
            base_url: Ollama server URL
        """
        self.base_url = base_url
        self._test_cases = QUALITY_TEST_CASES
        self._personas = {
            "benaud": BENAUD,
            "greig": GREIG,
        }

    def _calculate_brevity_score(self, text: str, ideal_length: int) -> float:
        """Calculate brevity score based on word count vs ideal.

        Closer to ideal = higher score.
        Too long = penalty.
        """
        word_count = len(text.split())

        if word_count == 0:
            return 0.0

        if word_count <= ideal_length:
            # Perfect or under ideal
            return 1.0
        else:
            # Penalty for being too verbose
            ratio = ideal_length / word_count
            return max(0.0, ratio)

    def _calculate_relevance_score(self, text: str, entities: list[str]) -> float:
        """Calculate relevance based on entity mentions."""
        text_lower = text.lower()
        mentioned = sum(1 for entity in entities if entity.lower() in text_lower)
        return mentioned / len(entities) if entities else 0.0

    def _calculate_style_score(self, text: str, persona: Persona) -> float:
        """Calculate style adherence score.

        For minimalist personas: shorter is better, no filler words.
        For dramatic personas: more descriptive, exclamations OK.
        """
        word_count = len(text.split())

        if persona.is_minimalist:
            # Minimalist: penalize verbosity, filler words
            filler_words = ["the", "and", "but", "very", "really", "just", "that"]
            filler_count = sum(1 for word in text.lower().split() if word in filler_words)

            # Score based on brevity and lack of filler
            brevity_factor = 1.0 if word_count <= 5 else max(0.0, 1.0 - (word_count - 5) * 0.1)
            filler_factor = max(0.0, 1.0 - filler_count * 0.2)

            return (brevity_factor + filler_factor) / 2
        else:
            # Dramatic: allow more words, reward punctuation variety
            has_exclamation = "!" in text
            has_description = word_count >= 10

            score = 0.5
            if has_exclamation:
                score += 0.25
            if has_description:
                score += 0.25

            return min(1.0, score)

    def evaluate_single(
        self,
        model: str,
        test_case: dict[str, Any],
        max_tokens: int = 50,
    ) -> QualityScore:
        """Evaluate a single test case."""
        persona_name = test_case["persona"]
        persona = self._personas.get(persona_name, BENAUD)

        # Build prompt
        if persona.is_minimalist:
            system = f"You are {persona.name}. Respond in 1-5 words maximum. Be extremely concise."
        else:
            system = f"You are {persona.name}. Be dramatic and descriptive."

        user = f"Commentate on: {test_case['event']}"

        # Generate commentary
        try:
            provider = create_llm_provider("ollama", model=model, base_url=self.base_url)
            response = provider.complete(system, user, max_tokens=max_tokens)
            text = response.text.strip()
        except Exception as e:
            logger.warning("Generation failed", model=model, error=str(e))
            text = ""

        # Calculate scores
        brevity = self._calculate_brevity_score(text, test_case["ideal_length"])
        relevance = self._calculate_relevance_score(text, test_case["entities"])
        style = self._calculate_style_score(text, persona)

        # Weighted overall (brevity matters most for cricket commentary)
        overall = brevity * 0.4 + relevance * 0.3 + style * 0.3

        return QualityScore(
            brevity_score=brevity,
            relevance_score=relevance,
            style_score=style,
            overall_score=overall,
            word_count=len(text.split()),
            char_count=len(text),
            text=text,
            model=model,
            persona=persona_name,
        )

    def evaluate_model(
        self,
        model: str,
        test_cases: list[dict[str, Any]] | None = None,
    ) -> ModelQualityReport:
        """Evaluate a model across all test cases.

        Args:
            model: Model name to evaluate
            test_cases: Custom test cases (uses defaults if None)

        Returns:
            ModelQualityReport with aggregated scores
        """
        cases = test_cases or self._test_cases
        scores: list[QualityScore] = []

        logger.info("Evaluating model quality", model=model, num_cases=len(cases))

        for case in cases:
            score = self.evaluate_single(model, case)
            scores.append(score)
            logger.debug(
                "Test case result",
                event=case["event"][:30],
                overall=score.overall_score,
                words=score.word_count,
            )

        # Aggregate scores
        if scores:
            report = ModelQualityReport(
                model=model,
                num_samples=len(scores),
                avg_brevity=sum(s.brevity_score for s in scores) / len(scores),
                avg_relevance=sum(s.relevance_score for s in scores) / len(scores),
                avg_style=sum(s.style_score for s in scores) / len(scores),
                avg_overall=sum(s.overall_score for s in scores) / len(scores),
                avg_word_count=sum(s.word_count for s in scores) / len(scores),
                samples=scores,
            )
        else:
            report = ModelQualityReport(
                model=model,
                num_samples=0,
                avg_brevity=0,
                avg_relevance=0,
                avg_style=0,
                avg_overall=0,
                avg_word_count=0,
            )

        logger.info("Quality evaluation complete", model=model, avg_overall=report.avg_overall)
        return report

    def compare_models(
        self,
        models: list[str],
        test_cases: list[dict[str, Any]] | None = None,
    ) -> list[ModelQualityReport]:
        """Compare quality across multiple models.

        Args:
            models: List of model names
            test_cases: Custom test cases

        Returns:
            List of ModelQualityReports, sorted by overall score
        """
        reports = []

        for model in models:
            report = self.evaluate_model(model, test_cases)
            reports.append(report)

        # Sort by overall score (highest first)
        reports.sort(key=lambda r: r.avg_overall, reverse=True)
        return reports

    def print_comparison_table(self, reports: list[ModelQualityReport]) -> None:
        """Print formatted comparison table."""
        print("\n" + "=" * 90)
        print("MODEL QUALITY COMPARISON")
        print("=" * 90)
        print(f"{'Model':<25} {'Overall':>10} {'Brevity':>10} {'Relevance':>10} " f"{'Style':>10} {'Avg Words':>10}")
        print("-" * 90)

        for r in reports:
            print(
                f"{r.model:<25} {r.avg_overall:>10.3f} {r.avg_brevity:>10.3f} "
                f"{r.avg_relevance:>10.3f} {r.avg_style:>10.3f} {r.avg_word_count:>10.1f}"
            )

        print("=" * 90)

        if reports:
            best = reports[0]
            print(f"\nBest Quality: {best.model} (overall: {best.avg_overall:.3f})")

    def print_detailed_results(self, report: ModelQualityReport) -> None:
        """Print detailed results for a single model."""
        print(f"\n{'=' * 60}")
        print(f"DETAILED RESULTS: {report.model}")
        print(f"{'=' * 60}")

        for i, sample in enumerate(report.samples, 1):
            print(f"\n[{i}] Persona: {sample.persona}")
            print(f"    Text: {sample.text[:60]}{'...' if len(sample.text) > 60 else ''}")
            print(f"    Words: {sample.word_count}, Overall: {sample.overall_score:.3f}")
            print(
                f"    Brevity: {sample.brevity_score:.3f}, Relevance: {sample.relevance_score:.3f}, "
                f"Style: {sample.style_score:.3f}"
            )
