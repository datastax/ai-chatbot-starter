import abc
from typing import Dict, List, Type

from .config import Config

integrations_registry: Dict[str, Type["BaseIntegration"]] = {}


class BaseIntegration(metaclass=abc.ABCMeta):
    required_fields: List[str]  # A list of config fields needed for this integration
    config: Config

    # Register all subclasses
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        integrations_registry[cls.__name__] = cls

    def __init__(self, config: Config):
        self.config = config
