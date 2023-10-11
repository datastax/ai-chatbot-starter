import abc
from dataclasses import dataclass
from typing import Any, Dict, Optional, Type

from .utils import register

response_action_registry: Dict[str, Type["ResponseAction"]] = {}


@dataclass
class ResponseAction(metaclass=abc.ABCMeta):
    """
    A class to handle actions to take based on the response
    from the assistant. Should take the actions in from_asst_response
    and set the response content for the endpoint with response_dict.

    If response_dict is None, will iterate until we find a valid response_dict
    """

    response_dict: Optional[Dict[str, Any]]
    response_code: Optional[int]

    # Register all subclasses
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        register(response_action_registry, cls)

    @classmethod
    @abc.abstractmethod
    def from_asst_response(
        cls,
        conv_info: Any,
        bot_response: str,
        responses_from_vs: str,
        context: str,
    ) -> "ResponseAction":
        pass
