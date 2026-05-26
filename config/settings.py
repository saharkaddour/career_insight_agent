"""Configuration centralisée de l'Agent"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# SQL Server (LocalDB / SSMS)
SQL_SERVER = r"(localdb)\MSSQLLocalDB"
SQL_DATABASE = "JobsStaging"
SQL_DRIVER = "ODBC Driver 18 for SQL Server"
SQL_TRUSTED_CONNECTION = True
SQL_TRUST_SERVER_CERTIFICATE = True

TABLE_DIM_SKILL = "dbo.dim_skill"
TABLE_BRIDGE_JOB_SKILLS = "dbo.bridge_job_skill"
TABLE_FACT_JOB_POSTS = "dbo.fact_job_posts"
# Dataset CV local
RESUME_CSV_PATH = PROJECT_ROOT / "data" / "Resume.csv"
# Ml model
ML_MODEL_PATH = PROJECT_ROOT / "models" / "skill_extractor.joblib"
ML_TEST_SIZE = 0.2
ML_RANDOM_STATE = 42
ML_MAX_CV_SAMPLES = 5000
# Web search
DDG_MAX_RESULTS = 8
DDG_REGION = "fr-fr"
# Pdf report
REPORTS_DIR = PROJECT_ROOT / "reports"
DEFAULT_REPORT_NAME = "rapport_competences.pdf"
# Web UI
WEB_HOST = "127.0.0.1"
WEB_PORT = 5000
