import abc
from dataclasses import dataclass
from typing import Any, Dict, Optional

from llama_index import Response

from .base_integration import BaseIntegration, integrations_registry
from .config import Config


@dataclass
class EndpointResponse:
    """
    A class to handle actions to take based on the response
    from the assistant.
    """
    response_dict: Optional[Dict[str, Any]]
    response_code: Optional[int]


class ResponseActor(BaseIntegration, metaclass=abc.ABCMeta):
    """
    A class to take any actions based on the chatbot output, and return the
    response we will produce from the endpoint. If response is None, will iterate
    until we find a valid response
    """
    @abc.abstractmethod
    def take_action(
        self,
        conv_info: Any,
        bot_response: Response,
        responses_from_vs: str,
        context: str,
    ) -> Optional[EndpointResponse]:
        pass


def take_all_actions(
    config: Config,
    conv_info: Any,
    bot_response: Response,
    responses_from_vs: str,
    context: str
) -> EndpointResponse:
    """Runs all ResponseActors specified in config to take response actions"""
    endpoint_response = None

    for cls_name in config.response_actor_cls:
        response_actor = integrations_registry[cls_name](config)
        assert isinstance(response_actor, ResponseActor), f"Must only specify ResponseActor in response_actor_cls"
        curr_endpoint_response = response_actor.take_action(conv_info, bot_response, responses_from_vs, context)

        if curr_endpoint_response is not None:
            endpoint_response = curr_endpoint_response

    if endpoint_response is None:
        raise ValueError(f"Must return at least one valid response from all ResponseActors")

    return endpoint_response
