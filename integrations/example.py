"""
A file to show an example basic integration - other integrations can be created by following this
format. This example takes in a request with a single required field "question", passes that as
the prompt to the LLM, then prints the resulting question/answer pair upon request completion.

NOTE: You must add this import to `integrations/__init__.py` in order for it to get added to the registry.
"""
from typing import Any, Mapping

from pipeline import (
    BaseIntegration,
    ResponseActor,
    ResponseDecider,
    ResponseDecision,
    UserContext,
    UserContextCreator,
)


class ExampleMixin(BaseIntegration):
    required_fields = []


# TODO: Decouple conv_info from ResponseDecider (should only have to implement UserContextCreator)
class ExampleResponseDecider(ExampleMixin, ResponseDecider):
    """An example of deciding on a response and producing conv_info"""

    def make_response_decision(
        self, request_body: Mapping[str, Any], request_headers: Mapping[str, str],
    ) -> ResponseDecision:
        assert "question" in request_body, "Include 'question' field in the POST request"
        return ResponseDecision(
            should_return_early=False,
            conversation_info={"question": request_body["question"]},
        )


class ExampleUserContextCreator(ExampleMixin, UserContextCreator):
    """An example of creating User Context to modify for any integrations"""

    def create_user_context(self, conv_info: Any) -> UserContext:
        return UserContext(
            user_question=conv_info["question"],
            persona="default",
            context_str="",
        )


class ExampleResponseActor(ExampleMixin, ResponseActor):
    """An example of a response actor that takes action based on the chatbot response"""

    def take_action(self, conv_info: Any, text_response: str, responses_from_vs: str, context: str) -> None:
        print("Bot Response:")
        print(f"    Question: {conv_info['question']}")
        print(f"")
