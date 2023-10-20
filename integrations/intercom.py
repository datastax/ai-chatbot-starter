import hashlib
import hmac
import re
import json
import bugsnag
import requests

from dataclasses import dataclass
from integrations.astra import get_persona
from pipeline import (
    BaseIntegration,
    ResponseActor,
    ResponseDecider,
    ResponseDecision,
    UserContext,
    UserContextCreator,
)
from typing import Any, Dict, List, Optional, Mapping, Union

# Pulled from https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Conversations/conversation/
DEFAULT_ALLOWED_DELIVERED_AS = [
    "customer_initiated",
    "admin_initiated",
    "campaigns_initiated",
    "operator_initiated",
    "automated",
]


# Validate the webhook actually comes from Intercom servers
def validate_signature(
    header: Mapping[str, str], body: Mapping[str, Any], secret: str
) -> bool:
    # Get the signature from the payload
    signature_header = header["X-Hub-Signature"]
    sha_name, signature = signature_header.split("=")
    if sha_name != "sha1":
        print("ERROR: X-Hub-Signature in payload headers was not sha1=****")
        return False
    # Convert the dictionary to a JSON string
    data_str = json.dumps(body)
    data_bytes = data_str.encode("utf-8")

    local_signature = hmac.new(
        secret.encode("utf-8"), msg=data_bytes, digestmod=hashlib.sha1
    )

    # See if they match
    return hmac.compare_digest(local_signature.hexdigest(), signature)


class IntercomIntegrationMixin(BaseIntegration):
    required_fields = ["bot_intercom_id", "intercom_token", "intercom_client_secret"]

    # Get an Intercom contact/lead using the Intercom UUID
    def get_intercom_contact_by_id(self, _id: Union[int, str]) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.config.intercom_token}"}
        res = requests.get(f"https://api.intercom.io/contacts/{_id}", headers=headers)
        return res.json()

    def add_comment_to_intercom_conversation(
        self, conversation_id: str, message: str,
    ) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.config.intercom_token}"}
        res = requests.post(
            f"https://api.intercom.io/conversations/{conversation_id}/reply",
            headers=headers,
            json={
                "message_type": "note",
                "type": "admin",
                "admin_id": self.config.bot_intercom_id,
                "body": message,
            },
        )
        return res.json()

    # Reply to an existing Intercom conversation
    def send_intercom_message(self, conversation_id: str, message: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.config.intercom_token}"}
        payload = {
            "type": "admin",
            "admin_id": self.config.bot_intercom_id,
            "message_type": "comment",
            "body": message,
        }
        res = requests.post(
            f"https://api.intercom.io/conversations/{conversation_id}/reply",
            json=payload,
            headers=headers,
        )
        return res.json()


@dataclass
class IntercomConversationInfo:
    """A class representing all the required attributes from the chatbot to give a response"""

    conversation_id: str
    contact: Dict[str, Any]
    user_question: str
    is_user: bool
    debug_mode: bool
    source_url: str


