from dotenv import load_dotenv
import pytest

from integrations.google import init_gcp
from pipeline.config import load_config


@pytest.fixture(scope="module", autouse=True)
def init_config():
    load_dotenv(".env")
    config = load_config("config.yml")
    yield config


@pytest.fixture(scope="module")
def gcp_conn(init_config):
    init_gcp(init_config)
