#!/usr/bin/env python3
"""
Career Insight Agent — point d'entrée principal.

Usage:
  python main.py train
  python main.py db-test
  python main.py profile-trends
  python main.py analyze --job "Data Analyst" --resume-id 16852973
  python main.py web
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.orchestrator import CareerInsightAgent
from agent.web_research import search_trends_by_category
from config.profile_categories import PROFILE_CATEGORIES
from config.settings import DEFAULT_REPORT_NAME, ML_MAX_CV_SAMPLES, REPORTS_DIR
from database.sql_server_client import SqlServerClient
from ml.resume_loader import get_resume_text_by_id
from ml.train_evaluate import train_and_evaluate
from report.pdf_generator import generate_pdf_report


def cmd_db_test() -> None:
    client = SqlServerClient()
    skills = client.fetch_skills_referential()
    jobs = client.list_job_titles(5)
    sample = client.fetch_job_skills_detailed(jobs[0], top_n=5) if jobs else None
    print("Connexion SSMS OK.")
    print(f"  Compétences (dim_skill) : {len(skills)}")
    print(f"  Top métiers (fact_job_posts) : {', '.join(jobs)}")
    if sample is not None and not sample.empty:
        print(f"  Exemple jointure pour '{jobs[0]}' :")
        for _, row in sample.iterrows():
            print(
                f"    - {row['skill_name']} ({row.get('skill_type', '')}) "
                f"[{row.get('job_title', '')}]"
            )


def cmd_train(limit: int) -> None:
    train_and_evaluate(limit=limit)


def cmd_profile_trends(categories: list[str] | None, top_n: int) -> None:
    from database.sql_server_client import SqlServerClient

    cats = categories or list(PROFILE_CATEGORIES.keys())
    referential: list[str] = []
    try:
        referential = SqlServerClient().fetch_skills_referential()["skill_name"].tolist()
    except Exception:
        pass
    print("\n=== Competences tendance par categorie (DuckDuckGo) ===\n")
    for cat in cats:
        result = search_trends_by_category(cat, top_n=top_n, referential_skills=referential)
        print(f"  [{cat}]")
        print(f"    Requete : {result.query[:80]}...")
        for skill in result.trend_skills:
            print(f"    - {skill}")
        print()


def cmd_analyze(
    cv_path: Path | None,
    resume_id: int | None,
    job_title: str,
    output: Path | None,
) -> None:
    if resume_id is not None:
        cv_text, category = get_resume_text_by_id(resume_id)
        print(f"CV charge (ID={resume_id}, categorie={category})")
    elif cv_path is not None:
        from utils.cv_parser import extract_text_from_cv

        raw = cv_path.read_bytes()
        cv_text = extract_text_from_cv(cv_path.name, raw)
    else:
        raise SystemExit("Indiquez --cv ou --resume-id")

    agent = CareerInsightAgent()
    result = agent.analyze(cv_text=cv_text, target_job_title=job_title)
    report_path = output or (REPORTS_DIR / DEFAULT_REPORT_NAME)
    generate_pdf_report(result, target_job=job_title, output_path=report_path)

    print("\n=== Résultat ===")
    print(f"  Profil : {result.profile_summary[:120]}...")
    print(f"  Compétences : {', '.join(result.candidate_skills[:12])}")
    print(f"  PDF : {report_path}\n")


def cmd_web() -> None:
    from web.app import run_server

    run_server()


def main() -> None:
    parser = argparse.ArgumentParser(description="Career Insight Agent")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("db-test", help="Tester SSMS")
    sub.add_parser("web", help="Lancer l'interface web")

    p_train = sub.add_parser("train", help="Entraîner le modèle ML")
    p_train.add_argument("--limit", type=int, default=ML_MAX_CV_SAMPLES)

    p_trends = sub.add_parser(
        "profile-trends",
        help="Compétences tendance par catégorie (DuckDuckGo)",
    )
    p_trends.add_argument(
        "--category",
        action="append",
        help="Catégorie (ex: HR). Répétable. Défaut : toutes.",
    )
    p_trends.add_argument("--top", type=int, default=12)

    p_analyze = sub.add_parser("analyze", help="Analyser un CV + PDF")
    cv_group = p_analyze.add_mutually_exclusive_group(required=True)
    cv_group.add_argument("--cv", type=Path)
    cv_group.add_argument("--resume-id", type=int)
    p_analyze.add_argument("--job", type=str, required=True)
    p_analyze.add_argument("--output", type=Path, default=None)

    args = parser.parse_args()

    if args.command == "db-test":
        cmd_db_test()
    elif args.command == "train":
        cmd_train(limit=args.limit)
    elif args.command == "profile-trends":
        cmd_profile_trends(categories=args.category, top_n=args.top)
    elif args.command == "analyze":
        cmd_analyze(args.cv, args.resume_id, args.job, args.output)
    elif args.command == "web":
        cmd_web()


if __name__ == "__main__":
    main()
