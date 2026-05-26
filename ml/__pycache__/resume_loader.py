"""Chargement et préparation du dataset Resume.csv (profil + compétences)."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from config.settings import RESUME_CSV_PATH
from ml.skill_normalizer import SkillNormalizer

_SKILLS_PATTERN = re.compile(
    r"\bSkills\b\s*(.+?)(?:\n\s*\n|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_SKILLS_FALLBACK = re.compile(r"\bSkills\b\s*(.+)$", re.IGNORECASE | re.DOTALL)
_SUMMARY_PATTERN = re.compile(
    r"\bSummary\b\s*(.+?)(?:\n\s*(?:Highlights|Experience|Skills|Education)\b|\Z)",
    re.IGNORECASE | re.DOTALL,
)

_MAX_SKILL_LEN = 50
_MAX_SKILL_WORDS = 5


def _is_valid_skill_token(token: str) -> bool:
    token = token.strip().lower()
    if len(token) < 2 or len(token) > _MAX_SKILL_LEN:
        return False
    if len(token.split()) > _MAX_SKILL_WORDS:
        return False
    return True


def extract_skills_from_resume(resume_text: str) -> list[str]:
    if not resume_text or not str(resume_text).strip():
        return []
    text = str(resume_text)
    match = _SKILLS_PATTERN.search(text) or _SKILLS_FALLBACK.search(text)
    if not match:
        return []
    block = match.group(1).strip().split("\n")[0][:1500]
    return sorted(
        {s.strip().lower() for s in re.split(r"[,;|]", block) if _is_valid_skill_token(s)}
    )


def extract_profile_summary(resume_text: str, category: str = "", max_chars: int = 500) -> str:
    parts: list[str] = []
    if category and str(category).strip():
        parts.append(str(category).strip())
    if resume_text:
        summary_match = _SUMMARY_PATTERN.search(str(resume_text))
        if summary_match:
            parts.append(" ".join(summary_match.group(1).split())[:max_chars])
        else:
            lines = [ln.strip() for ln in str(resume_text).splitlines() if ln.strip()]
            if lines:
                parts.append(" ".join(lines[:4])[:max_chars])
    return " ".join(parts).strip()[:max_chars]


def load_resume_csv(path: Path | None = None, limit: int | None = None) -> pd.DataFrame:
    csv_path = path or RESUME_CSV_PATH
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset introuvable : {csv_path}")
    df = pd.read_csv(csv_path, nrows=limit)
    missing = {"Resume_str", "Category"} - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes : {missing}")
    return df


def prepare_labeled_dataset(
    raw_df: pd.DataFrame,
    normalizer: SkillNormalizer | None = None,
    min_skills: int = 2,
) -> pd.DataFrame:
    """
    Labels alignés sur dim_skill : matching référentiel + section Skills normalisée.
    Entrée modèle : texte CV complet (meilleure couverture lexicale.
    """
    norm = normalizer or SkillNormalizer.from_database()
    valid_ref = set(norm.skill_names) if norm.is_loaded else None

    records: list[dict] = []
    for _, row in raw_df.iterrows():
        resume_text = str(row.get("Resume_str", "") or "")
        category = str(row.get("Category", "") or "").strip()
        if not resume_text.strip():
            continue

        labels: set[str] = set(norm.match_from_text(resume_text))
        if len(labels) < min_skills:
            parsed = extract_skills_from_resume(resume_text)
            labels.update(norm.normalize_skill_list(parsed))

        if valid_ref:
            labels = {s for s in labels if s in valid_ref}

        if len(labels) < min_skills:
            continue

        records.append(
            {
                "profile_text": resume_text[:8000],
                "profile_category": category,
                "profile_summary": extract_profile_summary(resume_text, category),
                "skills": sorted(labels),
            }
        )
    return pd.DataFrame(records)


def get_resume_text_by_id(resume_id: int, path: Path | None = None) -> tuple[str, str]:
    csv_path = path or RESUME_CSV_PATH
    df = pd.read_csv(csv_path)
    if "ID" not in df.columns:
        raise ValueError("Colonne ID absente du dataset Resume.csv")
    match = df.loc[df["ID"] == resume_id]
    if match.empty:
        raise ValueError(f"Aucun CV avec ID={resume_id}")
    row = match.iloc[0]
    return str(row["Resume_str"]), str(row.get("Category", ""))
