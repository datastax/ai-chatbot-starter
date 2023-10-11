import abc
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Type

from .utils import register

response_decision_registry: Dict[str, Type["ResponseDecision"]] = {}


@dataclass
class ResponseDecision(metaclass=abc.ABCMeta):
    """
    A class to handle incoming requests and determine whether
    to engage the chatbot to answer, or return early based on
    conditional logic.
    """

    should_return_early: bool
    response_dict: Optional[Dict[str, Any]] = None
    response_code: Optional[int] = None
    conversation_info: Optional[Any] = None

    # Register all subclasses
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        register(response_decision_registry, cls)

    @classmethod
    @abc.abstractmethod
    def from_request(
        cls,
        request_body: Mapping[str, Any],
        request_headers: Mapping[str, str],
    ) -> "ResponseDecision":
        pass
