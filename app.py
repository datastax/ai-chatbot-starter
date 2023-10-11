import json
import os
import bugsnag
import logging

from asgiref.sync import async_to_sync
from bugsnag.handlers import BugsnagHandler
from chatbot_api.nosql_assistant import AssistantBison
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from integrations.astra import init_astra_get_table_name
from integrations.google import init_gcp
from integrations.intercom import (
    IntercomResponseAction,
    IntercomResponseDecision,
    IntercomUserContext,
)


load_dotenv(".env")

# Grab the env variables loaded above
mode = os.getenv("MODE", "Development")
bugsnag_api_key = os.getenv("BUGSNAG_API_KEY")
dscloud_app_version = os.getenv("DSCLOUD_APP_VERSION")

# Setup astra and GCP
table_name = init_astra_get_table_name()
init_gcp()

# Configure bugsnag
bugsnag.configure(
    api_key=bugsnag_api_key,
    project_root="/",
    release_stage=mode,
    app_version=dscloud_app_version,
)

# Setup the logging infrastructure
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
        response_decision = IntercomResponseDecision.from_request(request_body, request.headers)

        # Exit early if we don't want to continue on to LLM for response
        if response_decision.should_return_early:
            return JSONResponse(
                content=response_decision.response_dict,
                status_code=response_decision.response_code,
            )

        # Assemble context for assistant query from relevant sources based on conversation
        user_context = IntercomUserContext.from_conversation_info(
            response_decision.conversation_info
        )

        ##
        # FINALLY, call the assistant
        ##
        bot_response, responses_from_vs, context = assistant.get_response(
            user_input=user_context.user_question,
            persona=user_context.persona,
            user_context=user_context.context_str,
        )

        # Take action based on the response from the bot
        response_action = IntercomResponseAction.from_asst_response(
            conv_info=response_decision.conversation_info,
            bot_response=bot_response,
            responses_from_vs=responses_from_vs,
            context=context,
        )

        return JSONResponse(
            content=response_action.response_dict,
            status_code=response_action.response_code,
        )

    except Exception as e:
        # Notify bugsnag if we hit an error
        bugsnag.notify(e)
        e.skip_bugsnag = True

        # Now this won't be sent a second time by the exception handlers
        raise e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
