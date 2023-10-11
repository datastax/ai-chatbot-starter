from typing import Dict, Type


def register(registry: Dict[str, Type], cls: Type) -> None:
    registry[cls.__name__] = cls
