"""Rapport HTML du mini-rapport (affichage web)."""

from __future__ import annotations

from datetime import datetime
from html import escape

from agent.orchestrator import AgentResult


def _tags(items: list[str], max_items: int = 14) -> str:
    if not items:
        return '<span class="muted">— Aucune donnée —</span>'
    return "".join(
        f'<span class="chip">{escape(str(item))}</span>' for item in items[:max_items]
    )


def _list_items(items: list[str], max_items: int = 10) -> str:
    if not items:
        return "<li class='muted'>—</li>"
    return "".join(f"<li>{escape(str(i))}</li>" for i in items[:max_items])


def _training_links_html(links: list[dict]) -> str:
    if not links:
        return "<p class='muted'>Aucune formation suggérée.</p>"
    rows = []
    for link in links:
        skill = link.get("related_skill", "")
        skill_badge = (
            f"<span class='chip chip-skill'>{escape(skill)}</span> " if skill else ""
        )
        rows.append(
            f"<li>{skill_badge}"
            f"<a href='{escape(link['url'])}' target='_blank' rel='noopener noreferrer'>"
            f"<strong>{escape(link['title'])}</strong></a> "
            f"<span class='provider'>({escape(link.get('provider', ''))})</span>"
            f"<p class='small'>{escape(link.get('description', ''))}</p></li>"
        )
    return "<ul class='links-list'>" + "".join(rows) + "</ul>"


def render_html_report(result: AgentResult, target_job: str) -> str:
    gaps = result.gaps
    internal_types_html = ""
    for stype, skills in result.internal.skills_by_type.items():
        internal_types_html += (
            f"<p><strong>{escape(stype)}</strong> : {_tags(skills, 8)}</p>"
        )

    return f"""
    <article class="report-card">
      <header class="report-header">
        <h2>Mini-rapport — {escape(target_job)}</h2>
        <p class="report-date">{datetime.now():%d/%m/%Y %H:%M}</p>
      </header>

      <section>
        <h3>1. Analyse du CV</h3>
        <p><strong>Résumé :</strong> {escape(result.profile_summary)}</p>
        <p><strong>Compétences détectées sur votre CV :</strong></p>
        <div class="chips">{_tags(result.candidate_skills, 16)}</div>
      </section>

      <section>
        <h3>2. Tendances marché (DuckDuckGo)</h3>
        <p class="muted small">Requête : {escape(result.trends.query)}</p>
        <p class="muted small">Source : {escape(getattr(result.trends, 'source_note', 'DuckDuckGo'))}</p>
        {_tags(result.trends.trend_skills, 14)}
      </section>

      <section>
        <h3>3. Marché interne (SSMS)</h3>
        <p><strong>Métier cible :</strong> {escape(result.internal.target_job)}</p>
        <p><strong>Compétences demandées (offres d'emploi) :</strong></p>
        {_tags(result.internal.primary_skills, 12)}
        {internal_types_html}
      </section>

      <section>
        <h3>4. Analyse des écarts</h3>
        <p class="muted small">Comparaison : <strong>votre CV</strong> vs exigences SSMS et tendances web.</p>
        <div class="gap-grid">
          <div>
            <h4>Déjà sur votre CV (aligné SSMS)</h4>
            <ul>{_list_items(gaps.matched_ssms)}</ul>
          </div>
          <div>
            <h4>Déjà sur votre CV (aligné tendances)</h4>
            <ul>{_list_items(gaps.matched_trends)}</ul>
          </div>
        </div>
        <div class="gap-missing highlight-box">
          <h4>À acquérir — absentes de votre CV</h4>
          <p class="small">Exigées par le marché mais non présentes sur votre CV :</p>
          {_tags(gaps.missing_from_cv_all, 20)}
          <details class="gap-details">
            <summary>Détail par source</summary>
            <p><strong>Vs SSMS :</strong> {_tags(gaps.missing_from_cv_ssms, 12)}</p>
            <p><strong>Vs tendances web :</strong> {_tags(gaps.missing_from_cv_trends, 12)}</p>
          </details>
        </div>
        <div class="gap-surplus">
          <h4>Peu demandées pour ce poste (présentes sur votre CV)</h4>
          <ul>{_list_items(gaps.surplus_on_cv, 8)}</ul>
        </div>
      </section>

      <section>
        <h3>5. Recommandations CV</h3>
        <p><strong>▲ Mettre en avant (haut du CV)</strong></p>
        <ul>{_list_items(result.recommendations_front)}</ul>
        <p><strong>▼ Reléguer en bas ou reformuler</strong></p>
        <ul>{_list_items(result.recommendations_bottom)}</ul>
      </section>

      <section>
        <h3>6. Formations gratuites recommandées</h3>
        <p class="muted small">Alignées sur vos lacunes et le poste « {escape(target_job)} ».</p>
        {_training_links_html(result.training_links)}
      </section>

      <footer class="report-footer">
        Sources : SSMS (fact_job_posts, bridge_job_skill, dim_skill) + DuckDuckGo
      </footer>
    </article>
    """
