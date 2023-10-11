import abc
from dataclasses import dataclass
from typing import Any, Dict, Type

from .utils import register

user_context_registry: Dict[str, Type["UserContext"]] = {}


@dataclass
class UserContext(metaclass=abc.ABCMeta):
    """
    A class to represent user context to be supplied to the LLM.
    It should handle retrieving the necessary fields, as well as
    formatting them appropriately into a string.
    """

    user_question: str
    persona: str
    context_str: str

    # Register all subclasses
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        register(user_context_registry, cls)

    @classmethod
    @abc.abstractmethod
    def from_conversation_info(cls, conv_info: Any) -> "UserContext":
        pass
