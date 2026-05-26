"""Analyse des écarts : compétences du CV vs marché (SSMS + DuckDuckGo)."""

from __future__ import annotations

from dataclasses import dataclass, field


def _normalize(skills: list[str]) -> set[str]:
    return {s.strip().lower() for s in skills if s}


@dataclass
class GapAnalysis:
    """Écarts du point de vue du candidat (ce qui manque ou est aligné sur son CV)."""

    # Présentes sur le CV et demandées par le marché
    matched_ssms: list[str] = field(default_factory=list)
    matched_trends: list[str] = field(default_factory=list)
    # Absentes du CV mais exigées par le marché (focus principal)
    missing_from_cv_ssms: list[str] = field(default_factory=list)
    missing_from_cv_trends: list[str] = field(default_factory=list)
    missing_from_cv_all: list[str] = field(default_factory=list)
    # Présentes sur le CV mais peu/pas demandées par le marché cible
    surplus_on_cv: list[str] = field(default_factory=list)

    # Alias rétrocompatibles
    @property
    def matched_internal(self) -> list[str]:
        return self.matched_ssms

    @property
    def missing_internal(self) -> list[str]:
        return self.missing_from_cv_ssms

    @property
    def missing_trends(self) -> list[str]:
        return self.missing_from_cv_trends

    @property
    def obsolete_or_low_priority(self) -> list[str]:
        return self.surplus_on_cv


def compute_gaps(
    candidate_skills: list[str],
    internal_primary: list[str],
    internal_minimum: list[str],
    trend_skills: list[str],
) -> GapAnalysis:
    """
    Compare le CV aux exigences marché (SSMS + tendances web).
    Les listes « missing_from_cv_* » = compétences demandées par le marché
    mais absentes du CV du candidat.
    """
    cand = _normalize(candidate_skills)
    ssms_required = list(dict.fromkeys(internal_primary + internal_minimum))
    trends_required = list(dict.fromkeys(trend_skills))
    ssms_set = _normalize(ssms_required)
    trends_set = _normalize(trends_required)

    matched_ssms = [s for s in candidate_skills if s.lower() in ssms_set]
    matched_trends = [s for s in candidate_skills if s.lower() in trends_set]

    missing_from_cv_ssms = [s for s in ssms_required if s.lower() not in cand][:15]
    missing_from_cv_trends = [s for s in trends_required if s.lower() not in cand][:15]

    combined_missing: list[str] = []
    seen: set[str] = set()
    for skill in missing_from_cv_ssms + missing_from_cv_trends:
        key = skill.lower()
        if key not in seen:
            seen.add(key)
            combined_missing.append(skill)

    market_union = ssms_set | trends_set
    surplus_on_cv = [s for s in candidate_skills if s.lower() not in market_union]

    return GapAnalysis(
        matched_ssms=sorted(set(matched_ssms), key=str.lower),
        matched_trends=sorted(set(matched_trends), key=str.lower),
        missing_from_cv_ssms=missing_from_cv_ssms,
        missing_from_cv_trends=missing_from_cv_trends,
        missing_from_cv_all=combined_missing[:20],
        surplus_on_cv=surplus_on_cv[:15],
    )
