from semaphore.client import SemaphoreClient
from semaphore.resources import (
    create_environment, create_inventory, create_key, create_project,
    create_repository, create_schedule, list_environments, list_inventory,
    list_keys, list_projects, list_repositories, list_schedules,
    list_templates, update_environment, update_inventory, update_key,
    update_project, update_repository, update_schedule,
)
from semaphore.resources.templates import create_template, update_template


def apply(client: SemaphoreClient, config: dict) -> None:
    """Server-side apply from a SemaphoreUI export file.

    Creates or updates every resource. Never deletes anything.
    The project is identified by the name in config['meta']['name'].
    """
    proj_cfg = config["meta"]
    proj_name = proj_cfg["name"]

    print(f"Project: {proj_name}")
    existing_projects = {p["name"]: p for p in list_projects(client)}

    if proj_name in existing_projects:
        project_id = existing_projects[proj_name]["id"]
        update_project(client, project_id, proj_cfg)
        print(f"  [updated] id={project_id}")
    else:
        project_id = create_project(client, proj_cfg)
        print(f"  [created] id={project_id}")

    print("  Keys:")
    key_name_map = _upsert_keys(client, project_id, config.get("keys", []))

    none_key_id = next(
        v for k, v in key_name_map.items()
        if k.lower() == "none"
    )

    print("  Repositories:")
    repo_name_map = _upsert_repositories(client, project_id, config.get("repositories", []), key_name_map)

    print("  Inventory:")
    inv_name_map = _upsert_inventory(client, project_id, config.get("inventories", []), key_name_map, repo_name_map)

    print("  Environments:")
    env_name_map = _upsert_environments(client, project_id, config.get("environments", []))

    print("  Templates:")
    tmpl_name_map = _upsert_templates(client, project_id, config.get("templates", []), none_key_id, repo_name_map, inv_name_map, env_name_map)

    print("  Schedules:")
    _upsert_schedules(client, project_id, config.get("schedules", []), tmpl_name_map)

    print("\nDone.")


# ---------------------------------------------------------------------------
# Per-resource upsert helpers  (all keyed by resource name, not ref)
# ---------------------------------------------------------------------------

def _upsert_keys(client: SemaphoreClient, project_id: int, keys_cfg: list[dict]) -> dict[str, int]:
    """Returns name→id map. The auto-created None key is always included.

    Export files never contain secret values (SSH private keys, passwords).
    Existing keys are left untouched to preserve live credentials.
    New keys are created with placeholder values — fill them in via the UI.
    """
    existing = {k["name"]: k for k in list_keys(client, project_id)}
    name_map: dict[str, int] = {}

    # Register auto-created None key
    none_key = next((k for k in existing.values() if k["type"] == "none"), None)
    if none_key:
        name_map[none_key["name"]] = none_key["id"]

    for cfg in keys_cfg:
        name = cfg["name"]
        if cfg["type"] == "none":
            if none_key:
                name_map[name] = none_key["id"]
            continue

        if name in existing:
            # Do NOT update: the export has no secrets, overwriting would wipe live credentials
            name_map[name] = existing[name]["id"]
            print(f"    [skipped] {name}  (already exists — credentials preserved)")
        else:
            cfg_with_placeholders = _add_key_placeholders(cfg)
            created = create_key(client, project_id, cfg_with_placeholders)
            name_map[name] = created["id"]
            print(f"    [created] {name}  (⚠ placeholder credentials — update via UI before use)")

    return name_map


def _add_key_placeholders(cfg: dict) -> dict:
    """Return a copy of a key config with placeholder credentials for API acceptance."""
    cfg = dict(cfg)
    if cfg["type"] == "login_password":
        cfg.setdefault("login_password", {})
        cfg["login_password"] = {
            "login":    cfg["login_password"].get("login", "PLACEHOLDER"),
            "password": cfg["login_password"].get("password") or "PLACEHOLDER",
        }
    elif cfg["type"] == "ssh":
        cfg.setdefault("ssh", {})
        cfg["ssh"] = {
            "login":       cfg["ssh"].get("login", ""),
            "passphrase":  cfg["ssh"].get("passphrase", ""),
            "private_key": cfg["ssh"].get("private_key") or "PLACEHOLDER",
        }
    return cfg


