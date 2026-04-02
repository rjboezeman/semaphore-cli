from semaphore.client import SemaphoreClient


def list_templates(client: SemaphoreClient, project_id: int) -> list[dict]:
    return client.get(f"/api/project/{project_id}/templates")


def create_template(
    client: SemaphoreClient,
    project_id: int,
    cfg: dict,
    none_key_id: int,
    repo_name_map: dict[str, int],
    inv_name_map: dict[str, int],
    env_name_map: dict[str, int],
) -> dict:
    return client.post(
        f"/api/project/{project_id}/templates",
        _payload(project_id, cfg, none_key_id, repo_name_map, inv_name_map, env_name_map),
    )


def update_template(
    client: SemaphoreClient,
    project_id: int,
    tmpl_id: int,
    cfg: dict,
    none_key_id: int,
    repo_name_map: dict[str, int],
    inv_name_map: dict[str, int],
    env_name_map: dict[str, int],
) -> None:
    client.put(
        f"/api/project/{project_id}/templates/{tmpl_id}",
        {"id": tmpl_id, **_payload(project_id, cfg, none_key_id, repo_name_map, inv_name_map, env_name_map)},
    )


def _payload(
    project_id: int,
    cfg: dict,
    none_key_id: int,
    repo_name_map: dict[str, int],
    inv_name_map: dict[str, int],
    env_name_map: dict[str, int],
) -> dict:
    return {
        "project_id":                    project_id,
        "name":                          cfg["name"],
        "app":                           cfg.get("app", "ansible"),
        "type":                          cfg.get("type", ""),
        "playbook":                      cfg.get("playbook", ""),
        "repository_id":                 repo_name_map[cfg["repository"]],
        "inventory_id":                  inv_name_map[cfg["inventory"]],
        "environment_id":                env_name_map[cfg["environment"]],
        "ssh_key_id":                    none_key_id,
        "description":                   cfg.get("description", ""),
        "allow_override_args_in_task":   cfg.get("allow_override_args_in_task", False),
        "allow_override_branch_in_task": cfg.get("allow_override_branch_in_task", False),
        "allow_parallel_tasks":          cfg.get("allow_parallel_tasks", False),
        "suppress_success_alerts":       cfg.get("suppress_success_alerts", False),
        "autorun":                       cfg.get("autorun", False),
    }
