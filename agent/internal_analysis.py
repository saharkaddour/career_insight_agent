"""Analyse interne via SSMS (fact_job_posts + dim_skill + bridge_job_skill)."""

from __future__ import annotations

from dataclasses import dataclass, field

from database.sql_server_client import SqlServerClient


@dataclass
class JobSkillDetail:
    skill_name: str
    skill_type: str
    frequency: int
    job_title: str = ""


@dataclass
class InternalMarketAnalysis:
    target_job: str
    primary_skills: list[str]
    minimum_required_skills: list[str]
    skills_detail: list[JobSkillDetail] = field(default_factory=list)
    skills_by_type: dict[str, list[str]] = field(default_factory=dict)


def analyze_internal_market(
    target_job_title: str,
    client: SqlServerClient | None = None,
    top_primary: int = 25,
    min_frequency_pct: float = 0.12,
) -> InternalMarketAnalysis:
    db = client or SqlServerClient()
    detail_df = db.fetch_job_skills_detailed(target_job_title, top_n=top_primary)
    primary = db.fetch_skills_for_job_title(target_job_title, top_n=top_primary)
    minimum = db.fetch_minimum_skills_for_job(target_job_title, min_frequency_pct=min_frequency_pct)

    skills_detail: list[JobSkillDetail] = []
    skills_by_type: dict[str, list[str]] = {}

    if not detail_df.empty:
        for _, row in detail_df.iterrows():
            stype = str(row.get("skill_type", "") or "other")
            sname = str(row["skill_name"])
            skills_detail.append(
                JobSkillDetail(
                    skill_name=sname,
                    skill_type=stype,
                    frequency=int(row.get("frequency", 0)),
                    job_title=str(row.get("job_title", "") or ""),
                )
            )
            skills_by_type.setdefault(stype, [])
            if sname not in skills_by_type[stype]:
                skills_by_type[stype].append(sname)

    return InternalMarketAnalysis(
        target_job=target_job_title,
        primary_skills=primary,
        minimum_required_skills=minimum,
        skills_detail=skills_detail,
        skills_by_type=skills_by_type,
    )
