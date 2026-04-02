from semaphore.client import SemaphoreClient


def list_keys(client: SemaphoreClient, project_id: int) -> list[dict]:
    return client.get(f"/api/project/{project_id}/keys")


def create_key(client: SemaphoreClient, project_id: int, cfg: dict) -> dict:
    return client.post(f"/api/project/{project_id}/keys", _payload(project_id, cfg))


def update_key(client: SemaphoreClient, project_id: int, key_id: int, cfg: dict) -> None:
    client.put(f"/api/project/{project_id}/keys/{key_id}", {"id": key_id, **_payload(project_id, cfg)})


def _payload(project_id: int, cfg: dict) -> dict:
    key_type = cfg["type"]
    payload: dict = {"name": cfg["name"], "type": key_type, "project_id": project_id}
    if key_type == "ssh":
        payload["ssh"] = cfg.get("ssh", {})
    elif key_type == "login_password":
        payload["login_password"] = cfg.get("login_password", {})
    return payload
