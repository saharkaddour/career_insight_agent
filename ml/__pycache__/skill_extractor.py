"""Modèle ML d'extraction multi-label des compétences depuis un profil/CV."""

from __future__ import annotations

import re
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer

from ml.skill_normalizer import SkillNormalizer


class SkillExtractor:
    def __init__(self) -> None:
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            min_df=3,
            max_df=0.92,
            stop_words="english",
            sublinear_tf=True,
        )
        self.mlb = MultiLabelBinarizer()
        self.classifier = OneVsRestClassifier(
            LogisticRegression(max_iter=800, class_weight="balanced", C=2.0),
            n_jobs=-1,
        )
        self._skill_vocabulary: list[str] = []
        self.optimal_threshold: float = 0.25
        self.is_fitted = False

    def _filter_skill_lists(
        self,
        skill_lists: list[list[str]],
        min_count: int = 3,
        max_labels: int = 450,
    ) -> tuple[list[list[str]], list[str]]:
        from collections import Counter

        counts: Counter[str] = Counter()
        for skills in skill_lists:
            counts.update(skills)
        kept = {s for s, c in counts.items() if c >= min_count}
        if len(kept) > max_labels:
            top = [s for s, _ in counts.most_common(max_labels)]
            kept = set(top)
        filtered = [[s for s in skills if s in kept] for skills in skill_lists]
        filtered = [s for s in filtered if s]
        vocabulary = sorted(kept)
        return filtered, vocabulary

    def fit(self, texts: list[str], skill_lists: list[list[str]]) -> None:
        filtered_lists, vocabulary = self._filter_skill_lists(skill_lists)
        if not vocabulary:
            raise ValueError("Vocabulaire de compétences vide après filtrage.")
        texts_f: list[str] = []
        skills_f: list[list[str]] = []
        for text, skills in zip(texts, filtered_lists):
            if skills:
                texts_f.append(text)
                skills_f.append(skills)
        if not texts_f:
            raise ValueError("Aucun échantillon valide après filtrage des labels.")
        self.mlb = MultiLabelBinarizer(classes=vocabulary)
        y = self.mlb.fit_transform(skills_f)
        self._skill_vocabulary = list(self.mlb.classes_)
        x = self.vectorizer.fit_transform(texts_f)
        self.classifier.fit(x, y)
        self.is_fitted = True

    def tune_threshold(
        self,
        texts: list[str],
        skill_lists: list[list[str]],
    ) -> float:
        if not self.is_fitted:
            return self.optimal_threshold
        from sklearn.preprocessing import MultiLabelBinarizer as MLB

        mlb = MLB(classes=self._skill_vocabulary)
        y_true = mlb.fit_transform(skill_lists)
        x = self.vectorizer.transform(texts)
        proba = self.classifier.predict_proba(x)

        best_t, best_score = 0.25, 0.0
        for threshold in np.arange(0.15, 0.55, 0.05):
            scores = []
            for i in range(len(texts)):
                idx = np.where(proba[i] >= threshold)[0]
                pred = set(idx)
                true = set(np.where(y_true[i])[0])
                if not true and not pred:
                    scores.append(1.0)
                elif not true or not pred:
                    scores.append(0.0)
                else:
                    scores.append(len(true & pred) / len(true | pred))
            mean_score = float(np.mean(scores))
            if mean_score > best_score:
                best_score = mean_score
                best_t = float(threshold)
        self.optimal_threshold = best_t
        return best_t

    def predict(self, text: str, threshold: float | None = None) -> list[str]:
        if not self.is_fitted:
            raise RuntimeError("Le modèle n'est pas entraîné.")
        t = threshold if threshold is not None else self.optimal_threshold
        x = self.vectorizer.transform([text])
        proba = self.classifier.predict_proba(x)[0]
        indices = np.where(proba >= t)[0]
        return [self._skill_vocabulary[i] for i in indices]

    def extract_from_cv(
        self,
        cv_text: str,
        referential_skills: list[str] | None = None,
        normalizer: SkillNormalizer | None = None,
    ) -> dict:
        norm = normalizer
        if norm is None and referential_skills:
            norm = SkillNormalizer.from_skill_list(referential_skills)
        elif norm is None:
            norm = SkillNormalizer()

        profile_summary = self._extract_profile_summary(cv_text)
        ref_matched = norm.match_from_text(cv_text) if norm.is_loaded else []
        if not ref_matched and referential_skills:
            ref_lower = {s.lower(): s for s in referential_skills}
            ref_matched = self._match_referential(cv_text, ref_lower)

        ml_skills: list[str] = []
        if self.is_fitted:
            ml_skills = self.predict(cv_text)

        combined = sorted(set(ref_matched) | set(ml_skills))
        parsed = extract_skills_from_resume(cv_text)
        if norm.is_loaded:
            combined = sorted(set(combined) | set(norm.normalize_skill_list(parsed)))
        else:
            combined = sorted(set(combined) | set(parsed[:20]))

        return {"profile_summary": profile_summary, "skills": combined}

    @staticmethod
    def _extract_profile_summary(cv_text: str, max_chars: int = 400) -> str:
        from ml.resume_loader import extract_profile_summary

        return extract_profile_summary(cv_text, max_chars=max_chars)

    @staticmethod
    def _match_referential(text: str, ref_lower: dict[str, str]) -> list[str]:
        text_lower = text.lower()
        found = []
        for key, original in ref_lower.items():
            if len(key) < 3 and key not in {"r", "go", "c#", "c++"}:
                continue
            pattern = r"\b" + re.escape(key) + r"\b"
            if re.search(pattern, text_lower):
                found.append(original)
        return found

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "vectorizer": self.vectorizer,
                "mlb": self.mlb,
                "classifier": self.classifier,
                "skill_vocabulary": self._skill_vocabulary,
                "optimal_threshold": self.optimal_threshold,
                "is_fitted": self.is_fitted,
            },
            path,
        )

    @classmethod
    def load(cls, path: Path) -> "SkillExtractor":
        data = joblib.load(path)
        model = cls()
        model.vectorizer = data["vectorizer"]
        model.mlb = data["mlb"]
        model.classifier = data["classifier"]
        model._skill_vocabulary = data["skill_vocabulary"]
        model.optimal_threshold = data.get("optimal_threshold", 0.25)
        model.is_fitted = data["is_fitted"]
        return model


def extract_skills_from_resume(resume_text: str) -> list[str]:
    from ml.resume_loader import extract_skills_from_resume as _extract

    return _extract(resume_text)
