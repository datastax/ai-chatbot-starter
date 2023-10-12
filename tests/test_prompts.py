import sys
import os
import pytest

sys.path.append("../")

from chatbot_api.assistant import AssistantBison

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
def test_prompts(persona, astra_table_name, gcp_conn):
    assistant = AssistantBison(
        table_name=astra_table_name,
        max_tokens_response=1024,
        k=4,
        company=os.getenv("COMPANY"),
        custom_rules=os.getenv("CUSTOM_RULES").split("\n"),
    )

    print(f"\n{persona} Questions:")
    for x, question in enumerate(questions):
        print(f"#{x + 1}: {question}")
        response = assistant.get_response(question, persona, user_context=mock_context)
        print(response)
