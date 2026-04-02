from semaphore.client import SemaphoreClient


def list_projects(client: SemaphoreClient) -> list[dict]:
    return client.get("/api/projects")


def create_project(client: SemaphoreClient, cfg: dict) -> int:
    project = client.post("/api/projects", _payload(cfg))
    return project["id"]


def update_project(client: SemaphoreClient, project_id: int, cfg: dict) -> None:
    client.put(f"/api/project/{project_id}", {"id": project_id, **_payload(cfg)})


def _payload(cfg: dict) -> dict:
    return {
        "name": cfg["name"],
        "alert": cfg.get("alert", False),
        "alert_chat": cfg.get("alert_chat", ""),
        "max_parallel_tasks": cfg.get("max_parallel_tasks", 0),
        "demo": False,
    }
