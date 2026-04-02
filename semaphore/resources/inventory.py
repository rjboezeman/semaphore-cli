from semaphore.client import SemaphoreClient


def list_inventory(client: SemaphoreClient, project_id: int) -> list[dict]:
    return client.get(f"/api/project/{project_id}/inventory")


def create_inventory(client: SemaphoreClient, project_id: int, cfg: dict, key_map: dict[str, int]) -> dict:
    return client.post(f"/api/project/{project_id}/inventory", _payload(project_id, cfg, key_map))


def update_inventory(client: SemaphoreClient, project_id: int, inv_id: int, cfg: dict, key_map: dict[str, int]) -> None:
    client.put(f"/api/project/{project_id}/inventory/{inv_id}", {"id": inv_id, **_payload(project_id, cfg, key_map)})


def _payload(project_id: int, cfg: dict, key_map: dict[str, int]) -> dict:
    return {
        "name": cfg["name"],
        "project_id": project_id,
        "type": cfg.get("type", "static"),
        "inventory": cfg.get("inventory", ""),
        "ssh_key_id": key_map[cfg.get("ssh_key", "none")],
        "become_key_id": key_map[cfg.get("become_key", "none")],
    }
