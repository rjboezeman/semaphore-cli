import json as json_mod

from semaphore.client import SemaphoreClient


def list_environments(client: SemaphoreClient, project_id: int) -> list[dict]:
    return client.get(f"/api/project/{project_id}/environment")


def create_environment(client: SemaphoreClient, project_id: int, cfg: dict) -> dict:
    return client.post(f"/api/project/{project_id}/environment", _payload(project_id, cfg))


def update_environment(client: SemaphoreClient, project_id: int, env_id: int, cfg: dict) -> None:
    client.put(f"/api/project/{project_id}/environment/{env_id}", {"id": env_id, **_payload(project_id, cfg)})


def _payload(project_id: int, cfg: dict) -> dict:
    json_vars = cfg.get("json", {})
    env_vars = cfg.get("env", None)
    return {
        "name": cfg["name"],
        "project_id": project_id,
        "json": json_mod.dumps(json_vars) if isinstance(json_vars, dict) else json_vars,
        "env": json_mod.dumps(env_vars) if isinstance(env_vars, dict) else env_vars,
    }
