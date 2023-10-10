import sys

import pytest

sys.path.append("../")

from chatbot_api.nosql_assistant import AssistantBison
from utils.astra import init_astra_session_keyspace_tablename
from utils.google import init_gcp

session, keyspace, table_name = init_astra_session_keyspace_tablename()
init_gcp()

mock_context = (
    f"Here is information on the user:\n"
    f"- User Name: Fake User\n"
    f"- User Email: fake.user@example.com\n"
    f"- User Primary Programming Language (also known as favorite programming language and preferred programming language): Javascript\n"
    f"The user has not created any databases"
)

questions = [
    "What is your name?",  # NOTE: This prompt can cause 'unsafe' responses from bison
    "How do I create a token?",
]


@pytest.mark.parametrize("persona", ["default"])
def test_prompts(persona):
    assistant = AssistantBison(
        session,
        keyspace=keyspace,
        table_name=table_name,
        max_tokens_response=1024,
    )

    print(f"\n{persona} Questions:")
    for x, question in enumerate(questions):
        print(f"#{x + 1}: {question}")
        response = assistant.get_response(question, persona, user_context=mock_context)
        print(response)
