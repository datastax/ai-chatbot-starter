from typing import Any

from llama_index import Response
import requests

from pipeline import EndpointResponse, ResponseActor


class SlackResponseActor(ResponseActor):
    required_fields = ["slack_webhook_url"]

    def send_slack_message(self, message: str) -> None:
        requests.post(
            self.config.slack_webhook_url,
            json={"text": message, "username": "AI Bot", "icon_emoji": ":ghost:"},
        )

    def take_action(
        self, conv_info: Any, bot_response: Response, responses_from_vs: str, context: str
    ) -> EndpointResponse:
        self.send_slack_message("*PROMPT*")
        self.send_slack_message(context)

        self.send_slack_message("*RESPONSE*")
        self.send_slack_message(bot_response)

        return None
