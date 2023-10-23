import abc
from typing import Any

from .base_integration import BaseIntegration, integrations_registry
from .config import Config


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
        text_response: str,
        responses_from_vs: str,
        context: str,
    ) -> None:
        pass


def take_all_actions(
    config: Config,
    conv_info: Any,
    text_response: str,
    responses_from_vs: str,
    context: str
) -> None:
    """Runs all ResponseActors specified in config to take response actions"""
    for cls_name in config.response_actor_cls:
        response_actor = integrations_registry[cls_name](config)
        assert isinstance(response_actor, ResponseActor), f"Must only specify ResponseActor in response_actor_cls"
        response_actor.take_action(conv_info, text_response, responses_from_vs, context)
