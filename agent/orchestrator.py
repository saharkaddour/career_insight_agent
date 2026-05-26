"""Agent IA : extraction CV, analyse SSMS et recherche DuckDuckGo en parallèle."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from agent.gap_analysis import GapAnalysis, compute_gaps
from agent.internal_analysis import InternalMarketAnalysis, analyze_internal_market
from agent.web_research import TrendSkillsResult, search_trend_skills
from config.settings import ML_MODEL_PATH
from config.training_links import get_personalized_training_links
from database.sql_server_client import SqlServerClient
from ml.skill_extractor import SkillExtractor
from ml.skill_normalizer import SkillNormalizer


@dataclass
class AgentResult:
    profile_summary: str
    candidate_skills: list[str]
    internal: InternalMarketAnalysis
    trends: TrendSkillsResult
    gaps: GapAnalysis
    recommendations_front: list[str]
    recommendations_bottom: list[str]
    training_links: list[dict]


class CareerInsightAgent:
    def __init__(
        self,
        model_path: Path = ML_MODEL_PATH,
        db_client: SqlServerClient | None = None,
    ) -> None:
        self.db = db_client or SqlServerClient()
        self.model_path = model_path
        self._extractor: SkillExtractor | None = None
        self._referential: list[str] | None = None
        self._normalizer: SkillNormalizer | None = None

    def _get_extractor(self) -> SkillExtractor:
        if self._extractor is None:
            if self.model_path.exists():
                self._extractor = SkillExtractor.load(self.model_path)
            else:
                raise FileNotFoundError(
                    f"Modèle introuvable : {self.model_path}. "
                    "Lancez : python main.py train"
                )
        return self._extractor

    def _get_referential(self) -> list[str]:
        if self._referential is None:
            df = self.db.fetch_skills_referential()
            self._referential = df["skill_name"].tolist()
        return self._referential

    def _get_normalizer(self) -> SkillNormalizer:
        if self._normalizer is None:
            self._normalizer = SkillNormalizer.from_database(self.db)
        return self._normalizer

    def analyze(
        self,
        cv_text: str,
        target_job_title: str,
    ) -> AgentResult:
        extractor = self._get_extractor()
        referential = self._get_referential()

        extraction_result: dict = {}
        internal_result: InternalMarketAnalysis | None = None
        trend_result: TrendSkillsResult | None = None

        def task_extract() -> None:
            extraction_result.update(
                extractor.extract_from_cv(
                    cv_text,
                    referential_skills=referential,
                    normalizer=self._get_normalizer(),
                )
            )

        def task_internal() -> InternalMarketAnalysis:
            return analyze_internal_market(target_job_title, client=self.db)

        def task_trends() -> TrendSkillsResult:
            return search_trend_skills(
                target_job_title,
                referential_skills=referential,
                db_client=self.db,
            )

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(task_extract): "extract",
                executor.submit(task_internal): "internal",
                executor.submit(task_trends): "trends",
            }
            for future in as_completed(futures):
                name = futures[future]
                if name == "extract":
                    future.result()
                elif name == "internal":
                    internal_result = future.result()
                else:
                    trend_result = future.result()

        assert internal_result is not None and trend_result is not None

        candidate_skills = extraction_result.get("skills", [])
        profile_summary = extraction_result.get("profile_summary", "")

        gaps = compute_gaps(
            candidate_skills=candidate_skills,
            internal_primary=internal_result.primary_skills,
            internal_minimum=internal_result.minimum_required_skills,
            trend_skills=trend_result.trend_skills,
        )

        front = list(
            dict.fromkeys(
                gaps.matched_ssms
                + gaps.matched_trends
                + gaps.missing_from_cv_all[:10]
            )
        )[:12]

        bottom = list(dict.fromkeys(gaps.surplus_on_cv))[:12]

        training = get_personalized_training_links(
            missing_skills=gaps.missing_from_cv_all,
            target_job=target_job_title,
        )

        return AgentResult(
            profile_summary=profile_summary,
            candidate_skills=candidate_skills,
            internal=internal_result,
            trends=trend_result,
            gaps=gaps,
            recommendations_front=front,
            recommendations_bottom=bottom,
            training_links=training,
        )
