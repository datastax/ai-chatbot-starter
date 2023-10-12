import requests
import json
import os
import hmac
import hashlib


from dotenv import load_dotenv

load_dotenv(".env")


###
# Let's define the question right here
###
CHATBOT_QUESTION = "How do i get started?"
intercom_secret = os.getenv("INTERCOM_CLIENT_SECRET")


# Build the appropriate headers
def get_headers(body):
    """Helper to get necessary request headers for successful POST"""
    digest = hmac.new(
        intercom_secret.encode("utf-8"),
        msg=json.dumps(body).encode("utf-8"),
        digestmod=hashlib.sha1,
    ).hexdigest()

    return {"X-Hub-Signature": f"sha1={digest}"}


# Load the test request
user_data_file = "tests/test_request.json"
user_data = ""
with open(user_data_file, "r") as f:
    user_data = json.load(f)


def call_assistant(chatbot_question=CHATBOT_QUESTION):
    # Set the request appropriately
    user_data["data"]["item"]["conversation_parts"]["conversation_parts"][0][
        "body"
    ] = chatbot_question
    user_data["data"]["item"]["source"]["body"] = chatbot_question

    headers = get_headers(user_data)

    r = requests.post("http://127.0.0.1:5010/chat", json=user_data, headers=headers)

    # Check if the request was successful
    if r.status_code == requests.codes.created:
        return r.json()
    else:
        return f"Request failed with status code {r.status_code}: {r.text}"


example_result = call_assistant()

print(example_result["context"])
print("\n====\n")
print(example_result["response"])
