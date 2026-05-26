"""Pipeline Train/Test avec normalisation dim_skill et réglage du seuil."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MultiLabelBinarizer

from config.settings import ML_MAX_CV_SAMPLES, ML_MODEL_PATH, ML_RANDOM_STATE, ML_TEST_SIZE
from ml.resume_loader import extract_skills_from_resume, load_resume_csv, prepare_labeled_dataset
from ml.skill_extractor import SkillExtractor
from ml.skill_normalizer import SkillNormalizer

ACCURACY_TARGET = 0.95


def _jaccard_accuracy(y_true, y_pred) -> float:
    scores = []
    for true_row, pred_row in zip(y_true, y_pred):
        t = set(np.where(true_row)[0])
        p = set(np.where(pred_row)[0])
        if not t and not p:
            scores.append(1.0)
        elif not t or not p:
            scores.append(0.0)
        else:
            scores.append(len(t & p) / len(t | p))
    return float(np.mean(scores))


def _hybrid_predict(extractor: SkillExtractor, normalizer: SkillNormalizer, text: str) -> list[str]:
    ref = set(normalizer.match_from_text(text))
    ml = set(extractor.predict(text)) if extractor.is_fitted else set()
    parsed = set(normalizer.normalize_skill_list(extract_skills_from_resume(text)))
    return sorted(ref | ml | parsed)


def train_and_evaluate(
    limit: int = ML_MAX_CV_SAMPLES,
    model_path: Path = ML_MODEL_PATH,
    verbose: bool = True,
) -> dict:
    normalizer = SkillNormalizer.from_database()
    raw = load_resume_csv(limit=limit)
    dataset = prepare_labeled_dataset(raw, normalizer=normalizer)

    if dataset.empty:
        raise ValueError(
            "Dataset vide. Vérifiez Resume.csv et la connexion SSMS (dim_skill) pour les labels."
        )

    texts = dataset["profile_text"].tolist()
    skill_lists = dataset["skills"].tolist()

    x_train, x_val, y_train, y_val = train_test_split(
        texts,
        skill_lists,
        test_size=ML_TEST_SIZE,
        random_state=ML_RANDOM_STATE,
    )

    extractor = SkillExtractor()
    extractor.fit(x_train, y_train)
    optimal_t = extractor.tune_threshold(x_val, y_val)

    vocab = set(extractor._skill_vocabulary)
    y_val_vocab = [[s for s in skills if s in vocab] for skills in y_val]

    mlb = MultiLabelBinarizer(classes=extractor._skill_vocabulary)
    pairs = [
        (t, skills)
        for t, skills in zip(x_val, y_val_vocab)
        if skills
    ]
    if not pairs:
        raise ValueError("Jeu de test vide après filtrage vocabulaire.")
    x_eval, y_eval = zip(*pairs)
    y_true = mlb.fit_transform(y_eval)

    y_pred_labels = [_hybrid_predict(extractor, normalizer, t) for t in x_eval]
    y_pred = mlb.transform([[s for s in preds if s in vocab] for preds in y_pred_labels])

    ref_only = [
        sorted(set(s for s in normalizer.match_from_text(t) if s in vocab))
        for t in x_eval
    ]
    y_pred_ref = mlb.transform(ref_only)
    referential_jaccard = _jaccard_accuracy(y_true, y_pred_ref)

    strict_acc = accuracy_score(y_true, y_pred)
    jaccard_acc = _jaccard_accuracy(y_true, y_pred)
    micro_f1 = f1_score(y_true, y_pred, average="micro", zero_division=0)

    extractor.save(model_path)

    metrics = {
        "train_size": len(x_train),
        "test_size": len(x_eval),
        "dataset_size": len(dataset),
        "strict_accuracy": strict_acc,
        "jaccard_accuracy": jaccard_acc,
        "referential_jaccard": referential_jaccard,
        "micro_f1": micro_f1,
        "optimal_threshold": optimal_t,
        "referential_size": len(normalizer.skill_names),
        "meets_95_jaccard": jaccard_acc >= ACCURACY_TARGET,
        "model_path": str(model_path),
    }

    if verbose:
        print("\n=== Evaluation (hybride referentiel + ML) ===")
        print(f"  Source                 : data/Resume.csv + dim_skill")
        print(f"  Referentiel SSMS       : {metrics['referential_size']} competences")
        print(f"  Profils labellises     : {metrics['dataset_size']}")
        print(f"  Train / Test           : {metrics['train_size']} / {metrics['test_size']}")
        print(f"  Seuil ML optimal       : {optimal_t:.2f}")
        print(f"  Accuracy stricte       : {strict_acc:.2%}  (toutes les competences exactes)")
        print(f"  Accuracy Jaccard       : {jaccard_acc:.2%}  (chevauchement partiel)")
        print(f"  Jaccard (referentiel)  : {referential_jaccard:.2%}")
        print(f"  F1 micro               : {micro_f1:.2%}")
        status = "ATTEINT" if jaccard_acc >= ACCURACY_TARGET else "non atteint"
        print(f"  Objectif 95% (Jaccard) : {status}")
        print(f"  Modele                 : {model_path}\n")

    return metrics
