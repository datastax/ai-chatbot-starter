from dotenv import load_dotenv
import pytest

from integrations.astra import init_astra_get_table_name
from integrations.google import init_gcp


@pytest.fixture(scope="module", autouse=True)
def init_env():
    load_dotenv("../.env")


@pytest.fixture(scope="module")
def gcp_conn():
    init_gcp()


@pytest.fixture(scope="module")
def astra_table_name():
    yield init_astra_get_table_name()
