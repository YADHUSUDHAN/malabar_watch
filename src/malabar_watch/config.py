"""Configuration module for Malabar Watch using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment Meta
    ENVIRONMENT: str = Field(default="development", description="Runtime environment")
    LOG_LEVEL: str = Field(default="INFO", description="Application log level")

    # LLM API Keys
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API Key")
    GEMINI_MODEL: str = Field(default="gemini-3.6-flash", description="Primary LLM Model")


    GROQ_API_KEY: str = Field(default="", description="Groq API Key for Failover")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile", description="Fallback LLM Model")

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = Field(default="", description="Telegram Bot API Token")
    TELEGRAM_CHAT_ID: str = Field(default="", description="Target Telegram Channel/Group Chat ID")

    # Ingestion
    OPEN_METEO_BASE_URL: str = Field(
        default="https://api.open-meteo.com/v1/forecast",
        description="Open-Meteo Weather API Base URL",
    )
    INGESTION_INTERVAL_MINUTES: int = Field(
        default=60,
        description="Polling frequency for weather data",
    )

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///malabar_watch.sqlite",
        description="SQLite Database Connection URL",
    )

    # Risk Engine Thresholds (mm)
    RAINFALL_WARNING_THRESHOLD_24H: float = 100.0
    RAINFALL_HIGH_RISK_THRESHOLD_24H: float = 150.0
    RAINFALL_EXTREME_THRESHOLD_24H: float = 204.4
    ANTECEDENT_PRECIPITATION_INDEX_ALPHA: float = 0.85


# Singleton settings instance
settings = Settings()
