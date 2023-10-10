import os
from typing import Tuple

from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster, Session


def get_persona(contact):
    """Given information about the user, choose a persona and associated prompt"""
    # TODO: Only a single prompt here, extend as needed!

    return "default"


def init_astra_session_keyspace_tablename() -> Tuple[Session, str, str]:
    """Initializes the Astra DB session and returns keyspace, table_name from env vars"""
    keyspace = os.getenv("ASTRA_DB_KEYSPACE", "chat")
    table_name = os.getenv("ASTRA_DB_TABLE_NAME", "chatbot_documents_cleaned")
    session = init_astra_session(keyspace)

    return session, keyspace, table_name


def init_astra_session(keyspace: str) -> Session:
    """Initialize connection to Astra DB based on env vars"""
    secure_connect_bundle = os.getenv("SECURE_CONNECT_BUNDLE")
    cassandra_token = os.getenv("CASSANDRA_TOKEN")

    # Set up Cassandra instance
    cloud_config = {"secure_connect_bundle": secure_connect_bundle}
    auth_provider = PlainTextAuthProvider("token", cassandra_token)
    cluster = Cluster(
        cloud=cloud_config,
        auth_provider=auth_provider,
    )
    return cluster.connect(keyspace)
