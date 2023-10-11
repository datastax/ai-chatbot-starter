import os
from typing import List

from langchain.prompts import load_prompt


def get_template(
    persona: str,
    vector_search_results: str,
    user_question: str,
    user_context: str,
    company: str,
    custom_rules: List[str],
) -> str:
    persona_path = f"prompts/{persona}.yaml"
    if not os.path.exists(persona_path):
        persona_path = f"../prompts/{persona}.yaml"

    prompt = load_prompt(persona_path)
    input_txt = prompt.format(
        **{
            "vector_search_results": vector_search_results,
            "user_question": user_question,
            "user_context": user_context,
            "company": company,
            "custom_rules": "\n".join(custom_rules),
        }
    )

    return input_txt
