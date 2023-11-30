"""
Script that runs an automated test suite for Anthropic Claude.

Testset and results use the Scorecard SDK.
"""

import os
import httpx
import scorecard

from dotenv import load_dotenv
from fastapi.testclient import TestClient

from app import app

load_dotenv(".env")


SCORECARD_API_KEY = os.environ["SCORECARD_API_KEY"]


def query_ai_chatbot_starter(user_query):
    # Set the request appropriately
    headers = {}
    request_body = {"question": user_query}

    response = TestClient(app).post("/chat", json=request_body, headers=headers)

    # Check if the request was successful
    if response.status_code == httpx.codes.created:
        return response.content.decode()
    else:
        return f"Request failed with status code {response.status_code}: {response.text}"


def run_all_tests(input_testset_id: int, scoring_config_id: int):
    run_id = scorecard.create_run(input_testset_id, scoring_config_id)
    testcases = scorecard.get_testset(input_testset_id)

    for testcase in testcases:
        print(f"Running testcase {testcase['id']}...")
        print(f"User query: {testcase['user_query']}")

        # Get the model's response using the helper function
        model_response = query_ai_chatbot_starter(testcase["user_query"])

        scorecard.log_record(
            run_id, testcase["id"], model_response, # TODO: Add PROMPT_TEMPLATE
        )

    scorecard.update_run_status(run_id)


if __name__ == "__main__":
    INPUT_TESTSET_ID = int(os.environ["INPUT_TESTSET_ID"])
    SCORING_CONFIG_ID = int(os.environ["SCORING_CONFIG_ID"])

    run_all_tests(INPUT_TESTSET_ID, SCORING_CONFIG_ID)
