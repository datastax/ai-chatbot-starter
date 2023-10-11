from dataclasses import dataclass
import hashlib
import hmac
import os
import re
import json
from typing import Any, Dict, List, Optional, Mapping, Union

import bugsnag
from dotenv import load_dotenv
import requests
from urllib.parse import urlparse

from integrations.astra import get_persona
from integrations.orchestrator import get_databases
from pipeline import ResponseAction, ResponseDecision, UserContext


load_dotenv(".env")


intercom_token = os.getenv("INTERCOM_TOKEN")
intercom_client_secret = os.getenv("INTERCOM_CLIENT_SECRET")
bot_intercom_id = os.getenv("BOT_INTERCOM_ID")

# Pulled from https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Conversations/conversation/
DEFAULT_ALLOWED_DELIVERED_AS = [
    "customer_initiated",
    "admin_initiated",
    "campaigns_initiated",
    "operator_initiated",
    "automated",
]


# Get an Intercom contact/lead using the Intercom UUID
def get_intercom_contact_by_id(_id: Union[int, str]) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {intercom_token}"}
    res = requests.get(f"https://api.intercom.io/contacts/{_id}", headers=headers)
    return res.json()


def add_comment_to_intercom_conversation(
    conversation_id: str, message: str
) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {intercom_token}"}
    res = requests.post(
        f"https://api.intercom.io/conversations/{conversation_id}/reply",
        headers=headers,
        json={
            "message_type": "note",
            "type": "admin",
            "admin_id": bot_intercom_id,
            "body": message,
        },
    )
    return res.json()


# Reply to an existing Intercom conversation
def send_intercom_message(conversation_id: str, message: str) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {intercom_token}"}
    payload = {
        "type": "admin",
        "admin_id": bot_intercom_id,
        "message_type": "comment",
        "body": message,
    }
    res = requests.post(
        f"https://api.intercom.io/conversations/{conversation_id}/reply",
        json=payload,
        headers=headers,
    )
    return res.json()


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


@dataclass
class IntercomConversationInfo:
    """A class representing all the required attributes from the chatbot to give a response"""

    conversation_id: str
    contact: Dict[str, Any]
    user_question: str
    is_datastax_user: bool
    debug_mode: bool
    source_url: str


@dataclass
class IntercomResponseDecision(ResponseDecision):
    """A class that determines the type of action to take based on the intercom request payload"""

    conversation_info: Optional[IntercomConversationInfo] = None

    @classmethod
    def from_request(
        cls,
        request_body: Mapping[str, Any],
        request_headers: Mapping[str, str],
        allowed_delivered_as: Optional[List[str]] = None,
    ) -> "IntercomResponseDecision":
        """Set properties based on each of the logical branches we can take"""
        # NOTE: Empty list will be overriden
        allowed_delivered_as = allowed_delivered_as or DEFAULT_ALLOWED_DELIVERED_AS

        # Don't allow invalid signatures
        if not validate_signature(
            request_headers, request_body, intercom_client_secret
        ):
            return cls(
                should_return_early=True,
                response_dict={"ok": False, "message": "Invalid signature."},
                response_code=401,
            )
        # Ignore repeat deliveries
        if request_body["delivery_attempts"] > 1:
            return cls(
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
            return cls(
                should_return_early=True,
                response_dict={"ok": True, "message": "Successful ping."},
                response_code=200,
            )
        # Check for empty source
        if data["item"]["source"] is None:
            return cls(
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
            return cls(
                should_return_early=True,
                response_dict={"ok": False, "message": "Unauthorized user."},
                response_code=403,
            )

        user_question = re.sub("<[^<]+?>", "", str(conversation_text))
        # Reject request if empty question
        if not user_question:
            return cls(
                should_return_early=True,
                response_dict={"ok": False, "message": "Query provided was empty"},
                response_code=400,
            )

        # If we passed every check above, should proceed with querying the LLM
        return cls(
            should_return_early=False,
            conversation_info=IntercomConversationInfo(
                conversation_id=data["item"]["id"],
                contact=get_intercom_contact_by_id(author["id"]),
                user_question=user_question,
                is_datastax_user="@datastax.com" in author["email"],
                debug_mode="[DEBUG]" in user_question,
                source_url=data["item"]["source"]["url"],
            ),
        )


@dataclass
class IntercomUserContext(UserContext):
    @classmethod
    def from_conversation_info(
        cls, conv_info: IntercomConversationInfo
    ) -> "IntercomUserContext":
        # Grab needed parameters
        mode = os.getenv("MODE", "Development")
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
                f"- User Primary Programming Language (also known as favorite programming language and preferred programming language): {programming_language}\n"
                f"{db_text}"
            )

        # Send an intercom debug message if debug mode is on
        if conv_info.debug_mode:
            send_intercom_message(
                conversation_id,
                f"Generating response: "
                f"\nContext: {context_str}\n"
                f"\nQuestion: {conv_info.user_question}\n",
            )

        return cls(
            user_question=conv_info.user_question,
            persona=get_persona(conv_info.contact),
            context_str=context_str,
        )


@dataclass
class IntercomResponseAction(ResponseAction):
    @classmethod
    def from_asst_response(
        cls,
        conv_info: IntercomConversationInfo,
        bot_response: str,
        responses_from_vs: str,
        context: str,
    ) -> "IntercomResponseAction":
        # Read necessary env vars
        include_response = os.getenv("INCLUDE_RESPONSE", True)
        include_context = os.getenv("INCLUDE_CONTEXT", True)

        # One more debugging message
        if conv_info.debug_mode:
            send_intercom_message(
                conv_info.conversation_id, "\nDocuments retrieved: " + responses_from_vs
            )

        # Either comment or message based on whether its a datastax user
        if conv_info.is_datastax_user:
            send_intercom_message(conv_info.conversation_id, bot_response)
        else:
            add_comment_to_intercom_conversation(
                conv_info.conversation_id,
                f"NoSQL Assistant Suggested Response: {bot_response}",
            )

        # Return the result with the full response if desired
        result = {"ok": True, "message": "Response submitted successfully."}
        if include_response:
            result["response"] = bot_response
        if include_context:
            result["context"] = context

        return cls(
            response_dict=result,
            response_code=requests.codes.created,
        )
