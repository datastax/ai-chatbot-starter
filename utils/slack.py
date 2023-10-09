import requests

SLACK_WEBHOOK_URL = (
    "https://hooks.slack.com/services/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"
)


def send_slack_message(message):
    requests.post(
        SLACK_WEBHOOK_URL,
        json={"text": message, "username": "AI Bot", "icon_emoji": ":ghost:"},
    )
