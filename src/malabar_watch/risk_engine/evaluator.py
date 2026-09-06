"""Deterministic rule evaluator implementing calibrated Kerala landslide threshold matrix."""

from typing import TYPE_CHECKING

from malabar_watch.risk_engine.models import RiskLevel

if TYPE_CHECKING:
    from malabar_watch.ingestion.models import PrecipitationMetrics


class RiskEvaluator:
    """Evaluates precipitation metrics against regional geotechnical thresholds for Kerala.

    Threshold Matrix (SPEC-002):
    - LOW:      24h < 50mm,  48h < 90mm,  API < 60
    - MODERATE: 24h >= 50mm, 48h >= 90mm, API >= 60
    - HIGH:     24h >= 100mm, 48h >= 150mm, API >= 100
    - SEVERE:   24h >= 200mm, 48h >= 250mm, API >= 150

    Rule Precedence: Highest tier among 24h, 48h, and API dictates final risk level.
    """

    # Threshold constants
    SEVERE_24H = 200.0
    SEVERE_48H = 250.0
    SEVERE_API = 150.0

    HIGH_24H = 100.0
    HIGH_48H = 150.0
    HIGH_API = 100.0

    MODERATE_24H = 50.0
    MODERATE_48H = 90.0
    MODERATE_API = 60.0

    @classmethod
    def evaluate_values(
        cls,
        rainfall_24h: float,
        rainfall_48h: float,
        antecedent_index: float,
    ) -> tuple[RiskLevel, list[str]]:
        """Evaluates raw numerical values and produces a RiskLevel with human-readable audit rules.

        Args:
            rainfall_24h: Trailing 24h precipitation in mm.
            rainfall_48h: Trailing 48h precipitation in mm.
            antecedent_index: Antecedent Precipitation Index (soil moisture decay model).

        Returns:
            Tuple of (RiskLevel, triggered_rules list of strings).
        """
        # Collect severe triggers
        severe_rules: list[str] = []
        if rainfall_24h >= cls.SEVERE_24H:
            severe_rules.append(f"24h rainfall ({rainfall_24h:.1f}mm) >= {cls.SEVERE_24H:.1f}mm")
        if rainfall_48h >= cls.SEVERE_48H:
            severe_rules.append(f"48h rainfall ({rainfall_48h:.1f}mm) >= {cls.SEVERE_48H:.1f}mm")
        if antecedent_index >= cls.SEVERE_API:
            severe_rules.append(f"API index ({antecedent_index:.1f}) >= {cls.SEVERE_API:.1f}")

        if severe_rules:
            return RiskLevel.SEVERE, severe_rules

        # Collect high triggers
        high_rules: list[str] = []
        if rainfall_24h >= cls.HIGH_24H:
            high_rules.append(f"24h rainfall ({rainfall_24h:.1f}mm) >= {cls.HIGH_24H:.1f}mm")
        if rainfall_48h >= cls.HIGH_48H:
            high_rules.append(f"48h rainfall ({rainfall_48h:.1f}mm) >= {cls.HIGH_48H:.1f}mm")
        if antecedent_index >= cls.HIGH_API:
            high_rules.append(f"API index ({antecedent_index:.1f}) >= {cls.HIGH_API:.1f}")

        if high_rules:
            return RiskLevel.HIGH, high_rules

        # Collect moderate triggers
        moderate_rules: list[str] = []
        if rainfall_24h >= cls.MODERATE_24H:
            moderate_rules.append(
                f"24h rainfall ({rainfall_24h:.1f}mm) >= {cls.MODERATE_24H:.1f}mm"
            )
        if rainfall_48h >= cls.MODERATE_48H:
            moderate_rules.append(
                f"48h rainfall ({rainfall_48h:.1f}mm) >= {cls.MODERATE_48H:.1f}mm"
            )
        if antecedent_index >= cls.MODERATE_API:
            moderate_rules.append(f"API index ({antecedent_index:.1f}) >= {cls.MODERATE_API:.1f}")

        if moderate_rules:
            return RiskLevel.MODERATE, moderate_rules

        # Below all warning thresholds -> LOW
        return RiskLevel.LOW, []

    @classmethod
    def evaluate_metrics(
        cls, metrics: "PrecipitationMetrics"
    ) -> tuple[RiskLevel, list[str]]:
        """Convenience method to evaluate a PrecipitationMetrics instance directly."""
        return cls.evaluate_values(
            rainfall_24h=metrics.rainfall_24h,
            rainfall_48h=metrics.rainfall_48h,
            antecedent_index=metrics.antecedent_index,
        )


def evaluate_metrics(metrics: "PrecipitationMetrics") -> tuple[RiskLevel, list[str]]:
    """Functional shortcut for RiskEvaluator.evaluate_metrics."""
    return RiskEvaluator.evaluate_metrics(metrics)
