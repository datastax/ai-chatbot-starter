from typing import Any

import requests

from pipeline import ResponseActor


class SlackResponseActor(ResponseActor):
    required_fields = ["slack_webhook_url"]

    def send_slack_message(self, message: str) -> None:
        requests.post(
            self.config.slack_webhook_url,
            json={"text": message, "username": "AI Bot", "icon_emoji": ":ghost:"},
        )

    def take_action(
        self, conv_info: Any, text_response: str, responses_from_vs: str, context: str
    ) -> None:
        self.send_slack_message("*PROMPT*")
        self.send_slack_message(context)

        self.send_slack_message("*RESPONSE*")
        self.send_slack_message(text_response)
