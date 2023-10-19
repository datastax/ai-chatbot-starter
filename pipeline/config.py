import os
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, model_validator
import yaml

CONFIG_PATH = "config.yml"
# TODO: Probably a way to specify to load from os.env in validator/type instead
SENSITIVE_FIELDS = [
    "OPENAI_API_KEY",
    "GOOGLE_CREDENTIALS",
    "GOOGLE_PROJECT_ID",
    "BOT_INTERCOM_ID",
    "INTERCOM_TOKEN",
    "INTERCOM_CLIENT_SECRET",
    "BUGSNAG_API_KEY",
    "SLACK_WEBHOOK_URL",
    "ASTRA_DB_KEYSPACE",
    "ASTRA_DB_DATABASE_ID",
    "ASTRA_DB_TOKEN",
    "ASTRA_DB_TABLE_NAME",
]


class LLMProvider(str, Enum):
    OpenAI = "openai"
    Google = "google"


class Config(BaseModel):
    """The allowed configuration options for this application"""
    # Base config options
    llm_provider: LLMProvider = LLMProvider.OpenAI
    company: str
    company_url: str = ""
    custom_rules: Optional[List[str]] = None
    doc_pages: List[str]
    mode: str = "Development"

    # Determine which integrations will run
    response_decider_cls: List[str]  # TODO: Get a better name here
    user_context_creator_cls: List[str]
    response_actor_cls: List[str]

    # Integration specific fields for LLM Providers and Integrations
    # TODO: Move these down one level further into sub-Models that can be defined
    #       in the corresponding integrations file
    openai_api_key: Optional[str] = None

    google_credentials: Optional[str] = None
    google_project_id: Optional[str] = None

    bot_intercom_id: Optional[str] = None
    intercom_token: Optional[str] = None
    intercom_client_secret: Optional[str] = None
    intercom_include_response: bool = True
    intercom_include_context: bool = True

    bugsnag_api_key: Optional[str] = None

    slack_webhook_url: Optional[str] = None

    # Credentials for Astra DB
    astra_db_keyspace: str
    astra_db_database_id: str
    astra_db_token: str
    astra_db_table_name: str = "data"

    @model_validator(mode="after")
    def check_llm_creds(self):
        if self.llm_provider == LLMProvider.OpenAI:
            assert self.openai_api_key is not None, "openai_api_key must be included"
        elif self.llm_provider == LLMProvider.Google:
            assert self.google_credentials is not None, "google_credentials must be included"
            assert self.google_project_id is not None, "google_project_id must be included"
        else:
            raise ValueError(f"Unrecognized llm_provider {self.llm_provider}")

    @model_validator(mode="after")
    def check_integration_creds(self):
        """Validates that any integrations being used have credentials present"""
        # Avoiding circular import
        from .base_integration import integrations_registry

        all_integrations = self.response_decider_cls + self.user_context_creator_cls + self.response_decider_cls
        for integration_cls_name in all_integrations:
            required_fields = integrations_registry[integration_cls_name].required_fields
            for field in required_fields:
                assert getattr(self, field) is not None, f"{field} must be specified for integration {integration_cls_name}"


def load_config() -> Config:
    """Return the Config for the app - assumes all env vars have been loaded"""
    with open(CONFIG_PATH) as config_file:
        yaml_config = yaml.safe_load(config_file)

    for field in SENSITIVE_FIELDS:
        if field in os.environ:
            # Lowering case to match config expected behavior
            yaml_config[field.lower()] = os.environ[field]

    return Config(**yaml_config)
