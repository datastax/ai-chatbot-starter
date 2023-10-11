import json
import os
import bugsnag
import logging
import requests

from asgiref.sync import async_to_sync
from bugsnag.handlers import BugsnagHandler
from chatbot_api.nosql_assistant import AssistantBison
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request
from urllib.parse import urlparse
from utils.astra import get_persona, init_astra_session_keyspace_tablename
from utils.google import init_gcp
from utils.intercom import (
    ResponseDecision,
    add_comment_to_intercom_conversation,
    send_intercom_message,
)
from utils.orchestrator import get_databases

load_dotenv(".env")

# Grab the env variables loaded above
mode = os.getenv("MODE", "Development")
include_response = os.getenv("INCLUDE_RESPONSE", True)
include_context = os.getenv("INCLUDE_CONTEXT", True)
bugsnag_api_key = os.getenv("BUGSNAG_API_KEY")

# Setup astra and GCP
session, keyspace, table_name = init_astra_session_keyspace_tablename()
init_gcp()

# Configure bugsnag
bugsnag.configure(
    api_key=bugsnag_api_key,
    project_root="/",
    release_stage=mode
)

# Set up the logging infrastructure
logger = logging.getLogger("test.logger")
handler = BugsnagHandler()
# send only ERROR-level logs and above
handler.setLevel(logging.ERROR)
logger.addHandler(handler)

# Define the FastAPI application
app = FastAPI(
    title="NoSQL Assistant",
    description="An LLM-powered Chatbot for Documentation",
    summary="AI Chatbot Starter",
    version="0.0.1",
    terms_of_service="http://example.com/terms/",
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

# Set appropriate origin requests
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
]

# Add the middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define our assistant with the appropriate parameters, global to the service
assistant = AssistantBison(
    session,
    keyspace=keyspace,
    table_name=table_name,
    max_tokens_response=1024,
    k=4,
    company=os.getenv("COMPANY"),
    custom_rules=os.getenv("CUSTOM_RULES").split("\n"),
)


@app.get("/chat")
def index():
    return {"ok": True, "message": "App is running"}


# Intercom posts webhooks to this route when a conversation is created or replied to
@app.post("/chat")
def conversations(request: Request):
    try:
        # Process the request body in a synchronous fashion
        request_body = async_to_sync(request.body)()
        data_str = request_body.decode("utf-8")
        request_body = json.loads(data_str)

        # Based on the body, create a ResponseDecision object
        response_decision = ResponseDecision.from_request(request_body, request.headers)

        # Exit early if we don't want to continue on to LLM for response
        if response_decision.should_return_early:
            return JSONResponse(
                content=response_decision.response_dict,
                status_code=response_decision.response_code,
            )

        # Grab needed parameters
        conv_info = response_decision.conversation_info  # Conversation information
        conversation_id = conv_info.conversation_id  # Astra User Id

        # Parse the source url of the request
        parsed_url = urlparse(conv_info.source_url)
        source_id = parsed_url.path.split("/")[-1]

        # Get the organization and associated databases
        org_id = source_id if conv_info.source_url is not None else ""
        databases = (
            get_databases(org_id)
            if mode.lower() == "development" or mode.lower() == "feat"
            else []
        )

        # Find the preferred programming language of the user
        programming_language = conv_info.contact.get("custom_attributes", {}).get(
            "programmingLanguage", "Javascript"
        )

        # Get all databases as a string associated with this user
        dbs_string = "Cannot retrieve databases for users in environments other than development."
        for db in databases:
            dbs_string += f"- {json.dumps(db)}\n"

        # Build a string associated
        db_text = ""
        if mode.lower() == "development":
            db_text = f"{'- The user has not created any databases' if databases == [] else '- Here are all the end-users databases: ' + dbs_string}"

        # Build user context information present
        user_context = "No user information present."
        if (
                conv_info.contact is not None
                and "name" in conv_info.contact
                and "email" in conv_info.contact
        ):
            user_context = (
                f"Here is information on the user:\n"
                f"- User Name: {conv_info.contact['name']}\n"
                f"- User Email: {conv_info.contact['email']}\n"
                f"- User Primary Programming Language (also known as favorite programming language and preferred "
                f"programming language): {programming_language}\n"
                f"{db_text}"
            )

        # Send an intercom debug message if debug mode is on
        persona = get_persona(conv_info.contact)
        if conv_info.debug_mode:
            send_intercom_message(
                conversation_id,
                f"Generating response: "
                f"\nContext: {user_context}\n"
                f"\nQuestion: {conv_info.user_question}\n",
            )

        ##
        # FINALLY, call the assistant
        ##
        response, responses_from_vs, context = assistant.get_response(
            conv_info.user_question, persona
        )

        # One more debugging message
        if conv_info.debug_mode:
            send_intercom_message(
                conversation_id, "\nDocuments retrieved: " + responses_from_vs
            )

        # Either comment or message based on whether it's a datastax user
        if conv_info.is_datastax_user:
            send_intercom_message(conversation_id, response)
        else:
            add_comment_to_intercom_conversation(
                conversation_id, f"NoSQL Assistant Suggested Response: {response}"
            )

        # Return the result with the full response if desired
        result = {"ok": True, "message": "Response submitted successfully."}
        if include_response:
            result["response"] = response
        if include_context:
            result["context"] = context

        return JSONResponse(content=result, status_code=requests.codes.created)

    except Exception as e:
        # Notify bugsnag if we hit an error
        bugsnag.notify(e)
        e.skip_bugsnag = True

        # Now this won't be sent a second time by the exception handlers
        raise e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
