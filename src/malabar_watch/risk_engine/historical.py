"""Historical landslide context store for regional grounding of early warnings."""

import json
from pathlib import Path

from malabar_watch.risk_engine.models import HistoricalEvent, RiskLevel


class HistoricalContextStore:
    """Manages verified historical landslide disaster events for Kerala's Western Ghats."""

    def __init__(self, data_path: str | Path | None = None) -> None:
        self.data_path = self._resolve_data_path(data_path)
        self._events: list[HistoricalEvent] = []
        self._load_events()

    def _resolve_data_path(self, data_path: str | Path | None) -> Path:
        """Locates the historical_events.json dataset across common package/workdir locations."""
        if data_path:
            p = Path(data_path)
            if p.exists():
                return p

        # Check candidate locations
        candidates = [
            Path("data/historical_events.json"),
            Path(__file__).parent.parent / "data" / "historical_events.json",
            Path(__file__).parent / "historical_events.json",
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()

        # Fallback to default expected path
        return Path("data/historical_events.json")

    def _load_events(self) -> None:
        """Parses and validates JSON records into HistoricalEvent models."""
        if not self.data_path.exists():
            self._events = []
            return

        with open(self.data_path, encoding="utf-8") as f:
            raw_data = json.load(f)

        self._events = [HistoricalEvent.model_validate(item) for item in raw_data]

    def get_all_events(self) -> list[HistoricalEvent]:
        """Returns all loaded historical disaster events."""
        return list(self._events)

    def get_event_by_id(self, event_id: str) -> HistoricalEvent | None:
        """Retrieves a specific disaster event by unique slug."""
        for event in self._events:
            if event.event_id.lower() == event_id.lower():
                return event
        return None

    def find_precedent(
        self,
        district: str,
        risk_level: RiskLevel,
        rainfall_24h: float = 0.0,
    ) -> HistoricalEvent | None:
        """Attaches the most relevant historical landslide precedent for HIGH/SEVERE risks.

        Args:
            district: District or micro-zone identifier (e.g. 'wayanad', 'kottayam_poonjar').
            risk_level: Evaluated RiskLevel.
            rainfall_24h: Observed 24-hour rainfall in mm.

        Returns:
            HistoricalEvent instance if risk is HIGH/SEVERE and district matches, else None.
        """
        # Historical context is only attached to elevated threats (HIGH or SEVERE)
        if risk_level not in (RiskLevel.HIGH, RiskLevel.SEVERE):
            return None

        # Normalize district identifier (e.g. 'kottayam_poonjar' -> 'kottayam')
        base_district = district.lower().split("_")[0].strip()

        # Find all historical events recorded for this district
        district_matches = [e for e in self._events if e.district.lower() == base_district]

        if not district_matches:
            # Graceful None fallback when district has no historical match in database
            return None

        # Filter by identical analog threshold level if available
        same_level_matches = [
            e for e in district_matches if e.analog_threshold_level.upper() == risk_level.value
        ]

        pool = same_level_matches if same_level_matches else district_matches

        # Pick the historical event closest to the current 24h rainfall
        return min(pool, key=lambda e: abs(e.rainfall_24h_mm - rainfall_24h))
