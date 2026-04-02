from semaphore.client import SemaphoreClient


def list_repositories(client: SemaphoreClient, project_id: int) -> list[dict]:
    return client.get(f"/api/project/{project_id}/repositories")


def create_repository(client: SemaphoreClient, project_id: int, cfg: dict, key_map: dict[str, int]) -> dict:
    return client.post(f"/api/project/{project_id}/repositories", _payload(project_id, cfg, key_map))


def update_repository(client: SemaphoreClient, project_id: int, repo_id: int, cfg: dict, key_map: dict[str, int]) -> None:
    client.put(f"/api/project/{project_id}/repositories/{repo_id}", {"id": repo_id, **_payload(project_id, cfg, key_map)})


def _payload(project_id: int, cfg: dict, key_map: dict[str, int]) -> dict:
    return {
        "name": cfg["name"],
        "project_id": project_id,
        "git_url": cfg["git_url"],
        "git_branch": cfg.get("git_branch", "main"),
        "ssh_key_id": key_map[cfg.get("ssh_key", "none")],
    }
