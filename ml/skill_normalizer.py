"""Normalisation des compétences vers le référentiel dim_skill (SSMS)."""

from __future__ import annotations

import re
from difflib import get_close_matches

import pandas as pd

from database.sql_server_client import SqlServerClient


class SkillNormalizer:
    def __init__(self, referential: pd.DataFrame | None = None) -> None:
        self._lookup: dict[str, str] = {}
        self._skill_names: list[str] = []
        if referential is not None and not referential.empty:
            self._load_from_dataframe(referential)

    def _load_from_dataframe(self, df: pd.DataFrame) -> None:
        name_col = "skill_name" if "skill_name" in df.columns else df.columns[0]
        for name in df[name_col].dropna().astype(str):
            canonical = name.strip()
            if len(canonical) < 2:
                continue
            key = canonical.lower()
            self._lookup[key] = canonical
            self._skill_names.append(canonical)

    @classmethod
    def from_database(cls, client: SqlServerClient | None = None) -> "SkillNormalizer":
        db = client or SqlServerClient()
        try:
            df = db.fetch_skills_referential()
            return cls(referential=df)
        except Exception:
            return cls()

    @classmethod
    def from_skill_list(cls, skills: list[str]) -> "SkillNormalizer":
        return cls(referential=pd.DataFrame({"skill_name": skills}))

    @property
    def skill_names(self) -> list[str]:
        return list(self._skill_names)

    @property
    def is_loaded(self) -> bool:
        return bool(self._lookup)

    def normalize_token(self, token: str, cutoff: float = 0.88) -> str | None:
        token = token.strip().lower()
        if not token or len(token) < 2:
            return None
        if token in self._lookup:
            return self._lookup[token]
        if len(token) >= 4:
            matches = get_close_matches(token, self._lookup.keys(), n=1, cutoff=cutoff)
            if matches:
                return self._lookup[matches[0]]
        return None

    def match_from_text(self, text: str) -> list[str]:
        if not text or not self._lookup:
            return []
        text_lower = text.lower()
        found: set[str] = set()
        for key, canonical in sorted(self._lookup.items(), key=lambda x: -len(x[0])):
            if len(key) < 3 and key not in {"r", "go", "c#", "c++"}:
                continue
            pattern = r"\b" + re.escape(key) + r"\b"
            if re.search(pattern, text_lower):
                found.add(canonical)
        return sorted(found)

    def normalize_skill_list(self, skills: list[str]) -> list[str]:
        normalized: set[str] = set()
        for skill in skills:
            canon = self.normalize_token(skill)
            if canon:
                normalized.add(canon)
            elif 2 <= len(skill.strip()) <= 50 and len(skill.split()) <= 4:
                normalized.add(skill.strip())
        return sorted(normalized)
