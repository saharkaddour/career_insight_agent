"""Interface web Career Insight Agent."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_file, url_for

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.orchestrator import CareerInsightAgent
from agent.web_research import search_all_category_trends
from config.settings import REPORTS_DIR, WEB_HOST, WEB_PORT
from config.training_links import FREE_TRAINING_LINKS
from database.sql_server_client import SqlServerClient
from utils.cv_parser import extract_text_from_cv
from report.html_report import render_html_report
from report.pdf_generator import generate_pdf_report

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "career-insight-dev-key-change-in-production"
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024

_category_cache: dict | None = None


def _read_cv_upload() -> str:
    if "cv_file" not in request.files:
        raise ValueError("Aucun fichier CV fourni.")
    file = request.files["cv_file"]
    if not file or not file.filename:
        raise ValueError("Sélectionnez un fichier CV.")
    raw = file.read()
    return extract_text_from_cv(file.filename, raw)


def _get_category_trends() -> dict[str, list[str]]:
    global _category_cache
    if _category_cache is None:
        referential: list[str] = []
        try:
            referential = SqlServerClient().fetch_skills_referential()["skill_name"].tolist()
        except Exception:
            pass
        results = search_all_category_trends(
            top_n=10,
            referential_skills=referential,
        )
        _category_cache = {cat: r.trend_skills for cat, r in results.items()}
    return _category_cache


@app.route("/", methods=["GET"])
def index():
    job_suggestions: list[str] = []
    try:
        job_suggestions = SqlServerClient().list_job_titles(15)
    except Exception:
        pass
    return render_template(
        "index.html",
        training_links=FREE_TRAINING_LINKS,
        training_personalized=False,
        category_trends=_get_category_trends(),
        job_suggestions=job_suggestions,
        report_html=None,
        download_token=None,
        target_job="",
    )


@app.route("/analyze", methods=["POST"])
def analyze():
    target_job = (request.form.get("target_job") or "").strip()
    if not target_job:
        flash("Indiquez le poste visé.", "error")
        return redirect(url_for("index"))

    try:
        cv_text = _read_cv_upload()
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))

    try:
        agent = CareerInsightAgent()
        result = agent.analyze(cv_text=cv_text, target_job_title=target_job)
    except FileNotFoundError:
        flash("Modèle ML absent. Exécutez : python main.py train", "error")
        return redirect(url_for("index"))
    except Exception as exc:
        flash(f"Erreur d'analyse : {exc}", "error")
        return redirect(url_for("index"))

    token = uuid.uuid4().hex[:12]
    pdf_path = REPORTS_DIR / f"rapport_{token}.pdf"
    generate_pdf_report(result, target_job=target_job, output_path=pdf_path)
    report_html = render_html_report(result, target_job=target_job)

    job_suggestions: list[str] = []
    try:
        job_suggestions = SqlServerClient().list_job_titles(15)
    except Exception:
        pass

    return render_template(
        "index.html",
        training_links=result.training_links,
        training_personalized=True,
        category_trends=_get_category_trends(),
        job_suggestions=job_suggestions,
        report_html=report_html,
        download_token=token,
        target_job=target_job,
    )


@app.route("/download/<token>")
def download(token: str):
    pdf_path = REPORTS_DIR / f"rapport_{token}.pdf"
    if not pdf_path.exists():
        flash("Rapport introuvable ou expiré.", "error")
        return redirect(url_for("index"))
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name="rapport_competences.pdf",
        mimetype="application/pdf",
    )


def run_server() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host=WEB_HOST, port=WEB_PORT, debug=False)


if __name__ == "__main__":
    run_server()
