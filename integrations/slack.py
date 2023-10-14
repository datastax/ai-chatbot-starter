from dataclasses import dataclass
from typing import Any

import requests
import os

from pipeline import ResponseAction


SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")


def send_slack_message(message: str) -> None:
    requests.post(
        SLACK_WEBHOOK_URL,
        json={"text": message, "username": "AI Bot", "icon_emoji": ":ghost:"},
    )


@dataclass
class SlackResponseAction(ResponseAction):
    @classmethod
    def from_asst_response(
        cls, conv_info: Any, bot_response: str, responses_from_vs: str, context: str
    ) -> "ResponseAction":
        send_slack_message("*PROMPT*")
        send_slack_message(context)

        send_slack_message("*RESPONSE*")
        send_slack_message(bot_response)

        return cls(response_dict=None, response_code=None)
