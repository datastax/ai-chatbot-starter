import abc
from dataclasses import dataclass
from typing import Any

from .base_integration import BaseIntegration, integrations_registry
from .config import Config


@dataclass
class UserContext:
    """
    A class to represent user context to be supplied to the LLM.
    """

    user_question: str
    persona: str
    context_str: str


class UserContextCreator(BaseIntegration, metaclass=abc.ABCMeta):
    """
    A class to create the user context. It should handle retrieving the necessary
    fields, as well as formatting them appropriately into a string.
    """
    @abc.abstractmethod
    def create_user_context(self, conv_info: Any) -> UserContext:
        pass


def create_all_user_context(
    config: Config,
    conv_info: Any,
) -> UserContext:
    """Runs all ResponseActors specified in config to take response actions"""
    # TODO: Some aggregation strategy that allows for multiple user_context_creators
    for cls_name in config.user_context_creator_cls:
        user_context_creator = integrations_registry[cls_name](config)
        assert isinstance(user_context_creator, UserContextCreator), f"Must only specify UserContextCreator in user_context_creator_cls"
        return user_context_creator.create_user_context(conv_info)

    raise ValueError(f"No UserContextCreator found - must specify one")
