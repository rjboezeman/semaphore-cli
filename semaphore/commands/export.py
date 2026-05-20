"""Export a deployed project to a SemaphoreUI-native export file.

Calls SemaphoreUI's own backup endpoint (the same one behind
Project → Settings → Export in the UI) so the resulting file is byte-for-byte
the native format that ``apply`` and ``diff`` consume.
"""

import json
import re
import sys

from semaphore.client import SemaphoreClient
from semaphore.resources import list_inventory, list_projects, list_repositories


def export(client: SemaphoreClient, project_ref: str, output_path: str | None = None) -> None:
    """Export the project identified by name or id to a JSON file.

    ``project_ref`` is matched as a numeric id if it is all digits, otherwise
    by exact project name. ``output_path`` defaults to a slug of the project
    name with a ``.json`` extension.
    """
    projects = list_projects(client)
    project = _resolve_project(projects, project_ref)

    data = client.get(f"/api/project/{project['id']}/backup")
    _enrich_file_inventories(client, project["id"], data)

    if output_path is None:
        output_path = f"{_slug(project['name'])}.json"

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Exported project '{project['name']}' (id={project['id']}) → {output_path}")
    counts = ", ".join(
        f"{len(data.get(k, []))} {label}"
        for k, label in [
            ("keys", "keys"), ("repositories", "repositories"),
            ("inventories", "inventories"), ("environments", "environments"),
            ("templates", "templates"),
        ]
    )
    print(f"  {counts}")


def _enrich_file_inventories(client: SemaphoreClient, project_id: int, data: dict) -> None:
    """Inject `repository` (by name) onto every file-type inventory.

    SemaphoreUI's /backup endpoint omits the repository name for file-type
    inventories, which makes the export fail schema validation on a later
    diff/apply (file-type inventories require both `repository` and
    `inventory`). The /inventory list endpoint still has `repository_id`, so
    we resolve names from there and graft them onto the backup payload.
    """
    inventories = data.get("inventories") or []
    if not any(inv.get("type") == "file" and "repository" not in inv for inv in inventories):
        return

    deployed_inv = list_inventory(client, project_id)
    deployed_repos = list_repositories(client, project_id)
    inv_repo_id_by_name = {
        inv["name"]: inv.get("repository_id")
        for inv in deployed_inv
        if inv.get("type") == "file"
    }
    repo_name_by_id = {r["id"]: r["name"] for r in deployed_repos}

    for inv in inventories:
        if inv.get("type") != "file" or "repository" in inv:
            continue
        repo_id = inv_repo_id_by_name.get(inv.get("name"))
        if repo_id is None:
            continue
        repo_name = repo_name_by_id.get(repo_id)
        if repo_name is None:
            continue
        inv["repository"] = repo_name


def _resolve_project(projects: list[dict], project_ref: str) -> dict:
    """Find a project by numeric id or exact name; exit with help on failure."""
    if project_ref.isdigit():
        match = next((p for p in projects if p["id"] == int(project_ref)), None)
    else:
        match = next((p for p in projects if p["name"] == project_ref), None)

    if match is None:
        available = "\n".join(f"  [{p['id']}] {p['name']}" for p in projects) or "  (none)"
        print(f"ERROR: no project matching '{project_ref}'.", file=sys.stderr)
        print(f"       Available projects:\n{available}", file=sys.stderr)
        sys.exit(1)
    return match


def _slug(name: str) -> str:
    """Turn a project name into a filesystem-friendly slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "project"
