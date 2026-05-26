"""Recherche web des compétences tendances (DuckDuckGo via package ddgs)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from config.profile_categories import PROFILE_CATEGORIES
from config.settings import DDG_MAX_RESULTS, DDG_REGION
from ml.skill_normalizer import SkillNormalizer

# Mots à exclure (bruit fréquent dans les snippets web)
_NOISE_TOKENS = frozenset({
    "the", "and", "for", "with", "your", "from", "will", "that", "this", "have",
    "are", "was", "been", "being", "their", "they", "you", "our", "can", "may",
    "role", "job", "work", "year", "years", "2024", "2025", "2026", "learn",
    "discover", "read", "more", "click", "here", "article", "blog", "guide",
    "toward", "towards", "continue", "driven", "advancements", "technology",
    "increasing", "importance", "employers", "seeking", "must", "top", "best",
})


@dataclass
class TrendSkillsResult:
    query: str
    trend_skills: list[str]
    snippets: list[str] = field(default_factory=list)
    source_note: str = ""


def _get_ddgs_client():
    try:
        from ddgs import DDGS

        return DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # type: ignore

            return DDGS
        except ImportError:
            return None


def _run_ddg_search(queries: list[str], max_results: int = DDG_MAX_RESULTS) -> tuple[str, list[str]]:
    snippets: list[str] = []
    combined_parts: list[str] = []
    DDGS = _get_ddgs_client()
    if DDGS is None:
        return "", snippets

    seen_queries: set[str] = set()
    for query in queries:
        q = query.strip()
        if not q or q in seen_queries:
            continue
        seen_queries.add(q)
        try:
            with DDGS() as ddgs:
                results = list(
                    ddgs.text(q, region=DDG_REGION, max_results=max_results)
                )
            for item in results:
                title = item.get("title", "") or ""
                body = item.get("body", "") or ""
                snippet = f"{title}. {body}".strip()
                if snippet and snippet not in snippets:
                    snippets.append(snippet[:400])
                    combined_parts.append(snippet)
        except Exception:
            continue

    return " ".join(combined_parts), snippets


def _is_clean_skill(name: str) -> bool:
    low = name.lower().strip()
    if len(low) < 2 or len(low) > 50:
        return False
    if low in _NOISE_TOKENS:
        return False
    if any(bad in low for bad in (" for ", " in 20", "&", "prerequisite", "familiarity", "discover")):
        return False
    if low.startswith(("and ", "the ", "for ", "with ")):
        return False
    if len(low.split()) > 4:
        return False
    return True


def _extract_skills_from_text(
    text: str,
    referential: list[str] | None = None,
    max_skills: int = 20,
) -> list[str]:
    if not text or not text.strip():
        return []

    normalizer = SkillNormalizer.from_skill_list(referential or [])
    found: set[str] = set()

    if normalizer.is_loaded:
        found.update(normalizer.match_from_text(text))

    tech_pattern = re.compile(
        r"\b("
        r"python|java|javascript|typescript|sql|spark|kafka|docker|kubernetes|"
        r"aws|azure|gcp|excel|tableau|power bi|snowflake|databricks|airflow|dbt|"
        r"react|angular|vue|node\.?js|\.net|c\+\+|machine learning|deep learning|"
        r"agile|scrum|devops|git|hris|payroll|recruitment|photoshop|illustrator|figma"
        r")\b",
        re.IGNORECASE,
    )
    for match in tech_pattern.finditer(text):
        token = match.group(0).lower()
        if normalizer.is_loaded:
            canon = normalizer.normalize_token(token)
            if canon:
                found.add(canon)
        elif _is_clean_skill(token):
            found.add(token.title())

    return sorted(s for s in found if _is_clean_skill(s))[:max_skills]


def _ssms_fallback_skills(job_title: str, db_client=None) -> list[str]:
    if db_client is None:
        return []
    try:
        from database.sql_server_client import SqlServerClient

        client = db_client if db_client is not None else SqlServerClient()
        return client.fetch_skills_for_job_title(job_title, top_n=20)
    except Exception:
        return []


def search_trend_skills(
    job_title: str,
    referential_skills: list[str] | None = None,
    max_results: int = DDG_MAX_RESULTS,
    fallback_internal: list[str] | None = None,
    db_client=None,
) -> TrendSkillsResult:
    queries = [
        f"{job_title} top skills required 2025 2026",
        f"{job_title} most in-demand technical skills list",
        f"compétences {job_title} marché emploi 2025",
    ]
    combined, snippets = _run_ddg_search(queries, max_results=max_results)
    source_note = "DuckDuckGo (ddgs)"

    fallback = list(fallback_internal or []) or _ssms_fallback_skills(job_title, db_client)

    if not combined.strip():
        source_note = "SSMS (recherche web indisponible)"
        snippets.append(
            "DuckDuckGo sans résultats — complément depuis fact_job_posts / dim_skill."
        )

    skills = _extract_skills_from_text(combined, referential=referential_skills)
    if not skills and fallback:
        skills = fallback[:20]
        source_note = "SSMS (recherche web indisponible)" if not combined.strip() else "DuckDuckGo + SSMS"
    elif fallback:
        seen = {s.lower() for s in skills}
        for s in fallback:
            if s.lower() not in seen and len(skills) < 20:
                skills.append(s)
                seen.add(s.lower())

    return TrendSkillsResult(
        query=queries[0],
        trend_skills=skills,
        snippets=snippets[:5],
        source_note=source_note,
    )


def search_trends_by_category(
    category: str,
    referential_skills: list[str] | None = None,
    max_results: int = DDG_MAX_RESULTS,
    top_n: int = 15,
) -> TrendSkillsResult:
    key = category.strip().upper().replace(" ", "-")
    base = PROFILE_CATEGORIES.get(
        key,
        f"top {category.replace('-', ' ')} professional skills 2025 2026",
    )
    queries = [base, f"{category.replace('-', ' ')} in-demand skills list 2025"]
    combined, snippets = _run_ddg_search(queries, max_results=max_results)

    if not combined.strip():
        snippets.append("Recherche web indisponible pour cette catégorie.")

    skills = _extract_skills_from_text(
        combined or base,
        referential=referential_skills,
        max_skills=top_n,
    )
    return TrendSkillsResult(
        query=queries[0],
        trend_skills=skills[:top_n],
        snippets=snippets[:3],
        source_note="DuckDuckGo (ddgs)" if combined.strip() else "indisponible",
    )


def search_all_category_trends(
    categories: list[str] | None = None,
    referential_skills: list[str] | None = None,
    top_n: int = 12,
) -> dict[str, TrendSkillsResult]:
    cats = categories or list(PROFILE_CATEGORIES.keys())
    return {
        cat: search_trends_by_category(cat, referential_skills=referential_skills, top_n=top_n)
        for cat in cats
    }
