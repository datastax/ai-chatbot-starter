import os
from typing import Any, Dict

import cassio

DEFAULT_TABLE_NAME = "data"
DEFAULT_KEYSPACE = "chat"


def get_persona(contact: Dict[str, Any]) -> str:
    """Given information about the user, choose a persona and associated prompt"""
    # TODO: Only a single prompt here, extend as needed!

    return "default"


def init_astra() -> None:
    """Initializes the Astra DB session via cassio"""
    cassio.init(
        token=os.getenv("ASTRA_DB_TOKEN"),
        database_id=os.getenv("ASTRA_DB_DATABASE_ID"),
        keyspace = os.getenv("ASTRA_DB_KEYSPACE", DEFAULT_KEYSPACE),
    )


def init_astra_get_table_name() -> str:
    """Initializes Astra connection and returns the table name"""
    init_astra()
    return os.getenv("ASTRA_DB_TABLE_NAME", DEFAULT_TABLE_NAME)
