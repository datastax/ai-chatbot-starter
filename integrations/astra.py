from typing import Any, Dict

import cassio

from pipeline.config import Config


def get_persona(contact: Dict[str, Any]) -> str:
    """Given information about the user, choose a persona and associated prompt"""
    # TODO: Only a single prompt here, extend as needed!

    return "default"


def init_astra(config: Config) -> None:
    """Initializes the Astra DB session via cassio"""
    cassio.init(
        token=config.astra_db_token,
        database_id=config.astra_db_database_id,
        keyspace=config.astra_db_keyspace,
    )
