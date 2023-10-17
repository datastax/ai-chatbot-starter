import openai

OPENAI_EMB_DIM = 1536

def init_chat_completion():
    return openai.ChatCompletion