import json

from google.cloud import aiplatform
from google.oauth2 import service_account

GECKO_EMB_DIM = 768

from pipeline.config import Config


def init_gcp(config: Config) -> None:
    """Initialize GCP Auth based on environment variables"""
    # Google Auth
    google_credentials_json = json.loads(config.google_credentials)
    google_credentials_json["private_key"] = google_credentials_json[
        "private_key"
    ].replace("\\n", "\n")
    credentials = service_account.Credentials.from_service_account_info(
        google_credentials_json
    )
    aiplatform.init(project=config.google_project_id, credentials=credentials)
