"""Pydantic data models for weather data ingestion."""

from datetime import datetime

from pydantic import BaseModel, Field


class DistrictTarget(BaseModel):
    """Represents a landslide-vulnerable geographic target for weather monitoring."""

    district_id: str = Field(description="Unique district identifier (e.g. 'wayanad')")
    name: str = Field(description="Display name of the district")
    micro_zone: str = Field(description="Specific high-risk slope or micro-zone")
    latitude: float = Field(description="Latitude coordinate in decimal degrees")
    longitude: float = Field(description="Longitude coordinate in decimal degrees")


class HourlyPrecipitationData(BaseModel):
    """Raw time-series precipitation records fetched from Open-Meteo API."""

    timestamps: list[datetime] = Field(description="Sorted list of observation timestamps")
    precipitation: list[float] = Field(
        description="Hourly precipitation amounts in millimeters (rain + showers)"
    )


class PrecipitationMetrics(BaseModel):
    """Derived multi-window rainfall aggregations and Antecedent Precipitation Index."""

    district_id: str = Field(description="District identifier")
    timestamp: datetime = Field(description="Timestamp of the latest observation")
    rainfall_1h: float = Field(description="Precipitation in the latest completed hour (mm)")
    rainfall_24h: float = Field(description="Trailing 24-hour cumulative precipitation (mm)")
    rainfall_48h: float = Field(description="Trailing 48-hour cumulative precipitation (mm)")
    rainfall_72h: float = Field(description="Trailing 72-hour cumulative precipitation (mm)")
    antecedent_index: float = Field(
        description="Antecedent Precipitation Index (API) with soil drainage decay"
    )


# Pre-configured high-risk micro-zones in Kerala's Western Ghats
DEFAULT_TARGETS: dict[str, DistrictTarget] = {
    "wayanad": DistrictTarget(
        district_id="wayanad",
        name="Wayanad",
        micro_zone="Vythiri / Meppadi / Chooralmala",
        latitude=11.6084,
        longitude=76.0883,
    ),
    "idukki": DistrictTarget(
        district_id="idukki",
        name="Idukki (North / High Range)",
        micro_zone="Munnar / Devikulam / Pettimudi",
        latitude=10.0889,
        longitude=77.0595,
    ),
    "idukki_peerumade": DistrictTarget(
        district_id="idukki_peerumade",
        name="Idukki (South / Peerumade)",
        micro_zone="Vagamon / Elappara / Kudayathoor",
        latitude=9.6850,
        longitude=76.9050,
    ),
    "kottayam": DistrictTarget(
        district_id="kottayam",
        name="Kottayam (Highland)",
        micro_zone="Teekoy / Erattupetta / Kanjirappally",
        latitude=9.6896,
        longitude=76.8160,
    ),
    "kottayam_poonjar": DistrictTarget(
        district_id="kottayam_poonjar",
        name="Kottayam (Poonjar Ridge)",
        micro_zone="Payyanithottam / Poonjar Thekkekara",
        latitude=9.6920,
        longitude=76.8450,
    ),
}