def _upsert_repositories(
    client: SemaphoreClient,
    project_id: int,
    repos_cfg: list[dict],
    key_name_map: dict[str, int],
) -> dict[str, int]:
    existing = {r["name"]: r for r in list_repositories(client, project_id)}
    name_map: dict[str, int] = {}

    for cfg in repos_cfg:
        name = cfg["name"]
        if name in existing:
            update_repository(client, project_id, existing[name]["id"], cfg, key_name_map)
            name_map[name] = existing[name]["id"]
            print(f"    [updated] {name}")
        else:
            created = create_repository(client, project_id, cfg, key_name_map)
            name_map[name] = created["id"]
            print(f"    [created] {name}")

    return name_map


def _upsert_inventory(
    client: SemaphoreClient,
    project_id: int,
    inventory_cfg: list[dict],
    key_name_map: dict[str, int],
    repo_name_map: dict[str, int],
) -> dict[str, int]:
    existing = {i["name"]: i for i in list_inventory(client, project_id)}
    name_map: dict[str, int] = {}

    for cfg in inventory_cfg:
        name = cfg["name"]
        if name in existing:
            update_inventory(client, project_id, existing[name]["id"], cfg, key_name_map, repo_name_map)
            name_map[name] = existing[name]["id"]
            print(f"    [updated] {name}")
        else:
            created = create_inventory(client, project_id, cfg, key_name_map, repo_name_map)
            name_map[name] = created["id"]
            print(f"    [created] {name}")

    return name_map


def _upsert_environments(
    client: SemaphoreClient,
    project_id: int,
    environments_cfg: list[dict],
) -> dict[str, int]:
    existing = {e["name"]: e for e in list_environments(client, project_id)}
    name_map: dict[str, int] = {}

    # Auto-created Empty environment
    empty_env = existing.get("Empty")
    if empty_env:
        name_map["Empty"] = empty_env["id"]

    for cfg in environments_cfg:
        name = cfg["name"]
        if name in existing:
            update_environment(client, project_id, existing[name]["id"], cfg)
            name_map[name] = existing[name]["id"]
            print(f"    [updated] {name}")
        else:
            created = create_environment(client, project_id, cfg)
            name_map[name] = created["id"]
            print(f"    [created] {name}")

    return name_map


def _upsert_templates(
    client: SemaphoreClient,
    project_id: int,
    templates_cfg: list[dict],
    none_key_id: int,
    repo_name_map: dict[str, int],
    inv_name_map: dict[str, int],
    env_name_map: dict[str, int],
) -> dict[str, int]:
    existing = {t["name"]: t for t in list_templates(client, project_id)}
    name_map: dict[str, int] = {t["name"]: t["id"] for t in existing.values()}

    for cfg in templates_cfg:
        name = cfg["name"]
        if name in existing:
            update_template(client, project_id, existing[name]["id"], cfg, none_key_id, repo_name_map, inv_name_map, env_name_map)
            print(f"    [updated] {name}")
        else:
            created = create_template(client, project_id, cfg, none_key_id, repo_name_map, inv_name_map, env_name_map)
            name_map[name] = created["id"]
            print(f"    [created] {name}")

    return name_map


def _upsert_schedules(
    client: SemaphoreClient,
    project_id: int,
    schedules_cfg: list[dict],
    tmpl_name_map: dict[str, int],
) -> None:
    """Upsert schedules, matched by schedule name.

    The export format references each schedule's template by name. Schedules
    without a name cannot be matched against the deployed state and are
    skipped (SemaphoreUI allows unnamed schedules; name yours to manage them
    here). Deployed schedules absent from the file are left untouched, like
    every other resource type.
    """
    existing: dict[str, list[dict]] = {}
    for s in list_schedules(client, project_id):
        existing.setdefault(s.get("name", ""), []).append(s)

    for cfg in schedules_cfg:
        name = cfg.get("name", "")
        if not name:
            print(f"    [skipped] unnamed schedule (cron '{cfg.get('cron_format', '?')}') — give it a name to manage it")
            continue
        if cfg.get("template") not in tmpl_name_map:
            print(f"    [skipped] {name}  (references unknown template '{cfg.get('template')}')")
            continue

        matches = existing.get(name, [])
        if len(matches) > 1:
            ids = ", ".join(str(m["id"]) for m in matches)
            print(f"    [skipped] {name}  (name is ambiguous on the server — ids: {ids})")
        elif matches:
            update_schedule(client, project_id, matches[0]["id"], cfg, tmpl_name_map)
            print(f"    [updated] {name}")
        else:
            create_schedule(client, project_id, cfg, tmpl_name_map)
            print(f"    [created] {name}")
