from semaphore.client import SemaphoreClient


def list_schedules(client: SemaphoreClient, project_id: int) -> list[dict]:
    return client.get(f"/api/project/{project_id}/schedules")


def create_schedule(
    client: SemaphoreClient,
    project_id: int,
    cfg: dict,
    tmpl_name_map: dict[str, int],
) -> dict:
    return client.post(
        f"/api/project/{project_id}/schedules",
        _payload(project_id, cfg, tmpl_name_map),
    )


def update_schedule(
    client: SemaphoreClient,
    project_id: int,
    schedule_id: int,
    cfg: dict,
    tmpl_name_map: dict[str, int],
) -> None:
    client.put(
        f"/api/project/{project_id}/schedules/{schedule_id}",
        {"id": schedule_id, **_payload(project_id, cfg, tmpl_name_map)},
    )


def delete_schedule(client: SemaphoreClient, project_id: int, schedule_id: int) -> None:
    client.delete(f"/api/project/{project_id}/schedules/{schedule_id}")


def _payload(project_id: int, cfg: dict, tmpl_name_map: dict[str, int]) -> dict:
    # The export format references the template by name; the API wants its id.
    # `type` is omitted: the server defaults an empty type to a cron schedule,
    # which is the only kind the export format carries.
    return {
        "project_id":  project_id,
        "name":        cfg.get("name", ""),
        "cron_format": cfg["cron_format"],
        "template_id": tmpl_name_map[cfg["template"]],
        "active":      cfg.get("active", True),
    }
