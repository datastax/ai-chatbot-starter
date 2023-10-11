import json
import os
import logging
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import hmac
import hashlib
from pydantic.utils import deep_update
import pytest


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
def client(init_env):
    from app import app

    yield TestClient(app)


@pytest.fixture(scope="function")
def standard_request():
    return load_test_request("test_request.json")


@pytest.fixture(scope="function")
def mock_assistant():
    """Mocks the AssistantBison object to prevent any real LLM queries being made"""
    with patch("app.assistant") as mock_bison:
        mock_bison.get_response = MagicMock(return_value=("Mocked response", [], []))
        yield mock_bison


def test_get_root_route(client):
    response = client.get("/chat")
    assert response.status_code == 200
    assert response.json()["ok"] == True
    assert response.json()["message"] == "App is running"


def test_standard_case(standard_request, client):
    headers = get_headers(standard_request)
    response = client.post("/chat", json=standard_request, headers=headers)
    assert response.status_code == 201
    assert response.json()["ok"] == True
    assert response.json()["message"] == "Response submitted successfully."


def test_broad_case(standard_request, client):
    # Process each question sequentially in the test questions file
    with open("test_questions.txt", "r") as file:
        lines = [line.strip() for line in file]

    for line in lines:
        # Set the request appropriately
        standard_request["data"]["item"]["conversation_parts"]["conversation_parts"][0][
            "body"
        ] = line
        standard_request["data"]["item"]["source"]["body"] = line

        # Create the digest and headers for the POST request
        headers = get_headers(standard_request)

        # Make the post request
        response = client.post("/chat", json=standard_request, headers=headers)

        # Log the results to a file for manual inspection
        logging.info("###")
        logging.info(line)
        logging.info(response.json())
        logging.info("###")
        logging.info("\n")

        # TODO: Expand - for now, check successful and manually inspect quality
        assert response.status_code == 201
        assert response.json()["ok"] == True
        assert response.json()["message"] == "Response submitted successfully."


def test_invalid_signature(standard_request, client):
    """
    This test is used to validate the signature.The request should be coming from the intercom.
    """
    intercom_secret = os.getenv("INTERCOM_CLIENT_SECRET")

    digest = hmac.new(
        intercom_secret.encode("utf-8"),
        msg=json.dumps(standard_request).encode("utf-8"),
        digestmod=hashlib.sha1,
    ).hexdigest()
    # Passing invalid signature
    headers = {"X-Hub-Signature": f"sha1={digest}_invalid_signature"}
    response = client.post("/chat", json=standard_request, headers=headers)
    assert response.status_code == 401
    assert response.json()["ok"] == False
    assert response.json()["message"] == "Invalid signature."


def test_delivery_attempts(standard_request, client):
    """
    Test passes if the delivery attempts are more than 1
    """
    # Changing delivery attempts. Currently setting it to 3
    standard_request["delivery_attempts"] = 3
    headers = get_headers(standard_request)
    response = client.post("/chat", json=standard_request, headers=headers)
    assert response.status_code == 208
    assert response.json()["ok"] == True
    assert response.json()["message"] == "Already reported."


def test_ping(standard_request, client):
    """
    Test if the request is for ping
    """
    standard_request["data"]["item"]["type"] = "ping"
    headers = get_headers(standard_request)
    response = client.post("/chat", json=standard_request, headers=headers)
    assert response.status_code == 200
    assert response.json()["ok"] == True
    assert response.json()["message"] == "Successful ping."


def test_source(standard_request, client):
    """
    Test if the source is None.
    None passes the test
    """
    standard_request["data"]["item"]["source"] = None
    headers = get_headers(standard_request)
    response = client.post("/chat", json=standard_request, headers=headers)
    assert response.status_code == 400
    assert response.json()["ok"] == False
    assert response.json()["message"] == "Empty source."


def test_datastax_user(standard_request, client):
    """
    Test to check if the user is a DataStax User
    """
    standard_request["data"]["item"]["source"][
        "delivered_as"
    ] = "not_customer_initiated"
    headers = get_headers(standard_request)
    response = client.post("/chat", json=standard_request, headers=headers)
    assert response.status_code == 403
    assert response.json()["ok"] == False
    assert response.json()["message"] == "Unauthorized user."


def test_null_user_question(standard_request, client):
    # Resolving bug where first msg of most conversations was converted to null
    standard_request["data"]["item"]["conversation_parts"] = {
        "conversation_parts": [
            {"body": None, "part_type": "default_assignment"},
            {"body": None, "part_type": "conversation_attribute_updated_by_admin"},
        ]
    }
    standard_request["data"]["item"]["source"][
        "body"
    ] = "<p>How do I authenticate my python client?</p>"
    headers = get_headers(standard_request)
    response = client.post("/chat", json=standard_request, headers=headers)

    assert response.status_code == 201
    assert response.json()["ok"]
    # Assert that the response mentions how to authenticate the python client
    assert "python" in response.json()["response"].lower()


@pytest.mark.parametrize(
    "should_respond,update_dict",
    [
        # Default should work
        (True, {}),
        # If the response is from an admin, should not respond
        (
            False,
            {
                "data": {
                    "item": {
                        "conversation_parts": {
                            "conversation_parts": [
                                {
                                    "author": {
                                        "email": "marcelo.borges@datastax.com",
                                        "id": "60be2e9f4de5986bab3f27d3",
                                        "type": "admin",
                                    },
                                    "body": "This is a test question",
                                }
                            ]
                        }
                    }
                }
            },
        ),
        # If the initiator was an admin, should still respond
        (
            True,
            {
                "data": {
                    "item": {
                        "source": {
                            "author": {"type": "admin"},
                            "delivered_as": "admin_initiated",
                        }
                    }
                }
            },
        ),
        # If the initiator was automated, should still respond
        (
            True,
            {
                "data": {
                    "item": {
                        "source": {
                            "author": {"type": "admin"},
                            "delivered_as": "automated",
                        }
                    }
                }
            },
        ),
        # If the initiator was unknown, should not respond
        (False, {"data": {"item": {"source": {"delivered_as": "unknown_option"}}}}),
        # If user initiated but no conversation parts should still respond
        (True, {"data": {"item": {"conversation_parts": {"conversation_parts": []}}}}),
        # If admin initiated and no conversation parts should not respond
        (
            False,
            {
                "data": {
                    "item": {
                        "conversation_parts": {"conversation_parts": []},
                        "source": {
                            "author": {"type": "admin"},
                            "delivered_as": "admin_initiated",
                        },
                    }
                }
            },
        ),
    ],
)
def test_responds_in_appropriate_settings(
    should_respond,
    update_dict,
    standard_request,
    mock_assistant,
    client,
):
    standard_request = deep_update(standard_request, update_dict)
    headers = get_headers(standard_request)
    response = client.post("/chat", json=standard_request, headers=headers)

    if should_respond:
        assert response.status_code == 201
        assert mock_assistant.get_response.called_once()
    else:
        assert response.status_code != 201
        assert mock_assistant.get_response.never_called()
