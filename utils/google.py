import json
import os

from google.cloud import aiplatform
from google.oauth2 import service_account

GECKO_EMB_DIM = 768


def init_gcp():
    """Initialize GCP Auth based on environment variables"""
    # Google Auth + Vertex instance
    project_id = os.environ.get("GOOGLE_PROJECT_ID")
    google_credentials = os.environ.get("GOOGLE_CREDENTIALS")

    # Google Auth
    google_credentials_json = json.loads(google_credentials)
    google_credentials_json["private_key"] = google_credentials_json[
        "private_key"
    ].replace("\\n", "\n")
    credentials = service_account.Credentials.from_service_account_info(
        google_credentials_json
    )
    aiplatform.init(project=project_id, credentials=credentials)
