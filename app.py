import json
import bugsnag
import logging

from asgiref.sync import async_to_sync
from bugsnag.handlers import BugsnagHandler
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

# NOTE: Load dotenv before importing any code from other files for globals
# TODO: Probably make this unnecessary with better abstractions
load_dotenv(".env")

from chatbot_api.assistant import AssistantBison
from integrations.astra import init_astra
from pipeline import (
    create_all_user_context,
    make_all_response_decisions,
    take_all_actions,
)
from pipeline.config import load_config

# Load Config
config = load_config()

# Setup astra table name
init_astra(config)

# Configure bugsnag
bugsnag.configure(api_key=config.bugsnag_api_key, project_root="/", release_stage=config.mode)

# Set up the logging infrastructure
logger = logging.getLogger("test.logger")
handler = BugsnagHandler()
# send only ERROR-level logs and above
handler.setLevel(logging.ERROR)
logger.addHandler(handler)

# Define the FastAPI application
app = FastAPI(
    title="AI Chatbot Starter",
    description="An LLM-powered Chatbot for Documentation",
    summary="Build an LLM-powered Chatbot for a given documentation set",
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
    config=config,
    max_tokens_response=1024,
    k=4,
    company=config.company,
    custom_rules=config.custom_rules,
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
        response_decision = make_all_response_decisions(
            config=config,
            request_body=request_body,
            request_headers=request.headers,
        )

        # Exit early if we don't want to continue on to LLM for response
        if response_decision.should_return_early:
            return JSONResponse(
                content=response_decision.response_dict,
                status_code=response_decision.response_code,
            )

        # Assemble context for assistant query from relevant sources based on conversation
        user_context = create_all_user_context(
            config=config,
            conv_info=response_decision.conversation_info,
        )

        # Call the assistant to retrieve a response
        bot_response, responses_from_vs, context = assistant.get_response(
            user_input=user_context.user_question,
            persona=user_context.persona,
            user_context=user_context.context_str,
        )

        def stream_data():
            txt_response = ""
            for text in bot_response.response_gen:
                txt_response += text
                yield text

            # Take action based on the response from the bot
            take_all_actions(
                config=config,
                conv_info=response_decision.conversation_info,
                text_response=txt_response,
                responses_from_vs=responses_from_vs,
                context=context,
            )

        return StreamingResponse(
            stream_data(),
            media_type="text/event-stream",
            status_code=201,
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