class IntercomResponseDecider(IntercomIntegrationMixin, ResponseDecider):
    """A class that determines the type of action to take based on the intercom request payload"""

    conversation_info: Optional[IntercomConversationInfo] = None

    def make_response_decision(
        self,
        request_body: Mapping[str, Any],
        request_headers: Mapping[str, str],
        allowed_delivered_as: Optional[List[str]] = None,
    ) -> ResponseDecision:
        """Set properties based on each of the logical branches we can take"""
        # NOTE: Empty list will be overriden
        allowed_delivered_as = allowed_delivered_as or DEFAULT_ALLOWED_DELIVERED_AS

        # Don't allow invalid signatures
        if not validate_signature(
            request_headers, request_body, self.config.intercom_client_secret
        ):
            return ResponseDecision(
                should_return_early=True,
                response_dict={"ok": False, "message": "Invalid signature."},
                response_code=401,
            )
        # Ignore repeat deliveries
        if request_body["delivery_attempts"] > 1:
            return ResponseDecision(
                should_return_early=True,
                response_dict={"ok": True, "message": "Already reported."},
                response_code=208,
            )

        data = request_body["data"]

        debugging_payload = {"request": data}
        bugsnag.notify(
            Exception(debugging_payload)
        )  # TODO: Simply for temporary debugging

        # Handle intercom webhook tests
        if data["item"]["type"] == "ping":
            return ResponseDecision(
                should_return_early=True,
                response_dict={"ok": True, "message": "Successful ping."},
                response_code=200,
            )
        # Check for empty source
        if data["item"]["source"] is None:
            return ResponseDecision(
                should_return_early=True,
                response_dict={"ok": False, "message": "Empty source."},
                response_code=400,
            )

        # Find relevant part of intercom conversation for most recent message
        conversation_parts = data["item"]["conversation_parts"]["conversation_parts"]
        filtered_conversation_parts = [
            part
            for part in conversation_parts
            if part.get("part_type") != "default_assignment"
            and part.get("body")  # Filter for nulls and empty strings
        ]

        # Use conversation parts if available (means user responded in the convo),
        # otherwise use the source (means user initiated a convo)
        if len(filtered_conversation_parts) > 0:
            conv_item = filtered_conversation_parts[0]
        else:
            conv_item = data["item"]["source"]

        conversation_text = conv_item["body"]
        author = conv_item["author"]

        def callback(event):
            event.user = {"email": author["email"]}

        bugsnag.before_notify(callback)

        # possible to be Contact, Admin, Campaign, Automated or Operator initiated
        delivered_as = "not_customer_initiated"
        if "delivered_as" in data["item"]["source"]:
            delivered_as = data["item"]["source"]["delivered_as"]

        conv_is_authorized = (
            author["type"] == "user" and delivered_as in allowed_delivered_as
        )

        if not conv_is_authorized:
            return ResponseDecision(
                should_return_early=True,
                response_dict={"ok": False, "message": "Unauthorized user."},
                response_code=403,
            )

        user_question = re.sub("<[^<]+?>", "", str(conversation_text))
        # Reject request if empty question
        if not user_question:
            return ResponseDecision(
                should_return_early=True,
                response_dict={"ok": False, "message": "Query provided was empty"},
                response_code=400,
            )

        # If we passed every check above, should proceed with querying the LLM
        return ResponseDecision(
            should_return_early=False,
            conversation_info=IntercomConversationInfo(
                conversation_id=data["item"]["id"],
                contact=self.get_intercom_contact_by_id(author["id"]),
                user_question=user_question,
                is_user=f"@{self.config.company_url}" in author["email"] and self.config.company_url != "",
                debug_mode="[DEBUG]" in user_question,
                source_url=data["item"]["source"]["url"],
            ),
        )


class IntercomUserContextCreator(IntercomIntegrationMixin, UserContextCreator):

    def create_user_context(
        self, conv_info: IntercomConversationInfo
    ) -> UserContext:
        # Grab needed parameters
        conversation_id = conv_info.conversation_id  # Astra User Id

        # Build user context information present
        context_str = "No user information present."
        if (
            conv_info.contact is not None
            and "name" in conv_info.contact
            and "email" in conv_info.contact
        ):
            context_str = (
                f"Here is information on the user:\n"
                f"- User Name: {conv_info.contact['name']}\n"
                f"- User Email: {conv_info.contact['email']}\n"
            )

        # Send an intercom debug message if debug mode is on
        if conv_info.debug_mode:
            self.send_intercom_message(
                conversation_id,
                f"Generating response: "
                f"\nContext: {context_str}\n"
                f"\nQuestion: {conv_info.user_question}\n",
            )

        return UserContext(
            user_question=conv_info.user_question,
            persona=get_persona(conv_info.contact),
            context_str=context_str,
        )


class IntercomResponseActor(IntercomIntegrationMixin, ResponseActor):

    def take_action(
        self,
        conv_info: IntercomConversationInfo,
        text_response: str,
        responses_from_vs: str,
        context: str,
    ) -> None:
        # One more debugging message
        if conv_info.debug_mode:
            self.send_intercom_message(
                conv_info.conversation_id, "\nDocuments retrieved: " + responses_from_vs
            )

        # Either comment or message based on whether its a current user
        if conv_info.is_user:
            self.send_intercom_message(conv_info.conversation_id, text_response)
        else:
            self.add_comment_to_intercom_conversation(
                conv_info.conversation_id,
                f"Assistant Suggested Response: {text_response}",
            )

        # Return the result with the full response if desired
        result = {"ok": True, "message": "Response submitted successfully."}
        if self.config.intercom_include_response:
            result["response"] = text_response
        if self.config.intercom_include_context:
            result["context"] = context
