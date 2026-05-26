"""Extraction des données SSMS """

from __future__ import annotations

import pyodbc
import pandas as pd

from config.settings import (
    SQL_DATABASE,
    SQL_DRIVER,
    SQL_SERVER,
    SQL_TRUSTED_CONNECTION,
    SQL_TRUST_SERVER_CERTIFICATE,
    TABLE_BRIDGE_JOB_SKILLS,
    TABLE_DIM_SKILL,
    TABLE_FACT_JOB_POSTS,
)


class SqlServerClient:

    def __init__(
        self,
        server: str = SQL_SERVER,
        database: str = SQL_DATABASE,
        driver: str = SQL_DRIVER,
    ) -> None:
        self.server = server
        self.database = database
        self.driver = driver
        self._connection_string = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"Trusted_Connection={'yes' if SQL_TRUSTED_CONNECTION else 'no'};"
            f"TrustServerCertificate={'yes' if SQL_TRUST_SERVER_CERTIFICATE else 'no'};"
        )

    def connect(self) -> pyodbc.Connection:
        return pyodbc.connect(self._connection_string)

    def fetch_skills_referential(self) -> pd.DataFrame:
        """dbo.dim_skill"""
        query = f"""
            SELECT skill_key, skill_id, skill_name, skill_type
            FROM {TABLE_DIM_SKILL}
            ORDER BY skill_name
        """
        with self.connect() as conn:
            return pd.read_sql_query(query, conn)

    def fetch_job_posts(self, limit: int | None = None) -> pd.DataFrame:
        """dbo.fact_job_posts"""
        top = f"TOP ({int(limit)})" if limit else ""
        query = f"SELECT {top} * FROM {TABLE_FACT_JOB_POSTS}"
        with self.connect() as conn:
            return pd.read_sql_query(query, conn)

    def fetch_bridge_job_skills(self, limit: int | None = None) -> pd.DataFrame:
        """dbo.bridge_job_skill """
        top = f"TOP ({int(limit)})" if limit else ""
        query = f"SELECT {top} job_key, skill_key FROM {TABLE_BRIDGE_JOB_SKILLS}"
        with self.connect() as conn:
            return pd.read_sql_query(query, conn)

    def fetch_skills_for_job_title(self, job_title_short: str, top_n: int = 30) -> list[str]:
        df = self.fetch_job_skills_detailed(job_title_short, top_n=top_n)
        return df["skill_name"].tolist() if not df.empty else []

    def fetch_job_skills_detailed(
        self,
        job_title_short: str,
        top_n: int = 30,
    ) -> pd.DataFrame:
        """
        Jointure fact_job_posts + bridge_job_skill + dim_skill.
        Retourne job_title, skill_name, skill_type et fréquence.
        """
        query = f"""
            SELECT TOP ({int(top_n)})
                j.job_title_short,
                j.job_title,
                s.skill_name,
                s.skill_type,
                COUNT(*) AS frequency
            FROM {TABLE_FACT_JOB_POSTS} j
            INNER JOIN {TABLE_BRIDGE_JOB_SKILLS} b ON j.job_key = b.job_key
            INNER JOIN {TABLE_DIM_SKILL} s ON b.skill_key = s.skill_key
            WHERE j.job_title_short = ?
            GROUP BY j.job_title_short, j.job_title, s.skill_name, s.skill_type
            ORDER BY frequency DESC, s.skill_name
        """
        with self.connect() as conn:
            return pd.read_sql_query(query, conn, params=[job_title_short])

    def fetch_job_titles_with_skills(self, top_jobs: int = 20, skills_per_job: int = 10) -> pd.DataFrame:
        """Top métiers (fact_job_posts) avec leurs compétences (dim_skill via bridge)."""
        query = f"""
            WITH ranked_jobs AS (
                SELECT TOP ({int(top_jobs)}) job_title_short
                FROM {TABLE_FACT_JOB_POSTS}
                GROUP BY job_title_short
                ORDER BY COUNT(*) DESC
            ),
            ranked_skills AS (
                SELECT
                    j.job_title_short,
                    j.job_title,
                    s.skill_name,
                    s.skill_type,
                    COUNT(*) AS frequency,
                    ROW_NUMBER() OVER (
                        PARTITION BY j.job_title_short
                        ORDER BY COUNT(*) DESC
                    ) AS rn
                FROM {TABLE_FACT_JOB_POSTS} j
                INNER JOIN {TABLE_BRIDGE_JOB_SKILLS} b ON j.job_key = b.job_key
                INNER JOIN {TABLE_DIM_SKILL} s ON b.skill_key = s.skill_key
                INNER JOIN ranked_jobs rj ON j.job_title_short = rj.job_title_short
                GROUP BY j.job_title_short, j.job_title, s.skill_name, s.skill_type
            )
            SELECT job_title_short, job_title, skill_name, skill_type, frequency
            FROM ranked_skills
            WHERE rn <= {int(skills_per_job)}
            ORDER BY job_title_short, frequency DESC
        """
        with self.connect() as conn:
            return pd.read_sql_query(query, conn)

    def fetch_minimum_skills_for_job(self, job_title_short: str, min_frequency_pct: float = 0.15) -> list[str]:
        """
        Compétences minimales requises : présentes dans au moins min_frequency_pct des offres du poste.
        """
        query = f"""
            WITH job_skills AS (
                SELECT s.skill_name, COUNT(DISTINCT j.job_key) AS job_count
                FROM {TABLE_FACT_JOB_POSTS} j
                INNER JOIN {TABLE_BRIDGE_JOB_SKILLS} b ON j.job_key = b.job_key
                INNER JOIN {TABLE_DIM_SKILL} s ON b.skill_key = s.skill_key
                WHERE j.job_title_short = ?
                GROUP BY s.skill_name
            ),
            total AS (
                SELECT COUNT(DISTINCT job_key) AS total_jobs
                FROM {TABLE_FACT_JOB_POSTS}
                WHERE job_title_short = ?
            )
            SELECT js.skill_name,
                   CAST(js.job_count AS FLOAT) / NULLIF(t.total_jobs, 0) AS ratio
            FROM job_skills js
            CROSS JOIN total t
            WHERE CAST(js.job_count AS FLOAT) / NULLIF(t.total_jobs, 0) >= ?
            ORDER BY ratio DESC
        """
        with self.connect() as conn:
            df = pd.read_sql_query(
                query, conn, params=[job_title_short, job_title_short, min_frequency_pct]
            )
        return df["skill_name"].tolist()

    def list_job_titles(self, top_n: int = 20) -> list[str]:
        query = f"""
            SELECT TOP ({int(top_n)}) job_title_short, COUNT(*) AS cnt
            FROM {TABLE_FACT_JOB_POSTS}
            GROUP BY job_title_short
            ORDER BY cnt DESC
        """
        with self.connect() as conn:
            df = pd.read_sql_query(query, conn)
        return df["job_title_short"].tolist()
