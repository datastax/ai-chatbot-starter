import abc
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from .base_integration import BaseIntegration, integrations_registry
from .config import Config


@dataclass
class ResponseDecision:
    """
    A class to handle incoming requests and determine whether
    to engage the chatbot to answer, or return early based on
    conditional logic.
    """

    should_return_early: bool
    response_dict: Optional[Dict[str, Any]] = None
    response_code: Optional[int] = None
    conversation_info: Optional[Any] = None


class ResponseDecider(BaseIntegration, metaclass=abc.ABCMeta):
    """A class to make a response decision based on the request input"""

    @abc.abstractmethod
    def make_response_decision(
        self,
        request_body: Mapping[str, Any],
        request_headers: Mapping[str, str],
    ) -> ResponseDecision:
        pass


def make_all_response_decisions(
    config: Config,
    request_body: Mapping[str, Any],
    request_headers: Mapping[str, str],
) -> ResponseDecision:
    """Runs all ResponseDeciders specified in config to return ResponseDecision's"""
    # TODO: Some aggregation strategy that allows for multiple response deciders present
    for cls_name in config.response_decider_cls:
        response_actor = integrations_registry[cls_name](config)
        assert isinstance(
            response_actor, ResponseDecider
        ), f"Must only specify ResponseDecider in response_decider_cls"
        return response_actor.make_response_decision(request_body, request_headers)

    # No response deciders present, so just keep going
    return ResponseDecision(should_return_early=False)
