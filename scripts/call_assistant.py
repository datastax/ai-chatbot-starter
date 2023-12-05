import httpx
import sys


###
# Let's define the question right here
###
CHATBOT_QUESTION = "What is Stargate? Can you give 5 key benefits?"


def call_assistant_async(chatbot_question=CHATBOT_QUESTION):
    # Set the request appropriately
    headers = {}
    request_body = {"question": chatbot_question}

    full_result = ""
    with httpx.stream(
        "POST",
        "http://127.0.0.1:5555/chat",
        json=request_body,
        headers=headers,
        timeout=600,
    ) as r:
        for chunk in r.iter_text():
            print(chunk, flush=True, end="")
            full_result += chunk

    return full_result


def call_assistant_sync(chatbot_question=CHATBOT_QUESTION):
    # Set the request appropriately
    headers = {}
    request_body = {"question": chatbot_question}

    r = httpx.post("http://127.0.0.1:5555/chat", json=request_body, headers=headers)

    # Check if the request was successful
    if r.status_code == httpx.codes.created:
        return r.content.decode()
    else:
        return f"Request failed with status code {r.status_code}: {r.text}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise ValueError("Please provide a question to ask the chatbot")

    call_assistant_async(chatbot_question=sys.argv[1])

    # Alternatively
    # example_result = call_assistant_sync()
    # print(example_result)
