"""
Utils for the Scorecard SDK.

Testset and results use the Scorecard SDK.
"""

import os
import requests

from dotenv import load_dotenv

load_dotenv(".env")

SCORECARD_API_KEY = os.environ["SCORECARD_API_KEY"]

# Endpoint definitions
BASE_URL = "https://api.getscorecard.ai/"
POST_CREATE_RUN_URL = BASE_URL + "create-run"
GET_TESTSET_BASE_URL = BASE_URL + "testset"
POST_CREATE_TESTRECORD_URL = BASE_URL + "create-testrecord"
PATCH_UPDATE_RUN_BASE_URL = BASE_URL + "update-run"

REQUEST_HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "X-API-Key": SCORECARD_API_KEY,
}


def create_run(
    input_testset_id: int, scoring_config_id: int, model_params: dict() = {}
):
    print("Creating new run...")
    create_run_url = POST_CREATE_RUN_URL
    response = requests.post(
        create_run_url,
        json={
            "testset_id": input_testset_id,
            "scoring_config_id": scoring_config_id,
            "status": "running_execution",
            "model_params": model_params,
        },
        headers=REQUEST_HEADERS,
        timeout=30,
    )
    if response.status_code != 200:
        print(f"ERROR: {response.status_code} {response.text}")
    print(response.text)
    return response.json()["run_id"]


def get_testset(testset_id: int):
    print("Retrieving testset...")
    get_testset_url = GET_TESTSET_BASE_URL + "/" + str(testset_id)
    testset_response = requests.get(
        get_testset_url, headers=REQUEST_HEADERS, timeout=30
    )
    if testset_response.status_code != 200:
        print(f"ERROR: {testset_response.status_code} {testset_response.text}")
        return []
    return testset_response.json()["data"]


def update_run_status(run_id: int, status: str = "awaiting_scoring"):
    update_run_url = PATCH_UPDATE_RUN_BASE_URL + "/" + str(run_id) + "?status=" + status
    response = requests.patch(update_run_url, headers=REQUEST_HEADERS, timeout=30)
    if response.status_code != 200:
        print(f"ERROR: {response.status_code} {response.text}")
    return response.json()


def log_record(
    run_id: int,
    testcase_id: int,
    model_response: str,
    prompt: str = "",
    model_params: dict() = {},
):
    testrecord = {
        "run_id": run_id,
        "testcase_id": testcase_id,
        "model_response": model_response,
        "prompt": prompt,
        "model_params": model_params,
    }

    print(f"Writing new testrecord for run_id {run_id}...")
    print("Testrecord:")
    for key, value in testrecord.items():
        print(f"\t{key}: {str(value)[:100]}")

    response = requests.post(
        POST_CREATE_TESTRECORD_URL,
        json=testrecord,
        headers=REQUEST_HEADERS,
        timeout=30,
    )
    if response.status_code != 200:
        print(f"ERROR: {response.status_code} {response.text}")
