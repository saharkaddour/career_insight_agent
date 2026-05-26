"""Formations gratuites alignées sur les compétences manquantes et le poste visé."""

from __future__ import annotations

from urllib.parse import quote_plus

# skill pattern (lowercase substring) -> liens gratuits / audit gratuits
_SKILL_TRAINING: list[tuple[str, list[dict]]] = [
    (
        "python",
        [
            {
                "title": "Python for Everybody (Coursera — audit gratuit)",
                "provider": "Coursera / Michigan",
                "url": "https://www.coursera.org/specializations/python",
                "description": "Fondamentaux Python, structures de données, web scraping.",
            },
            {
                "title": "Intro to Python (Khan Academy)",
                "provider": "Khan Academy",
                "url": "https://www.khanacademy.org/computing/intro-to-python-fundamentals-archived",
                "description": "Bases de la programmation Python.",
            },
        ],
    ),
    (
        "sql",
        [
            {
                "title": "SQL for Data Science (Coursera — audit gratuit)",
                "provider": "Coursera / UC Davis",
                "url": "https://www.coursera.org/learn/sql-for-data-science",
                "description": "Requêtes SQL, jointures, agrégations pour l'analyse.",
            },
            {
                "title": "Intro to SQL (Khan Academy)",
                "provider": "Khan Academy",
                "url": "https://www.khanacademy.org/computing/computer-programming/sql",
                "description": "SQL interactif gratuit.",
            },
        ],
    ),
    (
        "excel",
        [
            {
                "title": "Excel fondamental (Microsoft Learn)",
                "provider": "Microsoft",
                "url": "https://learn.microsoft.com/fr-fr/training/paths/excel-fundamentals/",
                "description": "Formules, tableaux, graphiques.",
            },
        ],
    ),
    (
        "power bi",
        [
            {
                "title": "Parcours Power BI (Microsoft Learn)",
                "provider": "Microsoft",
                "url": "https://learn.microsoft.com/fr-fr/training/paths/power-bi-data-analyst/",
                "description": "Modélisation, DAX, tableaux de bord.",
            },
        ],
    ),
    (
        "tableau",
        [
            {
                "title": "Tableau Public — tutoriels gratuits",
                "provider": "Tableau",
                "url": "https://public.tableau.com/en-us/s/resources",
                "description": "Visualisation de données avec Tableau Public.",
            },
        ],
    ),
    (
        "machine learning",
        [
            {
                "title": "Machine Learning (Coursera — audit gratuit)",
                "provider": "Coursera / Stanford",
                "url": "https://www.coursera.org/learn/machine-learning",
                "description": "Cours fondateur d'Andrew Ng.",
            },
        ],
    ),
    (
        "azure",
        [
            {
                "title": "Azure Fundamentals (Microsoft Learn)",
                "provider": "Microsoft",
                "url": "https://learn.microsoft.com/fr-fr/training/paths/az-900-describe-cloud-concepts/",
                "description": "Cloud Azure, services et tarification.",
            },
        ],
    ),
    (
        "aws",
        [
            {
                "title": "AWS Cloud Practitioner (AWS Skill Builder)",
                "provider": "Amazon",
                "url": "https://explore.skillbuilder.aws/learn",
                "description": "Fondamentaux AWS gratuits.",
            },
        ],
    ),
    (
        "agile",
        [
            {
                "title": "Agile avec Atlassian (Coursera — audit gratuit)",
                "provider": "Coursera",
                "url": "https://www.coursera.org/specializations/agile-atlassian",
                "description": "Scrum, Kanban, gestion de projet agile.",
            },
        ],
    ),
    (
        "scrum",
        [
            {
                "title": "Scrum Foundation (OpenClassrooms)",
                "provider": "OpenClassrooms",
                "url": "https://openclassrooms.com/fr/courses/4296701-decouvrez-les-methodes-agiles",
                "description": "Introduction aux rituels Scrum.",
            },
        ],
    ),
    (
        "recruitment",
        [
            {
                "title": "Recrutement et sélection (LinkedIn Learning — essai)",
                "provider": "LinkedIn",
                "url": "https://www.linkedin.com/learning/topics/recruiting",
                "description": "Sourcing, entretiens, marque employeur.",
            },
        ],
    ),
    (
        "payroll",
        [
            {
                "title": "Gestion de la paie — bases (OpenClassrooms)",
                "provider": "OpenClassrooms",
                "url": "https://openclassrooms.com/fr/courses",
                "description": "Rechercher « paie » sur le catalogue gratuit.",
            },
        ],
    ),
    (
        "hr",
        [
            {
                "title": "Human Resources (Coursera — audit gratuit)",
                "provider": "Coursera / Minnesota",
                "url": "https://www.coursera.org/specializations/human-resource-management",
                "description": "RH stratégique, droit du travail, performance.",
            },
        ],
    ),
    (
        "communication",
        [
            {
                "title": "Communication professionnelle (Coursera)",
                "provider": "Coursera",
                "url": "https://www.coursera.org/courses?query=professional%20communication",
                "description": "Présentation, écriture, communication interpersonnelle.",
            },
        ],
    ),
    (
        "photoshop",
        [
            {
                "title": "Photoshop — tutoriels Adobe",
                "provider": "Adobe",
                "url": "https://helpx.adobe.com/photoshop/tutorials.html",
                "description": "Retouche et composition (ressources gratuites).",
            },
        ],
    ),
    (
        "javascript",
        [
            {
                "title": "JavaScript algorithms (freeCodeCamp)",
                "provider": "freeCodeCamp",
                "url": "https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures/",
                "description": "JS moderne, structures de données.",
            },
        ],
    ),
    (
        "react",
        [
            {
                "title": "React — documentation officielle",
                "provider": "React",
                "url": "https://react.dev/learn",
                "description": "Tutoriel interactif gratuit.",
            },
        ],
    ),
    (
        "docker",
        [
            {
                "title": "Docker pour les débutants (KodeKloud — gratuit)",
                "provider": "KodeKloud",
                "url": "https://kodekloud.com/free-courses/docker-for-the-absolute-beginner/",
                "description": "Conteneurs et images Docker.",
            },
        ],
    ),
    (
        "kubernetes",
        [
            {
                "title": "Kubernetes basics (Linux Foundation)",
                "provider": "CNCF",
                "url": "https://kubernetes.io/docs/tutorials/kubernetes-basics/",
                "description": "Concepts et premiers déploiements.",
            },
        ],
    ),
]

