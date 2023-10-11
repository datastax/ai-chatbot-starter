import os
from typing import Any, List

import requests

orchestrator_admin_token = os.getenv("ORCHESTRATOR_ADMIN_TOKEN")
orchestrator_endpoint = os.getenv("ORCHESTRATOR_ENDPOINT")
mode = os.getenv("MODE", "Development")


# Get all databases using an Astra organization Id
def get_databases(org_id: str) -> List[Any]:
    try:
        headers = {"Authorization": f"Bearer {orchestrator_admin_token}"}
        res = requests.get(
            f"{orchestrator_endpoint}/v2/admin/databases?orgId={org_id}",
            headers=headers,
        )
        return res.json()
    except:
        # TODO: I don't think we want to notify each time this occurs
        # bugsnag.notify(Exception("Error calling orchestrator get databases API"))
        return []
