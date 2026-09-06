"""Autonomous pipeline orchestrator for Malabar Watch.

Executes: Data Ingestion (SPEC-001) -> Deterministic Risk Scoring (SPEC-002)
          -> Resilient Dual-LLM Advisory (SPEC-003) -> Telegram Dispatch (SPEC-004).
"""

from __future__ import annotations

import logging
from typing import Any

from malabar_watch.bot.dispatcher import AlertDispatcher
from malabar_watch.config import settings
from malabar_watch.ingestion import DataIngestionService
from malabar_watch.llm import DualLLMGateway
from malabar_watch.risk_engine import RiskAssessmentService
from malabar_watch.storage import DatabaseManager

logger = logging.getLogger(__name__)


class PipelineRunner:
    """Orchestrates an autonomous early-warning execution cycle across all micro-zones."""

    def __init__(
        self,
        db: DatabaseManager | None = None,
        ingestion_service: DataIngestionService | None = None,
        risk_service: RiskAssessmentService | None = None,
        llm_gateway: DualLLMGateway | None = None,
        dispatcher: AlertDispatcher | None = None,
    ) -> None:
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        self.db = db or DatabaseManager(db_path=db_path)
        self.db.initialize_schema()

        self.ingestion_service = ingestion_service or DataIngestionService(db_manager=self.db)
        self.risk_service = risk_service or RiskAssessmentService(db_manager=self.db)
        self.llm_gateway = llm_gateway or DualLLMGateway()
        self.dispatcher = dispatcher or AlertDispatcher(db=self.db)

    async def run_cycle(
        self,
        dry_run: bool = False,
        force_alert: bool = False,
    ) -> dict[str, Any]:
        """Runs a complete hourly pipeline cycle across all monitored micro-zones.

        Args:
            dry_run: If True, simulates dispatch without calling Telegram API.
            force_alert: If True, forces bilingual advisory generation and alert dispatch.

        Returns:
            Dictionary detailing cycle results per district.
        """
        logger.info("Starting Malabar Watch autonomous pipeline cycle...")
        results: dict[str, Any] = {}

        # 1. Ingestion: Fetch weather data
        try:
            metrics_dict = await self.ingestion_service.fetch_and_process_all()
        except Exception as e:
            logger.error("Data ingestion failure in cycle: %s", e)
            return {"error": f"Ingestion failed: {e}"}

        # 2. Risk Evaluation & Downstream Actions
        for district_id, metrics in metrics_dict.items():
            logger.info("Evaluating district=%s", district_id)
            assessment = self.risk_service.assess_metrics(metrics)
            district_result: dict[str, Any] = {
                "risk_level": assessment.risk_level.value,
                "escalation_state": assessment.escalation_state.value,
                "requires_alert": assessment.requires_alert,
                "dispatched": False,
            }

            # 3. LLM Gateway & Alert Broadcast
            if assessment.requires_alert or force_alert:
                logger.info(
                    "Alert required for %s (risk=%s, escalation=%s). Synthesizing advisory...",
                    district_id,
                    assessment.risk_level.value,
                    assessment.escalation_state.value,
                )
                try:
                    advisory = await self.llm_gateway.generate_advisory(assessment)
                    district_result["advisory"] = {
                        "provider_used": advisory.provider_used,
                        "summary_en": advisory.summary_en,
                        "summary_ml": advisory.summary_ml,
                    }

                    # 4. Dispatch Alert
                    dispatch_stats = await self.dispatcher.dispatch_alert(
                        assessment=assessment,
                        advisory=advisory,
                        dry_run=dry_run,
                    )
                    district_result["dispatch_stats"] = dispatch_stats
                    district_result["dispatched"] = True
                except Exception as e:
                    logger.error("Advisory/dispatch failure for %s: %s", district_id, e)
                    district_result["error"] = str(e)

            results[district_id] = district_result

        logger.info("Pipeline cycle finished successfully.")
        return results