_JOB_TRAINING: list[tuple[str, list[dict]]] = [
    (
        "data",
        [
            {
                "title": "Google Data Analytics Certificate (Coursera — audit)",
                "provider": "Google / Coursera",
                "url": "https://www.coursera.org/professional-certificates/google-data-analytics",
                "description": "Parcours data analyst de Google.",
            },
        ],
    ),
    (
        "analyst",
        [
            {
                "title": "Data Analyst nanodegree resources (Udacity free)",
                "provider": "Udacity",
                "url": "https://www.udacity.com/course/intro-to-data-analysis--ud170",
                "description": "Introduction à l'analyse de données.",
            },
        ],
    ),
    (
        "hr",
        [
            {
                "title": "HR Management (Harvard Online — gratuit)",
                "provider": "Harvard",
                "url": "https://online.harvard.edu/course/leading-people/",
                "description": "Leadership et gestion des équipes.",
            },
        ],
    ),
    (
        "teacher",
        [
            {
                "title": "Learning to Teach Online (Coursera — audit)",
                "provider": "Coursera / UNSW",
                "url": "https://www.coursera.org/learn/teach-online",
                "description": "Pédagogie et classes virtuelles.",
            },
        ],
    ),
    (
        "design",
        [
            {
                "title": "Graphic Design basics (Canva Design School)",
                "provider": "Canva",
                "url": "https://www.canva.com/designschool/",
                "description": "Principes visuels et outils de design.",
            },
        ],
    ),
]

_GENERIC_FALLBACK = [
    {
        "title": "Coursera — cours auditables gratuits",
        "provider": "Coursera",
        "url": "https://www.coursera.org/courses?query=free",
        "description": "Recherchez le nom de la compétence manquante.",
    },
    {
        "title": "Microsoft Learn",
        "provider": "Microsoft",
        "url": "https://learn.microsoft.com/fr-fr/training/",
        "description": "Parcours techniques et bureautique gratuits.",
    },
    {
        "title": "Harvard Online — cours gratuits",
        "provider": "Harvard",
        "url": "https://online.harvard.edu/free-courses",
        "description": "Management, santé, informatique.",
    },
]


def _search_url(provider: str, skill: str) -> dict:
    q = quote_plus(f"{skill} free course")
    urls = {
        "coursera": f"https://www.coursera.org/search?query={q}",
        "linkedin": f"https://www.linkedin.com/learning/search?keywords={q}",
        "edx": f"https://www.edx.org/search?q={q}",
    }
    return {
        "title": f"Cours gratuits : {skill}",
        "provider": provider,
        "url": urls.get(provider, urls["coursera"]),
        "description": f"Résultats de recherche pour acquérir « {skill} ».",
        "related_skill": skill,
    }


def get_personalized_training_links(
    missing_skills: list[str],
    target_job: str = "",
    max_links: int = 8,
) -> list[dict]:
    """
    Retourne des liens de formation gratuits alignés sur les compétences
    manquantes du CV et le poste visé.
    """
    links: list[dict] = []
    seen_urls: set[str] = set()

    def _add(entry: dict, skill: str = "") -> None:
        url = entry.get("url", "")
        if not url or url in seen_urls:
            return
        seen_urls.add(url)
        item = dict(entry)
        if skill:
            item["related_skill"] = skill
        links.append(item)

    for skill in missing_skills:
        skill_low = skill.lower()
        for pattern, entries in _SKILL_TRAINING:
            if pattern in skill_low or skill_low in pattern:
                for entry in entries:
                    _add(entry, skill)
                    if len(links) >= max_links:
                        return links

    job_low = target_job.lower()
    for pattern, entries in _JOB_TRAINING:
        if pattern in job_low:
            for entry in entries:
                _add(entry, target_job)
                if len(links) >= max_links:
                    return links

    for skill in missing_skills[:5]:
        if len(links) >= max_links:
            break
        _add(_search_url("coursera", skill), skill)

    for entry in _GENERIC_FALLBACK:
        if len(links) >= max_links:
            break
        _add(entry)

    return links[:max_links]


# Liens génériques (page d'accueil avant analyse)
FREE_TRAINING_LINKS = _GENERIC_FALLBACK
