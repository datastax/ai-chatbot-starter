import json
import os
import logging
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import hashlib
import hmac
from llama_index.response.schema import StreamingResponse
import pytest
import requests


def get_headers(body):
    """Helper to get necessary request headers for successful POST

    NOTE: Keys in `body` must be specified (recursively) in alphabetical order
    """
    intercom_secret = os.getenv("INTERCOM_CLIENT_SECRET")

    digest = hmac.new(
        intercom_secret.encode("utf-8"),
        msg=json.dumps(body).encode("utf-8"),
        digestmod=hashlib.sha1,
    ).hexdigest()
    return {"X-Hub-Signature": f"sha1={digest}"}


def load_test_request(filename):
    with open(filename, "r") as f:
        request_data = json.load(f)
    return request_data


@pytest.fixture(scope="module")
def client(init_config):
    # Patch necessary things
    with patch("pipeline.config.load_config") as mock:
        mock.return_value = init_config
        from app import app

        yield TestClient(app)


@pytest.fixture(scope="function")
def standard_request():
    return load_test_request(os.path.join("tests", "test_request.json"))


@pytest.fixture(scope="function")
def mock_assistant():
    """Mocks the AssistantBison object to prevent any real LLM queries being made"""
    with patch("app.assistant") as mock_bison:
        response_gen = (s for s in ["Mocked", "response"])
        mock_bison.get_response = MagicMock(
            return_value=(StreamingResponse(response_gen), [], [])
        )
        yield mock_bison


def get_text_response(client, data, headers, assert_created=True):
    # r = httpx.post("http://127.0.0.1:5010/chat", json=user_data, headers=headers)
    response = client.post("/chat", json=data, headers=headers)

    if assert_created:
        assert (
            response.status_code == requests.codes.created
        ), f"Request failed with status code {response.status_code}: {response.text}"

    # Check if the request was successful
    return response.content.decode()


def test_get_root_route(client):
    response = client.get("/chat")
    assert response.status_code == 200
    assert response.json()["ok"] == True
    assert response.json()["message"] == "App is running"


def test_standard_case(standard_request, client):
    headers = get_headers(standard_request)
    text = get_text_response(client, standard_request, headers)
    assert len(text) > 0


def test_broad_case(standard_request, client):
    # Process each question sequentially in the test questions file
    with open(os.path.join("tests", "test_questions.txt"), "r") as file:
        lines = [line.strip() for line in file]

    for line in lines:
        # Set the request appropriately
        standard_request = {"question": line}

        # Create the digest and headers for the POST request
        headers = get_headers(standard_request)

        # Make the post request
        text_response = get_text_response(client, standard_request, headers)

        # Log the results to a file for manual inspection
        logging.info("###")
        logging.info(line)
        logging.info(text_response)
        logging.info("###")
        logging.info("\n")
