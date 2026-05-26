"""Génération du mini-rapport PDF condensé sur une seule page."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from agent.orchestrator import AgentResult


def _bullet_list(items: list[str], max_items: int = 10) -> str:
    if not items:
        return "— Aucune donnée —"
    lines = [f"• {item}" for item in items[:max_items]]
    return "<br/>".join(lines)


def generate_pdf_report(
    result: AgentResult,
    target_job: str,
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleCI",
        parent=styles["Heading1"],
        fontSize=14,
        textColor=colors.HexColor("#1a365d"),
        spaceAfter=4,
    )
    section_style = ParagraphStyle(
        "SectionCI",
        parent=styles["Heading2"],
        fontSize=10,
        textColor=colors.HexColor("#2c5282"),
        spaceBefore=6,
        spaceAfter=2,
    )
    body_style = ParagraphStyle(
        "BodyCI",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        spaceAfter=2,
    )

    story = []
    story.append(
        Paragraph(
            f"<b>Rapport Stratégique CV — {target_job}</b><br/>"
            f"<font size='7'>{datetime.now():%d/%m/%Y %H:%M}</font>",
            title_style,
        )
    )

    # 1. Analyse du profil
    story.append(Paragraph("1. Analyse du Profil", section_style))
    story.append(
        Paragraph(
            f"<b>Résumé :</b> {result.profile_summary}<br/>"
            f"<b>Compétences actuelles :</b><br/>{_bullet_list(result.candidate_skills, 14)}",
            body_style,
        )
    )

    # 2. Tendances du marché
    story.append(Paragraph("2. Tendances du Marché (DuckDuckGo)", section_style))
    story.append(
        Paragraph(
            f"<b>Compétences tendances :</b><br/>{_bullet_list(result.trends.trend_skills, 12)}",
            body_style,
        )
    )

    # 3. Marché interne SSMS
    ssms_lines = _bullet_list(result.internal.primary_skills, 10)
    for stype, skills in list(result.internal.skills_by_type.items())[:4]:
        ssms_lines += f"<br/><b>{stype}:</b> " + ", ".join(skills[:6])
    story.append(Paragraph("3. Marché Interne (SSMS)", section_style))
    story.append(
        Paragraph(
            f"<b>Métier :</b> {result.internal.target_job}<br/>"
            f"<b>Compétences (fact_job + dim_skill) :</b><br/>{ssms_lines}",
            body_style,
        )
    )

    gaps = result.gaps
    story.append(Paragraph("4. Analyse des Écarts (votre CV vs marché)", section_style))
    story.append(
        Paragraph(
            f"<b>Déjà sur votre CV (SSMS) :</b> {_bullet_list(gaps.matched_ssms, 6)}<br/>"
            f"<b>Déjà sur votre CV (tendances) :</b> {_bullet_list(gaps.matched_trends, 6)}<br/>"
            f"<b>À acquérir — absentes de votre CV :</b> "
            f"{_bullet_list(gaps.missing_from_cv_all, 10)}<br/>"
            f"<b>Peu demandées pour ce poste :</b> {_bullet_list(gaps.surplus_on_cv, 5)}",
            body_style,
        )
    )

    story.append(Paragraph("5. Recommandations CV", section_style))
    story.append(
        Paragraph(
            f"<b>▲ Mettre en avant (en haut du CV) :</b><br/>"
            f"{_bullet_list(result.recommendations_front, 10)}<br/>"
            f"<b>▼ Supprimer ou reléguer en bas :</b><br/>"
            f"{_bullet_list(result.recommendations_bottom, 10)}",
            body_style,
        )
    )

    training_lines = []
    for link in result.training_links[:6]:
        skill = link.get("related_skill", "")
        title = link.get("title", "")
        training_lines.append(f"[{skill}] {title}" if skill else title)
    story.append(Paragraph("6. Formations gratuites (selon vos lacunes)", section_style))
    story.append(
        Paragraph(
            _bullet_list(training_lines, 6) if training_lines else "— Aucune —",
            body_style,
        )
    )

    story.append(Spacer(1, 0.2 * cm))
    story.append(
        Paragraph(
            "<font size='6' color='#718096'>Sources : SSMS (dim_skill, bridge_job_skill, "
            "fact_job_posts) + DuckDuckGo.</font>",
            body_style,
        )
    )

    doc.build(story)
    return output_path
